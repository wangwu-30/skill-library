#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from filelock import FileLock

DEFAULT_ROOT = Path(__file__).resolve().parents[4]
MAX_JSON_BYTES = 16 * 1024 * 1024
METADATA_SCHEMA_VERSION = 2
DEFAULT_USAGE_TRACKING_MODE = "none"
VALID_USAGE_TRACKING_MODES = {"none", "manual", "hub"}
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEWED_CORE_PATH_RE = re.compile(r"^house-skills/core/[a-z0-9]+(?:-[a-z0-9]+)*$")
GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
MAX_REVIEWED_SKILL_FILES = 1_024
MAX_REVIEWED_SKILL_PAYLOAD_BYTES = 16 * 1024 * 1024
DEFAULT_LIFECYCLE_CONFIG = {
    "young": {
        "default_ttl_days": 14,
        "refresh_ttl_days_on_use": 14,
        "auto_archive_expired": False,
    },
    "promotion": {
        "min_use_count": 3,
        "recent_use_within_days": 14,
        "auto_promote_eligible": False,
    },
    "archive": {
        "hard_delete_enabled": False,
        "keep_reason_history": True,
    },
}


def locate_library_root(cli_root: Path | None, anchor_path: Path | None = None) -> Path:
    if cli_root:
        root = cli_root.expanduser().resolve()
        if not (root / "catalog" / "tracked_repos.json").is_file():
            raise FileNotFoundError(
                f"Not a skill-library root (missing catalog/tracked_repos.json): {root}"
            )
        return root

    candidates: list[Path] = [Path.cwd().resolve()]

    if anchor_path is not None:
        resolved_anchor = anchor_path.resolve()
        candidates.extend(resolved_anchor.parents)

    candidates.append(DEFAULT_ROOT)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "catalog" / "tracked_repos.json").exists():
            return candidate

    raise FileNotFoundError("Could not locate catalog/tracked_repos.json")


def ensure_within_root(
    path: Path, root: Path, *, label: str = "path", allow_root: bool = False
) -> Path:
    """Resolve *path* and reject paths that escape *root*.

    This check intentionally resolves existing symlinks. Callers that create files must
    validate the destination before writing and should use :func:`atomic_write_text`.
    """

    resolved_root = root.expanduser().resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside {resolved_root}: {path}") from exc
    if resolved_path == resolved_root and not allow_root:
        raise ValueError(f"{label} must not be the library root: {path}")
    return resolved_path


def resolve_relative_path(root: Path, value: str | Path, *, label: str = "path") -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be relative to the library root: {value}")
    if ".." in candidate.parts:
        raise ValueError(f"{label} must not contain parent traversal: {value}")
    current = root.expanduser().resolve()
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} must not contain symlinks: {value}")
    return ensure_within_root(root / candidate, root, label=label)


def canonical_upstream_repo_url(value: str) -> str:
    """Validate and canonicalize a credential-free GitHub HTTPS repository URL."""

    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 2048:
        raise ValueError("upstream repo_url must be a non-empty, trimmed string")
    if "\\" in value or "%" in value:
        raise ValueError("upstream repo_url must not contain escapes or backslashes")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError("upstream repo_url must use https://github.com")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("upstream repo_url must not contain credentials")
    if parsed.port is not None or parsed.query or parsed.fragment:
        raise ValueError("upstream repo_url must not contain a port, query, or fragment")
    parts = parsed.path.removesuffix("/").split("/")
    if len(parts) != 3 or parts[0]:
        raise ValueError("upstream repo_url must identify exactly one owner/repository")
    owner, repository = parts[1], parts[2].removesuffix(".git")
    if not GITHUB_OWNER_RE.fullmatch(owner) or not GITHUB_REPOSITORY_RE.fullmatch(repository):
        raise ValueError("upstream repo_url contains an invalid GitHub owner or repository name")
    if repository in {".", ".."} or repository.startswith("."):
        raise ValueError("upstream repo_url contains an invalid repository name")
    return f"https://github.com/{owner.lower()}/{repository.lower()}"


def skill_content_sha256(skill_dir: Path) -> str:
    """Hash reviewed skill payload files, excluding mutable lifecycle metadata and caches."""

    skill_root = skill_dir.resolve()
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for path in sorted(skill_root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(skill_root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"reviewed skill payload must not contain symlinks: {relative}")
        if not path.is_file() or relative == Path("metadata.json"):
            continue
        data = path.read_bytes()
        file_count += 1
        total_bytes += len(data)
        if file_count > MAX_REVIEWED_SKILL_FILES:
            raise ValueError(
                f"reviewed skill exceeds {MAX_REVIEWED_SKILL_FILES} payload files: {skill_dir}"
            )
        if total_bytes > MAX_REVIEWED_SKILL_PAYLOAD_BYTES:
            raise ValueError(
                "reviewed skill payload exceeds "
                f"{MAX_REVIEWED_SKILL_PAYLOAD_BYTES} bytes: {skill_dir}"
            )
        relative_bytes = relative.as_posix().encode("utf-8")
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    if file_count == 0:
        raise ValueError(f"reviewed skill has no payload files: {skill_dir}")
    return digest.hexdigest()


def read_reviewed_core_manifest(root: Path) -> dict[str, str]:
    path = root / "catalog" / "reviewed_core.lock.json"
    if not path.is_file():
        raise ValueError(f"missing reviewed core manifest: {path}")
    document = read_json(path)
    if document.get("schema_version") != 1 or not isinstance(document.get("skills"), list):
        raise ValueError(f"invalid reviewed core manifest schema: {path}")
    reviewed: dict[str, str] = {}
    for entry in document["skills"]:
        if not isinstance(entry, dict):
            raise ValueError("reviewed core manifest entries must be objects")
        skill_path = entry.get("path")
        content_hash = entry.get("content_sha256")
        if (
            not isinstance(skill_path, str)
            or not REVIEWED_CORE_PATH_RE.fullmatch(skill_path)
            or skill_path in reviewed
            or not isinstance(content_hash, str)
            or not SHA256_RE.fullmatch(content_hash)
        ):
            raise ValueError(f"invalid reviewed core manifest entry: {entry}")
        resolved = resolve_relative_path(root, skill_path, label="reviewed core skill path")
        ensure_within_root(resolved, root / "house-skills" / "core", label="reviewed core skill")
        reviewed[skill_path] = content_hash
    return reviewed


def read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    size = path.stat().st_size
    if size > MAX_JSON_BYTES:
        raise ValueError(f"JSON file exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, data: dict) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Publish a complete file atomically in the destination directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination_stat = path.lstat()
    except FileNotFoundError:
        publish_mode = 0o600
    else:
        if stat.S_ISLNK(destination_stat.st_mode):
            raise ValueError(f"refusing to replace symlink: {path}")
        if not stat.S_ISREG(destination_stat.st_mode):
            raise ValueError(f"refusing to replace non-regular file: {path}")
        publish_mode = stat.S_IMODE(destination_stat.st_mode) & 0o777
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fchmod(handle.fileno(), publish_mode)
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@contextmanager
def library_lock(root: Path, *, timeout: float = 30.0) -> Iterator[None]:
    """Serialize repository mutations across maintenance and MCP processes."""

    lock_path = ensure_within_root(root / ".skill-library.lock", root, label="lock path")
    with FileLock(lock_path, timeout=timeout):
        yield


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def iso_now() -> str:
    return now_utc().isoformat()


def default_skill_version(stage: str) -> str:
    return "1.0.0" if stage == "core" else "0.1.0"


def parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed


def ensure_timezone(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value


def nearest_metadata_path(skill_dir: Path, repo_root: Path) -> Path | None:
    current = skill_dir.resolve()
    repo_root = repo_root.resolve()
    while True:
        candidate = current / "metadata.json"
        if candidate.exists():
            return candidate
        if current == repo_root:
            return None
        if repo_root not in current.parents:
            return None
        current = current.parent


def load_skill_metadata(skill_dir: Path, repo_root: Path) -> tuple[Path | None, dict]:
    metadata_path = nearest_metadata_path(skill_dir, repo_root)
    if metadata_path is None:
        return None, {}
    return metadata_path, read_json(metadata_path, {})


def skill_stage(metadata: dict) -> str:
    return metadata.get("stage") or "upstream"


def usage_tracking_mode(metadata: dict) -> str:
    usage_tracking = metadata.get("usage_tracking")
    if not isinstance(usage_tracking, dict):
        return DEFAULT_USAGE_TRACKING_MODE
    mode = usage_tracking.get("mode")
    if mode in VALID_USAGE_TRACKING_MODES:
        return mode
    return DEFAULT_USAGE_TRACKING_MODE


def usage_counts_available(metadata: dict) -> bool:
    return usage_tracking_mode(metadata) in {"manual", "hub"}


def is_semver(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return bool(SEMVER_RE.match(value))


def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(value)
    if not match:
        raise ValueError(f"Invalid semver: {value}")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def format_semver(parts: tuple[int, int, int]) -> str:
    major, minor, patch = parts
    return f"{major}.{minor}.{patch}"


def bump_semver(value: str, bump: str) -> str:
    major, minor, patch = parse_semver(value)
    if bump == "major":
        return format_semver((major + 1, 0, 0))
    if bump == "minor":
        return format_semver((major, minor + 1, 0))
    if bump == "patch":
        return format_semver((major, minor, patch + 1))
    raise ValueError(f"Unsupported bump kind: {bump}")


def is_expired(metadata: dict, now: dt.datetime | None = None) -> bool:
    expires_at = parse_datetime(metadata.get("expires_at"))
    if expires_at is None:
        return False
    reference = ensure_timezone(now or now_utc())
    return expires_at <= reference


def relative_to_root(path: Path | None, root: Path) -> str:
    if path is None:
        return ""
    return str(ensure_within_root(path, root, allow_root=True).relative_to(root.resolve()))


def lifecycle_config_path(root: Path) -> Path:
    return root / "house-skills" / "config" / "lifecycle.json"


def _merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged[key] = _merge_dict(base[key], value)
        else:
            merged[key] = value
    return merged


def load_lifecycle_config(root: Path) -> dict:
    config_path = lifecycle_config_path(root)
    override = read_json(config_path, {})
    return _merge_dict(DEFAULT_LIFECYCLE_CONFIG, override)
