#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path

from skill_consult import resolve_skill
from skill_library_utils import (
    default_skill_version,
    iso_now,
    load_lifecycle_config,
    locate_library_root,
    parse_datetime,
    read_json,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fork a house skill into a young experiment variant.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--base", required=True, help="Base skill name or path")
    parser.add_argument("--variant", required=True, help="Experiment variant label")
    parser.add_argument("--notes", default="", help="Experiment notes")
    return parser.parse_args()


def normalize(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")


def rewrite_skill_frontmatter(skill_md: Path, name: str, description_suffix: str) -> None:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        return
    end = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            end = index
            break
    if end is None:
        return
    frontmatter = []
    for line in lines[1:end]:
        if line.startswith("name:"):
            frontmatter.append(f"name: {name}")
        elif line.startswith("description:"):
            frontmatter.append(f"{line} {description_suffix}")
        else:
            frontmatter.append(line)
    rewritten = ["---", *frontmatter, "---", *lines[end + 1 :]]
    skill_md.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def create_experiment(root: Path, base: str, variant: str, notes: str) -> Path:
    base_dir = resolve_skill(root, base)
    if base_dir is None:
        raise FileNotFoundError(f"base skill not found: {base}")

    variant_label = normalize(variant)
    if not variant_label:
        raise ValueError("variant must contain at least one alphanumeric character")

    experiment_name = f"{base_dir.name}-exp-{variant_label}"
    target = root / "house-skills" / "young" / experiment_name
    if target.exists():
        raise FileExistsError(f"Experiment already exists: {target}")

    shutil.copytree(base_dir, target)
    rewrite_skill_frontmatter(
        target / "SKILL.md",
        experiment_name,
        f"(Experimental variant: {variant_label}.)",
    )

    base_metadata = read_json(base_dir / "metadata.json")
    config = load_lifecycle_config(root)
    ttl_days = int(config["young"]["default_ttl_days"])
    now = iso_now()
    expires_at = parse_datetime(now)
    if expires_at is None:
        raise RuntimeError("failed to parse current time")
    expires_at = expires_at + dt.timedelta(days=ttl_days)

    metadata = read_json(target / "metadata.json")
    metadata["version"] = default_skill_version("young")
    metadata["stage"] = "young"
    metadata["status"] = "active"
    metadata["created_at"] = now
    metadata["updated_at"] = now
    metadata["last_used_at"] = None
    metadata["use_count"] = 0
    metadata["expires_at"] = expires_at.isoformat()
    metadata["usage_tracking"] = {"mode": "none"}
    metadata["derives_from"] = {
        "skill_path": str(base_dir.relative_to(root)),
        "version": base_metadata.get("version", ""),
    }
    metadata["replaces"] = []
    metadata["compatibility"] = {
        "backward_compatible": False,
        "notes": "Experimental variant; behavior may diverge from base skill.",
    }
    metadata["source"] = {
        "kind": "experiment",
        "repo_url": "local://house-skills/young",
        "skill_path": str(target.relative_to(root)),
        "author": "wangwu",
        "base_skill_path": str(base_dir.relative_to(root)),
        "variant": variant_label,
        "notes": notes,
    }
    metadata["experiment"] = {
        "base_skill_path": str(base_dir.relative_to(root)),
        "variant": variant_label,
        "notes": notes,
        "status": "running",
    }
    write_json(target / "metadata.json", metadata)

    note_path = target / "references" / "experiment-notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        f"# Experiment Notes\n\n- Base: {base_dir.relative_to(root)}\n- Variant: {variant_label}\n- Notes: {notes or 'n/a'}\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    target = create_experiment(root, args.base, args.variant, args.notes)
    print(f"Created skill experiment: {target.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
