#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

from skill_library_utils import (
    is_expired,
    load_skill_metadata,
    locate_library_root,
    relative_to_root,
    skill_stage,
    usage_tracking_mode,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local skill catalog.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def read_tracked_repos(root: Path) -> list[dict]:
    tracked_file = root / "catalog" / "tracked_repos.json"
    data = json.loads(tracked_file.read_text(encoding="utf-8"))
    return data["repos"]


def git_output(repo_path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def parse_skill_file(skill_file: Path, repo_root: Path, library_root: Path) -> dict:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    frontmatter = {}

    if len(lines) >= 3 and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                for raw_line in lines[1:index]:
                    if ":" not in raw_line:
                        continue
                    key, value = raw_line.split(":", 1)
                    frontmatter[key.strip()] = value.strip().strip('"')
                break

    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    metadata_path, metadata = load_skill_metadata(skill_file.parent, repo_root)
    lifecycle_stage = skill_stage(metadata)
    skill_root = metadata_path.parent if metadata_path else skill_file.parent

    return {
        "skill_file": str(skill_file.relative_to(repo_root)),
        "skill_dir": str(skill_file.parent.relative_to(repo_root)),
        "skill_root_dir": str(skill_root.relative_to(repo_root)),
        "skill_root_path": relative_to_root(skill_root, library_root),
        "metadata_file": relative_to_root(metadata_path, library_root),
        "name": frontmatter.get("name", ""),
        "description": frontmatter.get("description", ""),
        "title": title,
        "lifecycle_stage": lifecycle_stage,
        "lifecycle_status": metadata.get("status", ""),
        "schema_version": metadata.get("schema_version"),
        "version": metadata.get("version", ""),
        "owner": metadata.get("owner", ""),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "last_used_at": metadata.get("last_used_at"),
        "use_count": int(metadata.get("use_count", 0) or 0),
        "usage_tracking_mode": usage_tracking_mode(metadata),
        "compatibility_backward_compatible": (
            metadata.get("compatibility", {}).get("backward_compatible")
            if isinstance(metadata.get("compatibility"), dict)
            else None
        ),
        "replaces_count": (
            len(metadata.get("replaces", []))
            if isinstance(metadata.get("replaces"), list)
            else 0
        ),
        "expires_at": metadata.get("expires_at"),
        "expired": is_expired(metadata),
        "source": metadata.get("source", {}),
    }


def build_catalog(root: Path, repos: list[dict]) -> dict:
    repo_summaries = []
    skill_entries = []
    lifecycle_counts = {
        "core": 0,
        "young": 0,
        "archive": 0,
        "upstream": 0,
    }

    for repo in repos:
        repo_path = root / repo["local_dir"]
        summary = {
            **repo,
            "exists": repo_path.exists(),
            "path": str(repo_path),
            "origin_url": "",
            "head": "",
            "skill_count": 0,
            "sample_skills": [],
            "lifecycle_counts": {
                "core": 0,
                "young": 0,
                "archive": 0,
                "upstream": 0,
            },
        }

        if not repo_path.exists():
            repo_summaries.append(summary)
            continue

        summary["origin_url"] = git_output(repo_path, "remote", "get-url", "origin")
        summary["head"] = git_output(repo_path, "rev-parse", "--short", "HEAD")

        skill_files = sorted(repo_path.rglob("SKILL.md"))
        summary["skill_count"] = len(skill_files)
        summary["sample_skills"] = [
            str(path.relative_to(repo_path)) for path in skill_files[:5]
        ]

        for skill_file in skill_files:
            parsed = parse_skill_file(skill_file, repo_path, root)
            stage = parsed["lifecycle_stage"]
            summary["lifecycle_counts"][stage] = summary["lifecycle_counts"].get(stage, 0) + 1
            lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
            skill_entries.append(
                {
                    "repo_id": repo["id"],
                    "repo_local_dir": repo["local_dir"],
                    "repo_kind": repo["kind"],
                    "repo_priority": repo["priority"],
                    "repo_tags": repo["tags"],
                    "repo_notes": repo["notes"],
                    "repo_url": repo["repo_url"],
                    **parsed,
                }
            )

        repo_summaries.append(summary)

    repo_summaries.sort(key=lambda item: (-item["skill_count"], item["id"]))
    skill_entries.sort(
        key=lambda item: (
            item["repo_id"],
            item["skill_dir"],
            item["skill_file"],
        )
    )

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "root": str(root),
        "repo_count": len(repo_summaries),
        "skill_count": len(skill_entries),
        "lifecycle_counts": lifecycle_counts,
        "repos": repo_summaries,
        "skills": skill_entries,
    }


def write_catalog(root: Path, catalog: dict) -> None:
    catalog_path = root / "catalog" / "skill_catalog.json"
    catalog_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def render_markdown(catalog: dict) -> str:
    lines = [
        "# Skill Catalog",
        "",
        f"- Generated: `{catalog['generated_at']}`",
        f"- Root: `{catalog['root']}`",
        f"- Tracked repositories: `{catalog['repo_count']}`",
        f"- Indexed `SKILL.md` files: `{catalog['skill_count']}`",
        f"- Lifecycle counts: `core={catalog['lifecycle_counts']['core']}`, `young={catalog['lifecycle_counts']['young']}`, `archive={catalog['lifecycle_counts']['archive']}`, `upstream={catalog['lifecycle_counts']['upstream']}`",
        "",
        "## How To Query",
        "",
        "```bash",
        "python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root \"$PWD\" --query \"react playwright\"",
        "```",
        "",
        "## Repository Summary",
        "",
        "| Local Dir | Kind | Priority | Skills | Lifecycle | Tags | Source |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]

    for repo in catalog["repos"]:
        tags = ", ".join(repo["tags"])
        source = repo["repo_url"]
        lifecycle = ", ".join(
            f"{stage}={count}"
            for stage, count in repo["lifecycle_counts"].items()
            if count
        ) or "n/a"
        lines.append(
            f"| `{repo['local_dir']}` | `{repo['kind']}` | `{repo['priority']}` | {repo['skill_count']} | {lifecycle} | {tags} | {source} |"
        )

    lines.extend(
        [
            "",
            "## Highest-Signal Repositories",
            "",
        ]
    )

    for repo in catalog["repos"][:10]:
        sample = ", ".join(repo["sample_skills"][:3]) if repo["sample_skills"] else "n/a"
        lines.append(
            f"- `{repo['local_dir']}`: {repo['skill_count']} skills, tags `{', '.join(repo['tags'])}`, samples `{sample}`"
        )

    return "\n".join(lines) + "\n"


def write_markdown(root: Path, catalog: dict) -> None:
    catalog_md = root / "CATALOG.md"
    catalog_md.write_text(render_markdown(catalog), encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    repos = read_tracked_repos(root)
    catalog = build_catalog(root, repos)
    write_catalog(root, catalog)
    write_markdown(root, catalog)
    print(
        f"Indexed {catalog['skill_count']} skills across {catalog['repo_count']} repositories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
