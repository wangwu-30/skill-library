#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from skill_library_utils import locate_library_root


REQUIRED_FIELDS = ["id", "local_dir", "repo_url", "kind", "priority", "tags", "notes"]
ALLOWED_KINDS = {
    "house-skill-space",
    "official-library",
    "community-library",
    "domain-library",
    "aggregator",
    "curated-list",
    "reference-spec",
}
ALLOWED_PRIORITIES = {"core", "high", "medium", "low"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit tracked repository integrity.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--require-local",
        action="store_true",
        help="Fail when tracked upstream mirrors have not been refreshed into local directories",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def read_tracked_repos(root: Path) -> list[dict]:
    tracked_file = root / "catalog" / "tracked_repos.json"
    data = json.loads(tracked_file.read_text(encoding="utf-8"))
    return data["repos"]


def read_blacklisted_repos(root: Path) -> list[dict]:
    blacklist_file = root / "catalog" / "blacklisted_repos.json"
    if not blacklist_file.exists():
        return []
    data = json.loads(blacklist_file.read_text(encoding="utf-8"))
    return data.get("repos", [])


def count_skill_files(repo_path: Path) -> int:
    return sum(1 for _ in repo_path.rglob("SKILL.md"))


def blacklisted_match(repo: dict, blacklisted: list[dict]) -> str | None:
    for blocked in blacklisted:
        if repo.get("id") and repo.get("id") == blocked.get("id"):
            return f"repo is blacklisted by id: {repo['id']}"
        if repo.get("local_dir") and repo.get("local_dir") == blocked.get("local_dir"):
            return f"repo is blacklisted by local_dir: {repo['local_dir']}"
        if repo.get("repo_url") and repo.get("repo_url") == blocked.get("repo_url"):
            return f"repo is blacklisted by repo_url: {repo['repo_url']}"
    return None


def audit_repo(
    root: Path,
    repo: dict,
    seen_ids: set[str],
    seen_dirs: set[str],
    blacklisted: list[dict],
    require_local: bool,
) -> list[str]:
    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in repo:
            issues.append(f"missing field: {field}")

    repo_id = repo.get("id")
    local_dir = repo.get("local_dir")
    kind = repo.get("kind")
    priority = repo.get("priority")
    repo_url = repo.get("repo_url")
    tags = repo.get("tags")
    notes = repo.get("notes")

    if repo_id:
        if repo_id in seen_ids:
            issues.append(f"duplicate id: {repo_id}")
        seen_ids.add(repo_id)

    if local_dir:
        if local_dir in seen_dirs:
            issues.append(f"duplicate local_dir: {local_dir}")
        seen_dirs.add(local_dir)

    if kind and kind not in ALLOWED_KINDS:
        issues.append(f"unknown kind: {kind}")
    if priority and priority not in ALLOWED_PRIORITIES:
        issues.append(f"unknown priority: {priority}")
    if not isinstance(tags, list):
        issues.append("tags must be a list")
    if not isinstance(notes, str) or not notes.strip():
        issues.append("notes must be a non-empty string")

    blocked = blacklisted_match(repo, blacklisted)
    if blocked:
        issues.append(blocked)

    is_local = isinstance(repo_url, str) and repo_url.startswith("local://")

    if kind == "house-skill-space":
        if not is_local:
            issues.append("house-skill-space must use local:// repo_url")
    else:
        if is_local:
            issues.append("non-house repo should not use local:// repo_url")

    if not local_dir:
        return issues

    repo_path = root / local_dir
    if not repo_path.exists():
        if require_local or is_local:
            issues.append(f"missing local path: {local_dir}")
        return issues

    skill_count = count_skill_files(repo_path)

    if kind in {"official-library", "community-library", "domain-library", "aggregator"} and skill_count == 0:
        issues.append(f"{kind} has no SKILL.md files")

    if kind == "curated-list" and skill_count == 0:
        issues.append("curated-list has no SKILL.md files; likely low-signal for this library")

    if kind == "reference-spec" and skill_count > 0:
        issues.append("reference-spec unexpectedly contains SKILL.md files")

    return issues


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    repos = read_tracked_repos(root)
    blacklisted = read_blacklisted_repos(root)
    seen_ids: set[str] = set()
    seen_dirs: set[str] = set()

    failing = 0
    for repo in repos:
        issues = audit_repo(root, repo, seen_ids, seen_dirs, blacklisted, args.require_local)
        label = repo.get("local_dir", repo.get("id", "<unknown>"))
        if issues:
            failing += 1
            print(f"FAIL  {label}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"OK    {label}")

    print(f"Summary: repos={len(repos)}, failing={failing}, passing={len(repos) - failing}")
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
