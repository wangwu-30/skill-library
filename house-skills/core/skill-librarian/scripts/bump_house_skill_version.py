#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from skill_library_utils import (
    bump_semver,
    iso_now,
    is_semver,
    locate_library_root,
    parse_semver,
    read_json,
    relative_to_root,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump a house skill version and optionally snapshot the previous version."
    )
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--skill-path", type=Path, required=True, help="House skill root path")
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Increment the current version by one semver segment",
    )
    version_group.add_argument(
        "--set-version",
        help="Set the skill version explicitly, for example 1.2.0",
    )
    parser.add_argument(
        "--snapshot-current",
        action="store_true",
        help="Copy the current skill into house-skills/archive before updating metadata",
    )
    parser.add_argument(
        "--compatibility",
        choices=["auto", "backward-compatible", "breaking"],
        default="auto",
        help="Compatibility declaration for the new version",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Short compatibility or release note to store in metadata",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned actions without writing files",
    )
    return parser.parse_args()


def resolve_skill_path(root: Path, skill_path: Path) -> Path:
    if skill_path.is_absolute():
        return skill_path.resolve()
    return (root / skill_path).resolve()


def snapshot_destination(root: Path, skill_dir: Path, version: str) -> Path:
    archive_root = root / "house-skills" / "archive"
    suffix = version.replace(".", "-")
    candidate = archive_root / f"{skill_dir.name}-v{suffix}"
    if not candidate.exists():
        return candidate
    return archive_root / f"{skill_dir.name}-v{suffix}-{iso_now().replace(':', '').replace('+', '_')}"


def compatibility_value(
    old_version: str, new_version: str, mode: str
) -> dict[str, bool | str]:
    if mode == "backward-compatible":
        backward_compatible = True
    elif mode == "breaking":
        backward_compatible = False
    else:
        old_major, _, _ = parse_semver(old_version)
        new_major, _, _ = parse_semver(new_version)
        backward_compatible = old_major == new_major
    return {
        "backward_compatible": backward_compatible,
    }


def append_replace_record(metadata: dict, record: dict) -> None:
    replaces = metadata.setdefault("replaces", [])
    if not isinstance(replaces, list):
        replaces = []
        metadata["replaces"] = replaces
    if replaces and replaces[-1] == record:
        return
    replaces.append(record)


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    skill_root = resolve_skill_path(root, args.skill_path)
    metadata_path = skill_root / "metadata.json"

    if not metadata_path.exists():
        raise SystemExit(f"metadata.json not found: {metadata_path}")

    metadata = read_json(metadata_path)
    old_version = metadata.get("version")
    if not is_semver(old_version):
        raise SystemExit(f"Current skill version is missing or invalid: {old_version}")

    if args.bump:
        new_version = bump_semver(old_version, args.bump)
    else:
        if not is_semver(args.set_version):
            raise SystemExit(f"Invalid target semver: {args.set_version}")
        new_version = args.set_version

    if new_version == old_version:
        raise SystemExit("New version is identical to the current version")

    now = iso_now()
    skill_rel_path = relative_to_root(skill_root, root)
    snapshot_rel_path = ""
    compatibility = compatibility_value(old_version, new_version, args.compatibility)
    compatibility["notes"] = args.notes

    if args.snapshot_current:
        snapshot_dir = snapshot_destination(root, skill_root, old_version)
        snapshot_rel_path = relative_to_root(snapshot_dir, root)
        if not args.dry_run:
            snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_root, snapshot_dir)
            snapshot_metadata_path = snapshot_dir / "metadata.json"
            snapshot_metadata = read_json(snapshot_metadata_path)
            snapshot_metadata["stage"] = "archive"
            snapshot_metadata["status"] = "archived"
            snapshot_metadata["updated_at"] = now
            snapshot_metadata["archived_at"] = now
            snapshot_metadata["archive_reason"] = "version-snapshot"
            snapshot_metadata["snapshot_of"] = {
                "skill_path": skill_rel_path,
                "version": old_version,
            }
            snapshot_metadata["replaced_by"] = {
                "skill_path": skill_rel_path,
                "version": new_version,
            }
            write_json(snapshot_metadata_path, snapshot_metadata)

    metadata["version"] = new_version
    metadata["updated_at"] = now
    metadata["compatibility"] = compatibility
    replace_record = {
        "skill_path": skill_rel_path,
        "version": old_version,
    }
    if snapshot_rel_path:
        replace_record["archived_path"] = snapshot_rel_path
    append_replace_record(metadata, replace_record)

    if not args.dry_run:
        write_json(metadata_path, metadata)

    print(
        f"{'DRY RUN ' if args.dry_run else ''}"
        f"{skill_root.name}: {old_version} -> {new_version} | "
        f"backward_compatible={str(compatibility['backward_compatible']).lower()}"
    )
    if snapshot_rel_path:
        print(f"Snapshot: {snapshot_rel_path}")
    if args.notes:
        print(f"Notes: {args.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
