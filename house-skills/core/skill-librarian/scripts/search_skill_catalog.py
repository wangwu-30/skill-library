#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from skill_library_utils import locate_library_root, read_json
from skill_retrieval import BM25

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


def score_entry(entry: dict, query_tokens: list[str], query_phrase: str) -> float:
    return BM25([entry]).score(0, query_phrase or " ".join(query_tokens))


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

    scorer = BM25(catalog["skills"])

    scored = []
    for position, entry in enumerate(catalog["skills"]):
        stage = entry.get("lifecycle_stage", "upstream")
        if args.stage != "any" and stage != args.stage:
            continue
        if not args.include_archived and (stage == "archive" or entry.get("expired")):
            continue
        score = scorer.score(position, args.query)
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
