#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from skill_library_utils import (
    REVIEWED_CORE_PATH_RE,
    locate_library_root,
    resolve_relative_path,
    skill_content_sha256,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a deterministic reviewed-core payload hash after manual review."
    )
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--skill-path",
        required=True,
        help="Direct core skill path, for example house-skills/core/skill-librarian",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    if not REVIEWED_CORE_PATH_RE.fullmatch(args.skill_path):
        raise SystemExit("--skill-path must name one direct house-skills/core child")
    skill_dir = resolve_relative_path(root, args.skill_path, label="core skill path")
    metadata_path = skill_dir / "metadata.json"
    skill_path = skill_dir / "SKILL.md"
    if not metadata_path.is_file() or not skill_path.is_file():
        raise SystemExit(f"core skill is incomplete: {args.skill_path}")
    print(skill_content_sha256(skill_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
