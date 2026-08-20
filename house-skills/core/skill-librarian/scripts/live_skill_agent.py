#!/usr/bin/env python3

from __future__ import annotations

import argparse
import time
from pathlib import Path

from daily_skill_watch import build_report, print_report, write_memory
from skill_library_utils import ensure_within_root, library_lock, locate_library_root, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live skill librarian maintenance loop.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Clone or restore upstream repositories to their committed lock entries",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=0,
        help="Run continuously at this interval. Default 0 runs once.",
    )
    parser.add_argument(
        "--memory-path",
        type=Path,
        default=None,
        help="Optional memory output path",
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=None,
        help="Optional JSON report output path",
    )
    return parser.parse_args()


def run_once(root: Path, pull: bool, memory_path: Path, json_path: Path) -> dict:
    with library_lock(root):
        report = build_report(root, pull_requested=pull)
        write_memory(memory_path, report)
        report["memory_written"] = True
        report["memory_path"] = str(memory_path)
        report["json_path"] = str(json_path)
        write_json(json_path, report)
    print_report(report, memory_path, json_path)
    return report


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    memory_path = ensure_within_root(
        args.memory_path or (root / "memory.md"), root, label="memory path"
    )
    json_path = ensure_within_root(
        args.json_path or (root / "catalog" / "live_skill_agent_last.json"),
        root,
        label="JSON report path",
    )

    if args.interval_minutes <= 0:
        report = run_once(root, args.pull, memory_path, json_path)
        return 0 if report["overall_status"] == "success" else 1

    while True:
        run_once(root, args.pull, memory_path, json_path)
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    raise SystemExit(main())
