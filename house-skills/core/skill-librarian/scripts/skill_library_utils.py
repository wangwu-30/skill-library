#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[4]
METADATA_SCHEMA_VERSION = 2
DEFAULT_USAGE_TRACKING_MODE = "none"
VALID_USAGE_TRACKING_MODES = {"none", "manual", "hub"}
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
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
        return cli_root.resolve()

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


def read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat()


def default_skill_version(stage: str) -> str:
    return "1.0.0" if stage == "core" else "0.1.0"


def parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def ensure_timezone(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
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
    return str(path.resolve().relative_to(root.resolve()))


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
