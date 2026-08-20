#!/usr/bin/env python3
"""
Consult a house skill and automatically record usage.

This is the minimal CLI runtime that makes usage_tracking meaningful.
Without a consult layer, manual usage recording is unreliable.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from skill_library_utils import ensure_within_root, locate_library_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consult a house skill by name or path, print its SKILL.md, and record usage."
    )
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "identifier",
        help="Skill name (e.g., 'decision-grade-research') or relative path (e.g., 'house-skills/young/doc-coauthoring')",
    )
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="Print the skill without recording usage (dry consult)",
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "hub"],
        default="manual",
        help="Usage tracking mode for this event",
    )
    return parser.parse_args()


def resolve_skill(root: Path, identifier: str) -> Path | None:
    """Resolve a skill identifier to its directory."""
    if not identifier or "\x00" in identifier:
        return None
    house_root = (root / "house-skills").resolve()
    # Try direct path first
    try:
        direct = ensure_within_root(root / identifier, house_root, label="skill identifier")
    except ValueError:
        direct = None
    if direct is not None and direct.exists() and (direct / "SKILL.md").is_file():
        return direct

    # Try as a relative path under house-skills/
    for stage in ("core", "young", "archive"):
        try:
            candidate = ensure_within_root(
                root / "house-skills" / stage / identifier,
                root / "house-skills" / stage,
                label="skill identifier",
            )
        except ValueError:
            continue
        if candidate.exists() and (candidate / "SKILL.md").is_file():
            return candidate

    # Try catalog search by exact name match
    catalog_path = root / "catalog" / "skill_catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        for entry in catalog.get("skills", []):
            if entry.get("name") == identifier:
                skill_root = entry.get("skill_root_path", "")
                if skill_root:
                    try:
                        candidate = ensure_within_root(
                            root / skill_root, house_root, label="catalog skill path"
                        )
                    except ValueError:
                        continue
                    if candidate.exists() and (candidate / "SKILL.md").is_file():
                        return candidate

    return None


def record_usage(root: Path, skill_dir: Path, mode: str) -> None:
    script = Path(__file__).parent / "record_skill_usage.py"
    rel_path = skill_dir.relative_to(root)
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(root),
            "--skill-path",
            str(rel_path),
            "--mode",
            mode,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[warn] usage recording failed: {result.stderr.strip()}", file=sys.stderr)
    else:
        print(f"[info] {result.stdout.strip()}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    skill_dir = resolve_skill(root, args.identifier)

    if skill_dir is None:
        print(
            f"error: skill not found: {args.identifier}\n"
            f"hint: run search first:\n"
            f"  python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py "
            f'--root {root} --query "{args.identifier}"',
            file=sys.stderr,
        )
        return 1

    skill_md = skill_dir / "SKILL.md"
    print(skill_md.read_text(encoding="utf-8"), end="")

    if not args.no_record:
        record_usage(root, skill_dir, args.mode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
