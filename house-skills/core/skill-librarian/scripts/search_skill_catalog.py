#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from skill_library_utils import locate_library_root, read_json

MAX_QUERY_CHARS = 2_000
MAX_RESULTS = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the local skill catalog.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--query", required=True, help="Query text")
    parser.add_argument("--limit", type=int, default=10, help="Maximum matches")
    parser.add_argument(
        "--stage",
        choices=["any", "core", "young", "archive", "upstream"],
        default="any",
        help="Limit results to a lifecycle stage",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived or expired house skills in search results",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def score_entry(entry: dict, query_tokens: list[str], query_phrase: str) -> int:
    haystacks = {
        "name": (entry.get("name", "") + " " + entry.get("title", "")).lower(),
        "description": entry.get("description", "").lower(),
        "path": (entry.get("skill_dir", "") + " " + entry.get("skill_file", "")).lower(),
        "repo": (
            entry.get("repo_id", "")
            + " "
            + " ".join(entry.get("repo_tags", []))
            + " "
            + entry.get("repo_notes", "")
        ).lower(),
    }

    score = 0
    if query_phrase and query_phrase in haystacks["name"]:
        score += 50
    if query_phrase and query_phrase in haystacks["description"]:
        score += 25

    for token in query_tokens:
        if token in haystacks["name"]:
            score += 20
        if token in haystacks["description"]:
            score += 10
        if token in haystacks["path"]:
            score += 8
        if token in haystacks["repo"]:
            score += 6

    if entry.get("repo_priority") == "core":
        score += 4
    elif entry.get("repo_priority") == "high":
        score += 2

    lifecycle_stage = entry.get("lifecycle_stage", "upstream")
    if lifecycle_stage == "core":
        score += 20
    elif lifecycle_stage == "young":
        score += 10
    elif lifecycle_stage == "archive":
        score -= 40

    if entry.get("expired"):
        score -= 80

    if entry.get("usage_tracking_mode") in {"manual", "hub"}:
        score += min(int(entry.get("use_count", 0) or 0), 5) * 3

    return score


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    catalog_path = root / "catalog" / "skill_catalog.json"
    if args.limit < 1 or args.limit > MAX_RESULTS:
        raise SystemExit(f"--limit must be between 1 and {MAX_RESULTS}")
    if not args.query.strip():
        raise SystemExit("--query must not be empty")
    if len(args.query) > MAX_QUERY_CHARS:
        raise SystemExit(f"--query exceeds {MAX_QUERY_CHARS} characters")
    if not catalog_path.exists():
        builder = Path(__file__).with_name("build_skill_catalog.py")
        result = subprocess.run([sys.executable, str(builder), "--root", str(root)], check=False)
        if result.returncode != 0:
            return result.returncode
    catalog = read_json(catalog_path)
    if not isinstance(catalog.get("skills"), list):
        raise SystemExit("catalog is invalid: missing skills list")

    query_phrase = " ".join(args.query.lower().split())
    query_tokens = [token for token in query_phrase.split() if token]

    scored = []
    for entry in catalog["skills"]:
        stage = entry.get("lifecycle_stage", "upstream")
        if args.stage != "any" and stage != args.stage:
            continue
        if not args.include_archived and (stage == "archive" or entry.get("expired")):
            continue
        score = score_entry(entry, query_tokens, query_phrase)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda item: (-item[0], item[1]["repo_id"], item[1]["skill_dir"]))

    for index, (score, entry) in enumerate(scored[: args.limit], start=1):
        description = entry.get("description") or entry.get("title") or "No description"
        stage = entry.get("lifecycle_stage", "upstream")
        display_path = entry.get("skill_root_path") or entry["repo_local_dir"]
        print(f"{index}. [{score}] [{stage}] {entry['repo_id']} :: {display_path} :: {description}")

    if not scored:
        print("No matches. Rebuild the catalog or broaden the query.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
