#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


METADATA_SCHEMA_VERSION = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a normalized house skill.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--dest-root", type=Path, default=None, help="Destination root")
    parser.add_argument("--name", required=True, help="House skill name")
    parser.add_argument("--description", required=True, help="Trigger description")
    parser.add_argument("--source-repo", required=True, help="Upstream repository URL")
    parser.add_argument("--source-path", required=True, help="Upstream skill path")
    parser.add_argument("--author", default="", help="Upstream author or org")
    parser.add_argument(
        "--stage",
        choices=["young", "core", "archive"],
        default="young",
        help="Lifecycle stage for the new house skill",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=None,
        help="Override the configured expiration window for young skills",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    if cli_root:
        return cli_root.resolve()

    script_path = Path(__file__).resolve()
    candidates = [Path.cwd().resolve(), *script_path.parents]
    for candidate in candidates:
        if (candidate / "catalog" / "tracked_repos.json").exists():
            return candidate
    raise FileNotFoundError("Could not locate catalog/tracked_repos.json")


def read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_lifecycle_config(root: Path) -> dict:
    default = {
        "young": {
            "default_ttl_days": 14,
            "refresh_ttl_days_on_use": 14,
            "auto_archive_expired": True,
        },
        "promotion": {
            "min_use_count": 3,
            "recent_use_within_days": 14,
            "auto_promote_eligible": True,
        },
        "archive": {
            "hard_delete_enabled": False,
            "keep_reason_history": True,
        },
    }
    config_path = root / "house-skills" / "config" / "lifecycle.json"
    override = read_json(config_path, {})
    return merge_dict(default, override)


def merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged[key] = merge_dict(base[key], value)
        else:
            merged[key] = value
    return merged


def normalize_name(raw_name: str) -> str:
    lowered = raw_name.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def default_skill_version(stage: str) -> str:
    return "1.0.0" if stage == "core" else "0.1.0"


def main() -> int:
    args = parse_args()
    library_root = resolve_root(args.root)
    lifecycle_config = load_lifecycle_config(library_root)
    skill_name = normalize_name(args.name)
    if args.dest_root is not None:
        destination_root = args.dest_root.resolve()
    else:
        destination_root = library_root / "house-skills" / args.stage
    skill_dir = destination_root / skill_name

    if skill_dir.exists():
        raise SystemExit(f"Destination already exists: {skill_dir}")

    title = title_from_name(skill_name)
    author_line = args.author if args.author else "Unknown"
    now = dt.datetime.now(dt.timezone.utc)
    ttl_days = (
        args.ttl_days
        if args.ttl_days is not None
        else int(lifecycle_config["young"]["default_ttl_days"])
    )
    expires_at = (
        (now + dt.timedelta(days=ttl_days)).isoformat()
        if args.stage == "young"
        else None
    )

    skill_md = f"""---
name: {skill_name}
description: {args.description}
---

# Purpose

Use this skill for the normalized workflow derived from the upstream source.

## When To Use

- Use when the task matches: {args.description}

## Inputs

- Task-specific requirements
- Any environment details needed for safe execution

## Workflow

1. Review the source notes in `references/source-notes.md`.
2. Apply the smallest reusable workflow that fits the user request.
3. Load extra references or scripts only when needed.

## Output Contract

Return:

1. The result
2. Important assumptions
3. Any follow-up or validation gaps

## Validation

- Confirm the output matches the task
- Confirm any critical files or commands were checked

## Sources

- See `references/source-notes.md`
"""

    metadata_json = f"""{{
  "schema_version": {METADATA_SCHEMA_VERSION},
  "version": "{default_skill_version(args.stage)}",
  "owner": "wangwu",
  "stage": "{args.stage}",
  "status": "{"active" if args.stage == "young" else "stable" if args.stage == "core" else "archived"}",
  "created_at": "{now.isoformat()}",
  "updated_at": "{now.isoformat()}",
  "last_used_at": null,
  "use_count": 0,
  "expires_at": {json_null(expires_at)},
  "usage_tracking": {{
    "mode": "none"
  }},
  "derives_from": null,
  "replaces": [],
  "compatibility": {{
    "backward_compatible": true,
    "notes": ""
  }},
  "source": {{
    "kind": "converted",
    "repo_url": "{args.source_repo}",
    "skill_path": "{args.source_path}",
    "author": "{author_line}"
  }}
}}
"""

    openai_yaml = f"""interface:
  display_name: "{title}"
  short_description: "Normalized house skill"
  default_prompt: "Use ${skill_name} to handle the normalized workflow."

policy:
  allow_implicit_invocation: false
"""

    source_notes = f"""# Source Notes

- Upstream repository: {args.source_repo}
- Upstream path: {args.source_path}
- Upstream author: {author_line}
- Conversion notes: Fill in what was preserved, removed, and rewritten.
"""

    write_text(skill_dir / "SKILL.md", skill_md)
    write_text(skill_dir / "metadata.json", metadata_json)
    write_text(skill_dir / "agents" / "openai.yaml", openai_yaml)
    write_text(skill_dir / "references" / "source-notes.md", source_notes)
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)

    print(f"Created normalized {args.stage} skill scaffold at {skill_dir}")
    return 0


def json_null(value: str | None) -> str:
    if value is None:
        return "null"
    return f"\"{value}\""


if __name__ == "__main__":
    raise SystemExit(main())
