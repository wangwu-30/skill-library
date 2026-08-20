from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from conftest import LIBRARIAN_SCRIPTS, load_script

catalog_builder = load_script("build_skill_catalog", LIBRARIAN_SCRIPTS / "build_skill_catalog.py")
utils = load_script("skill_library_utils", LIBRARIAN_SCRIPTS / "skill_library_utils.py")


def write_skill(path: Path, name: str, description: str, *, core: bool) -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    if core:
        (path / "metadata.json").write_text(
            json.dumps({"stage": "core", "status": "stable", "version": "1.0.0"}),
            encoding="utf-8",
        )


def test_catalog_marks_only_local_core_as_executable(library_root: Path) -> None:
    core_root = library_root / "house-skills/core"
    upstream_root = library_root / "upstream"
    write_skill(core_root / "reviewed", "reviewed", "Use when reviewing local work.", core=True)
    write_skill(
        upstream_root / "untrusted",
        "untrusted",
        "Use when inspecting upstream material.",
        core=False,
    )
    reviewed_path = "house-skills/core/reviewed"
    reviewed_hash = utils.skill_content_sha256(core_root / "reviewed")
    (library_root / "catalog/reviewed_core.lock.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": [{"path": reviewed_path, "content_sha256": reviewed_hash}],
            }
        ),
        encoding="utf-8",
    )
    repos = [
        {
            "id": "core",
            "local_dir": "house-skills/core",
            "repo_url": "local://house-skills/core",
            "kind": "house-skill-space",
            "priority": "core",
            "tags": ["local"],
            "notes": "reviewed",
        },
        {
            "id": "upstream",
            "local_dir": "upstream",
            "repo_url": "https://example.test/upstream",
            "kind": "community-library",
            "priority": "high",
            "tags": ["upstream"],
            "notes": "reference",
        },
    ]

    built = catalog_builder.build_catalog(library_root, repos)
    trust = {entry["name"]: entry["execution_trust"] for entry in built["skills"]}

    assert trust == {"reviewed": "reviewed-core", "untrusted": "reference-only"}
    catalog_builder.write_catalog(library_root, built)
    assert json.loads((library_root / "catalog/skill_catalog.json").read_text())["skill_count"] == 2


def test_catalog_records_malformed_skill_as_reference_only(library_root: Path) -> None:
    root = library_root / "house-skills/core/bad"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text("---\nname: [bad\n---\n", encoding="utf-8")
    parsed = catalog_builder.parse_skill_file(
        root / "SKILL.md", library_root / "house-skills/core", library_root
    )
    assert parsed["parse_error"].startswith("invalid YAML")
    assert parsed["execution_trust"] == "reference-only"


def test_catalog_requires_reviewed_payload_hash(library_root: Path) -> None:
    core_root = library_root / "house-skills/core"
    skill = core_root / "forged"
    write_skill(skill, "forged", "Use when testing explicit review evidence.", core=True)
    repos = [
        {
            "id": "core",
            "local_dir": "house-skills/core",
            "repo_url": "local://house-skills/core",
            "kind": "house-skill-space",
            "priority": "core",
            "tags": ["local"],
            "notes": "reviewed",
        }
    ]

    assert catalog_builder.build_catalog(library_root, repos)["skills"][0]["execution_trust"] == (
        "reference-only"
    )

    content_hash = utils.skill_content_sha256(skill)
    (library_root / "catalog/reviewed_core.lock.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": [
                    {
                        "path": "house-skills/core/forged",
                        "content_sha256": content_hash,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert catalog_builder.build_catalog(library_root, repos)["skills"][0]["execution_trust"] == (
        "reviewed-core"
    )

    (skill / "SKILL.md").write_text("changed after review\n", encoding="utf-8")
    assert catalog_builder.build_catalog(library_root, repos)["skills"][0]["execution_trust"] == (
        "reference-only"
    )


def test_atomic_json_write_and_invalid_json_handling(library_root: Path) -> None:
    path = library_root / "catalog/value.json"
    utils.write_json(path, {"message": "你好"})
    assert utils.read_json(path) == {"message": "你好"}
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))

    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        utils.read_json(path)


def test_atomic_write_new_file_is_private_even_with_permissive_umask(
    library_root: Path,
) -> None:
    path = library_root / "catalog/private.json"
    previous_umask = os.umask(0o000)
    try:
        utils.atomic_write_text(path, "private\n")
    finally:
        os.umask(previous_umask)

    assert path.read_text(encoding="utf-8") == "private\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))


@pytest.mark.parametrize("mode", [0o600, 0o640, 0o644, 0o755])
def test_atomic_write_preserves_existing_mode(library_root: Path, mode: int) -> None:
    path = library_root / "catalog/existing.json"
    path.write_text("old\n", encoding="utf-8")
    path.chmod(mode)

    utils.atomic_write_text(path, "new\n")

    assert path.read_text(encoding="utf-8") == "new\n"
    assert stat.S_IMODE(path.stat().st_mode) == mode


def test_atomic_write_strips_special_permission_bits(library_root: Path) -> None:
    path = library_root / "catalog/setuid-script"
    path.write_text("old\n", encoding="utf-8")
    path.chmod(0o4755)

    utils.atomic_write_text(path, "new\n")

    assert path.read_text(encoding="utf-8") == "new\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o755


def test_atomic_write_applies_mode_to_open_temporary_file(
    library_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = library_root / "catalog/private.txt"
    calls: list[tuple[int, int]] = []
    real_fchmod = os.fchmod

    def recording_fchmod(file_descriptor: int, mode: int) -> None:
        calls.append((file_descriptor, mode))
        real_fchmod(file_descriptor, mode)

    monkeypatch.setattr(utils.os, "fchmod", recording_fchmod)
    utils.atomic_write_text(path, "private\n")

    assert len(calls) == 1
    assert calls[0][0] >= 0
    assert calls[0][1] == 0o600


def test_atomic_write_refuses_symlink(library_root: Path, tmp_path: Path) -> None:
    target = tmp_path / "outside.txt"
    target.write_text("keep", encoding="utf-8")
    link = library_root / "catalog/link.txt"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        utils.atomic_write_text(link, "replace")
    assert target.read_text(encoding="utf-8") == "keep"


def test_atomic_write_refuses_non_regular_destination(library_root: Path) -> None:
    destination = library_root / "catalog/directory"
    destination.mkdir()

    with pytest.raises(ValueError, match="non-regular"):
        utils.atomic_write_text(destination, "replace")


def test_atomic_write_cleans_up_after_replace_failure(
    library_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = library_root / "catalog/existing.txt"
    path.write_text("old\n", encoding="utf-8")
    path.chmod(0o640)

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {source} with {destination}")

    monkeypatch.setattr(utils.os, "replace", fail_replace)
    with pytest.raises(OSError, match="cannot replace"):
        utils.atomic_write_text(path, "new\n")

    assert path.read_text(encoding="utf-8") == "old\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))


def test_paths_and_datetime_are_fail_closed(library_root: Path, tmp_path: Path) -> None:
    assert utils.resolve_relative_path(library_root, "catalog/file.json").is_relative_to(
        library_root
    )
    with pytest.raises(ValueError):
        utils.resolve_relative_path(library_root, "../escape")
    with pytest.raises(ValueError):
        utils.ensure_within_root(tmp_path, library_root)
    assert utils.parse_datetime("not-a-date") is None
    assert utils.parse_datetime("2026-08-20T00:00:00Z").tzinfo is not None


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("https://github.com/Owner/Repository", "https://github.com/owner/repository"),
        ("https://github.com/Owner/Repository.git", "https://github.com/owner/repository"),
        ("https://github.com/Owner/Repository/", "https://github.com/owner/repository"),
    ],
)
def test_upstream_url_is_canonicalized(raw: str, canonical: str) -> None:
    assert utils.canonical_upstream_repo_url(raw) == canonical


@pytest.mark.parametrize(
    "raw",
    [
        "http://github.com/owner/repository",
        "https://user:token@github.com/owner/repository",
        "https://github.com.evil.test/owner/repository",
        "https://github.com/owner/repository?ref=main",
        "file:///tmp/repository",
        "git@github.com:owner/repository.git",
    ],
)
def test_upstream_url_rejects_unsafe_transports(raw: str) -> None:
    with pytest.raises(ValueError):
        utils.canonical_upstream_repo_url(raw)


def test_reviewed_manifest_rejects_nested_skill_path(library_root: Path) -> None:
    (library_root / "catalog/reviewed_core.lock.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": [
                    {
                        "path": "house-skills/core/reviewed/nested",
                        "content_sha256": "a" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid reviewed core manifest entry"):
        utils.read_reviewed_core_manifest(library_root)
