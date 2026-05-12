#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from skill_consult import resolve_skill
from skill_library_utils import iso_now, locate_library_root, read_json, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply explicit house-skill lifecycle actions.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    subcommands = parser.add_subparsers(dest="action", required=True)

    promote = subcommands.add_parser("promote", help="Promote a young skill to core")
    promote.add_argument("identifier", help="Skill name or path")
    promote.add_argument("--reason", default="explicit-promotion")

    archive = subcommands.add_parser("archive", help="Archive a house skill")
    archive.add_argument("identifier", help="Skill name or path")
    archive.add_argument("--reason", default="explicit-archive")

    return parser.parse_args()


def stage_for_path(root: Path, skill_dir: Path) -> str:
    relative = skill_dir.resolve().relative_to((root / "house-skills").resolve())
    return relative.parts[0]


def move_skill(root: Path, skill_dir: Path, target_stage: str) -> Path:
    target = root / "house-skills" / target_stage / skill_dir.name
    if target.exists():
        raise FileExistsError(f"Lifecycle target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(skill_dir), str(target))
    return target


def update_metadata(skill_dir: Path, stage: str, status: str, reason_key: str, reason: str) -> None:
    metadata_path = skill_dir / "metadata.json"
    metadata = read_json(metadata_path)
    now = iso_now()
    metadata["stage"] = stage
    metadata["status"] = status
    metadata["updated_at"] = now
    if stage == "core":
        metadata["expires_at"] = None
        metadata["promoted_at"] = now
    if stage == "archive":
        metadata["archived_at"] = now
    metadata[reason_key] = reason
    write_json(metadata_path, metadata)


def promote_skill(root: Path, identifier: str, reason: str) -> Path:
    skill_dir = resolve_skill(root, identifier)
    if skill_dir is None:
        raise FileNotFoundError(f"skill not found: {identifier}")
    stage = stage_for_path(root, skill_dir)
    if stage != "young":
        raise ValueError(f"only young skills can be promoted; got stage={stage}")
    target = move_skill(root, skill_dir, "core")
    update_metadata(target, "core", "stable", "promotion_reason", reason)
    return target


def archive_skill(root: Path, identifier: str, reason: str) -> Path:
    skill_dir = resolve_skill(root, identifier)
    if skill_dir is None:
        raise FileNotFoundError(f"skill not found: {identifier}")
    stage = stage_for_path(root, skill_dir)
    if stage == "archive":
        raise ValueError("skill is already archived")
    target = move_skill(root, skill_dir, "archive")
    update_metadata(target, "archive", "archived", "archive_reason", reason)
    return target


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    if args.action == "promote":
        target = promote_skill(root, args.identifier, args.reason)
        print(f"Promoted skill to {target.relative_to(root)}")
        return 0
    if args.action == "archive":
        target = archive_skill(root, args.identifier, args.reason)
        print(f"Archived skill to {target.relative_to(root)}")
        return 0
    raise AssertionError(args.action)


if __name__ == "__main__":
    raise SystemExit(main())
