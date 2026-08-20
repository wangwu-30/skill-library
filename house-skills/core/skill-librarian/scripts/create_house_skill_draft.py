#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

import yaml
from skill_library_utils import (
    METADATA_SCHEMA_VERSION,
    default_skill_version,
    load_lifecycle_config,
    locate_library_root,
    write_json,
)

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 63
MAX_DESCRIPTION_LENGTH = 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a young house-skill draft scaffold.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--name", required=True, help="Skill name")
    parser.add_argument("--description", required=True, help="Trigger description")
    parser.add_argument(
        "--source-note",
        default="Created from a local consultation gap.",
        help="Short note explaining why this draft exists",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Optional task context to embed in the draft skill",
    )
    parser.add_argument(
        "--source-summary",
        default="",
        help="Optional nearby examples to embed in the draft skill",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=None,
        help="Override the configured young-skill TTL",
    )
    return parser.parse_args()


def normalize_name(raw_name: str) -> str:
    if (
        not isinstance(raw_name, str)
        or len(raw_name) > MAX_NAME_LENGTH
        or not NAME_PATTERN.fullmatch(raw_name)
    ):
        raise ValueError("skill name must be lowercase hyphen-case and at most 63 characters")
    return raw_name


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def markdown_block(value: str, fallback: str) -> str:
    cleaned = value.strip()
    return cleaned if cleaned else fallback


def validate_single_line(value: str, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field} must be single-line")
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")
    return value


def yaml_document(value: dict[str, object]) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).strip()


def build_skill_md(name: str, description: str, context: str, source_summary: str) -> str:
    frontmatter = yaml_document({"name": name, "description": description})
    return f"""---
{frontmatter}
---

# Purpose

Use this skill when the task matches the trigger and no stronger existing house skill fits. This
draft is meant to be usable immediately, then improved or archived after real use.

## When To Use

- Use when: {description}

## Request Context

{markdown_block(context, "No extra context was provided.")}

## Nearby Examples

{markdown_block(source_summary, "No close catalog examples were found.")}

## Inputs

- The user's concrete task
- Relevant repo, tool, domain, or artifact context
- Any constraints, safety boundaries, or expected output shape

## Workflow

1. Confirm the task really matches this skill and restate the concrete target.
2. Inspect the target repo, files, tools, credentials, and external service assumptions before acting.
3. If nearby examples are listed above, read only the strongest relevant one and adapt the workflow.
4. Execute the smallest practical path that solves the task; avoid turning the temporary skill into a broad framework.
5. Capture any reusable steps, commands, gotchas, or verification checks discovered during execution.
6. Verify the output before reporting completion.

## Output Contract

Return:

1. the result
2. important assumptions or boundaries
3. verification performed
4. remaining gaps, if any

## Validation

- The trigger is specific enough for another agent to decide when to use it.
- The workflow changes execution behavior, not just tone.
- The output shape is clear.
- Completion can be checked.
- If this skill is useful more than once, replace this draft with a tighter version based on observed work.

## Sources

- [references/source-notes.md](references/source-notes.md)
"""


def build_openai_yaml(name: str, description: str) -> str:
    title = title_from_name(name)
    short = description if len(description) <= 64 else f"{description[:61].rstrip()}..."
    if len(short) < 25:
        short = f"Use this skill to {short.rstrip('.')}"
    return yaml.safe_dump(
        {
            "interface": {
                "display_name": title,
                "short_description": short[:64],
                "default_prompt": f"Use ${name} for this task.",
            },
            "policy": {"allow_implicit_invocation": True},
        },
        sort_keys=False,
        allow_unicode=True,
    )


def create_draft(
    root: Path,
    name: str,
    description: str,
    source_note: str,
    ttl_days: int | None,
    context: str,
    source_summary: str,
) -> Path:
    root = root.resolve()
    if not (root / "catalog" / "tracked_repos.json").is_file():
        raise ValueError("root must be the skill-library repository root")
    skill_name = normalize_name(name)
    description = validate_single_line(description, "description", MAX_DESCRIPTION_LENGTH)
    source_note = validate_single_line(source_note, "source note", 1024)
    if len(context) > 20_000 or len(source_summary) > 20_000:
        raise ValueError("context and source summary must each be at most 20000 characters")
    skill_dir = root / "house-skills" / "young" / skill_name
    if skill_dir.exists():
        raise FileExistsError(f"Destination already exists: {skill_dir}")

    config = load_lifecycle_config(root)
    ttl = ttl_days if ttl_days is not None else int(config["young"]["default_ttl_days"])
    if ttl <= 0:
        raise ValueError("ttl-days must be positive")
    now = dt.datetime.now(dt.UTC)
    expires_at = now + dt.timedelta(days=ttl)

    write_text(
        skill_dir / "SKILL.md", build_skill_md(skill_name, description, context, source_summary)
    )
    write_text(skill_dir / "agents" / "openai.yaml", build_openai_yaml(skill_name, description))
    write_text(
        skill_dir / "references" / "source-notes.md",
        f"# Source Notes\n\n- Reason: {source_note}\n- Created from: local skill consultation gap\n",
    )
    metadata = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "version": default_skill_version("young"),
        "owner": "wangwu",
        "stage": "young",
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "last_used_at": None,
        "use_count": 0,
        "expires_at": expires_at.isoformat(),
        "usage_tracking": {"mode": "none"},
        "derives_from": None,
        "replaces": [],
        "compatibility": {
            "backward_compatible": True,
            "notes": "New draft scaffold.",
        },
        "source": {
            "kind": "draft",
            "repo_url": "local://house-skills/young",
            "skill_path": str(skill_dir.relative_to(root)),
            "author": "wangwu",
            "notes": source_note,
        },
    }
    write_json(skill_dir / "metadata.json", metadata)
    return skill_dir


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    skill_dir = create_draft(
        root=root,
        name=args.name,
        description=args.description,
        source_note=args.source_note,
        ttl_days=args.ttl_days,
        context=args.context,
        source_summary=args.source_summary,
    )
    print(f"Created young house-skill draft: {skill_dir.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
