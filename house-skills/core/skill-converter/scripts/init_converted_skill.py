#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import yaml

METADATA_SCHEMA_VERSION = 2
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 63
MAX_DESCRIPTION_LENGTH = 1024


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
        choices=["young"],
        default="young",
        help="Lifecycle stage for the new house skill (conversion always starts in young)",
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
    if (
        not isinstance(raw_name, str)
        or len(raw_name) > MAX_NAME_LENGTH
        or not NAME_PATTERN.fullmatch(raw_name)
    ):
        raise ValueError("skill name must be lowercase hyphen-case and at most 63 characters")
    return raw_name


def validate_single_line(
    value: str, field: str, max_length: int, *, allow_empty: bool = False
) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{field} must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field} must be single-line")
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")
    return value


def ensure_within(path: Path, parent: Path, field: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay within the skill-library repository") from exc
    return resolved


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
    if not (library_root / "catalog" / "tracked_repos.json").is_file():
        raise ValueError("root must be the skill-library repository root")
    lifecycle_config = load_lifecycle_config(library_root)
    skill_name = normalize_name(args.name)
    description = validate_single_line(args.description, "description", MAX_DESCRIPTION_LENGTH)
    source_repo = validate_single_line(args.source_repo, "source repository", 2048)
    source_path = validate_single_line(args.source_path, "source path", 2048)
    author_line = validate_single_line(args.author, "author", 256, allow_empty=True) or "Unknown"
    if args.dest_root is not None:
        destination_root = ensure_within(args.dest_root, library_root, "dest-root")
    else:
        destination_root = library_root / "house-skills" / args.stage
    allowed_stage_root = (library_root / "house-skills" / "young").resolve()
    destination_root = ensure_within(destination_root, allowed_stage_root, "dest-root")
    skill_dir = destination_root / skill_name

    if skill_dir.exists():
        raise SystemExit(f"Destination already exists: {skill_dir}")

    title = title_from_name(skill_name)
    now = dt.datetime.now(dt.UTC)
    ttl_days = (
        args.ttl_days
        if args.ttl_days is not None
        else int(lifecycle_config["young"]["default_ttl_days"])
    )
    if ttl_days <= 0:
        raise ValueError("ttl-days must be positive")
    expires_at = (now + dt.timedelta(days=ttl_days)).isoformat()

    frontmatter = yaml.safe_dump(
        {"name": skill_name, "description": description}, sort_keys=False, allow_unicode=True
    ).strip()
    skill_md = f"""---
{frontmatter}
---

# Purpose

Use this skill for the normalized workflow derived from the upstream source.

## When To Use

- Use when the task matches: {description}

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

- [references/source-notes.md](references/source-notes.md)
"""

    metadata_json = (
        json.dumps(
            {
                "schema_version": METADATA_SCHEMA_VERSION,
                "version": default_skill_version("young"),
                "owner": "wangwu",
                "stage": "young",
                "status": "active",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "last_used_at": None,
                "use_count": 0,
                "expires_at": expires_at,
                "usage_tracking": {"mode": "none"},
                "derives_from": None,
                "replaces": [],
                "compatibility": {"backward_compatible": True, "notes": ""},
                "source": {
                    "kind": "converted",
                    "repo_url": source_repo,
                    "skill_path": source_path,
                    "author": author_line,
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    openai_yaml = yaml.safe_dump(
        {
            "interface": {
                "display_name": title,
                "short_description": "Convert upstream material into a local house skill",
                "default_prompt": f"Use ${skill_name} to handle the normalized workflow.",
            },
            "policy": {"allow_implicit_invocation": True},
        },
        sort_keys=False,
        allow_unicode=True,
    )

    source_notes = f"""# Source Notes

- Upstream repository: {source_repo}
- Upstream path: {source_path}
- Upstream author: {author_line}
- Conversion notes: Fill in what was preserved, removed, and rewritten.
"""

    write_text(skill_dir / "SKILL.md", skill_md)
    write_text(skill_dir / "metadata.json", metadata_json)
    write_text(skill_dir / "agents" / "openai.yaml", openai_yaml)
    write_text(skill_dir / "references" / "source-notes.md", source_notes)
    print(f"Created normalized young skill scaffold at {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
