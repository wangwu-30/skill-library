#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from build_skill_catalog import build_catalog, read_tracked_repos, write_catalog, write_markdown
from gc_young_skills import review_young_skills
from refresh_tracked_repos import STATUS_FAIL, refresh_repositories, summarize_results
from skill_library_utils import iso_now, locate_library_root, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic daily skill library maintenance.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Attempt git pull --ff-only for clean upstream repositories with remotes",
    )
    parser.add_argument(
        "--memory-path",
        type=Path,
        default=None,
        help="Optional path for the markdown run memory (defaults to <root>/memory.md)",
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=None,
        help="Optional path for the machine-readable run report (defaults to <root>/catalog/daily_skill_watch_last.json)",
    )
    return parser.parse_args()


def remote_refresh_status(refresh_summary: dict, pull_requested: bool) -> str:
    if not pull_requested:
        return "not-requested"
    if refresh_summary["refreshable"] == 0:
        return "skipped"
    if refresh_summary["pull_fail"] > 0:
        return "failed"
    return "succeeded"


def overall_status(remote_status: str) -> str:
    if remote_status == "failed":
        return "partial-success"
    return "success"


def build_report(root: Path, pull_requested: bool) -> dict:
    refresh_results = refresh_repositories(root, pull=pull_requested)
    refresh_summary = summarize_results(refresh_results)
    tracked_repos = read_tracked_repos(root)
    catalog = build_catalog(root, tracked_repos)
    write_catalog(root, catalog)
    write_markdown(root, catalog)
    gc_results, gc_summary = review_young_skills(root, apply=False)

    remote_status = remote_refresh_status(refresh_summary, pull_requested)
    failed_refreshes = [
        {
            "local_dir": result["local_dir"],
            "error": result["error"],
        }
        for result in refresh_results
        if result["status"] == STATUS_FAIL
    ]

    report = {
        "run_at": iso_now(),
        "root": str(root),
        "overall_status": overall_status(remote_status),
        "refresh": {
            "pull_requested": pull_requested,
            "remote_status": remote_status,
            "summary": refresh_summary,
            "results": refresh_results,
            "failed_refreshes": failed_refreshes,
        },
        "catalog": {
            "generated_at": catalog["generated_at"],
            "repo_count": catalog["repo_count"],
            "skill_count": catalog["skill_count"],
            "lifecycle_counts": catalog["lifecycle_counts"],
        },
        "lifecycle": {
            "summary": gc_summary,
            "results": gc_results,
        },
        "remote_recommendations": {
            "status": "skipped" if remote_status != "succeeded" else "not-run",
            "reason": (
                "Remote refresh did not succeed; skip remote-derived repository recommendations."
                if remote_status != "succeeded"
                else "Deterministic daily maintenance does not perform remote discovery."
            ),
        },
        "memory_written": False,
    }
    return report


def render_memory_entry(report: dict) -> str:
    refresh = report["refresh"]
    refresh_summary = refresh["summary"]
    catalog = report["catalog"]
    lifecycle = report["lifecycle"]["summary"]
    remote_status = refresh["remote_status"]

    lines = [
        f"## {report['run_at']}",
        "",
        f"- Overall status: `{report['overall_status']}`",
        (
            f"- Remote refresh: `{remote_status}` "
            f"(pull_requested={str(refresh['pull_requested']).lower()}, "
            f"refreshable={refresh_summary['refreshable']}, "
            f"pull_ok={refresh_summary['pull_ok']}, "
            f"pull_fail={refresh_summary['pull_fail']})"
        ),
        (
            f"- Repo counts: `local_workspaces={refresh_summary['local_workspaces']}`, "
            f"`dirty={refresh_summary['dirty']}`, `missing={refresh_summary['missing']}`, "
            f"`no_remote={refresh_summary['no_remote']}`"
        ),
        (
            f"- Catalog: `{catalog['skill_count']} skills / {catalog['repo_count']} repos` "
            f"(generated `{catalog['generated_at']}`)"
        ),
        (
            f"- Lifecycle: `promoted={lifecycle['promoted']}`, "
            f"`archived={lifecycle['archived']}`, `kept={lifecycle['kept']}`, "
            f"`ttl_days={lifecycle['ttl_days']}`, "
            f"`promote_min_uses={lifecycle['promote_min_uses']}`, "
            f"`promote_recent_days={lifecycle['promote_recent_days']}`, "
            f"`auto_promote={str(lifecycle['auto_promote']).lower()}`, "
            f"`auto_archive={str(lifecycle['auto_archive']).lower()}`"
        ),
        (
            f"- Remote-derived recommendations: `{report['remote_recommendations']['status']}` "
            f"({report['remote_recommendations']['reason']})"
        ),
    ]

    failed_refreshes = refresh["failed_refreshes"]
    if failed_refreshes:
        sample = ", ".join(
            f"{item['local_dir']}: {item['error']}" for item in failed_refreshes[:3]
        )
        lines.append(f"- Refresh failures sample: `{sample}`")

    lines.extend(["", ""])
    return "\n".join(lines)


def write_memory(memory_path: Path, report: dict) -> None:
    existing = ""
    if memory_path.exists():
        existing = memory_path.read_text(encoding="utf-8")

    if not existing:
        existing = "# Skill Library Run Memory\n\n"

    memory_path.write_text(existing + render_memory_entry(report), encoding="utf-8")


def print_report(report: dict, memory_path: Path, json_path: Path) -> None:
    refresh = report["refresh"]
    refresh_summary = refresh["summary"]
    catalog = report["catalog"]
    lifecycle = report["lifecycle"]["summary"]

    print(
        f"Overall: {report['overall_status']} | "
        f"remote_refresh={refresh['remote_status']} | "
        f"catalog={catalog['skill_count']} skills/{catalog['repo_count']} repos"
    )
    print(
        "Refresh: "
        f"local_workspaces={refresh_summary['local_workspaces']}, "
        f"dirty={refresh_summary['dirty']}, "
        f"refreshable={refresh_summary['refreshable']}, "
        f"pull_ok={refresh_summary['pull_ok']}, "
        f"pull_fail={refresh_summary['pull_fail']}"
    )
    print(
        "Lifecycle: "
        f"promoted={lifecycle['promoted']}, "
        f"archived={lifecycle['archived']}, "
        f"kept={lifecycle['kept']}, "
        f"auto_promote={str(lifecycle['auto_promote']).lower()}, "
        f"auto_archive={str(lifecycle['auto_archive']).lower()}"
    )
    print(
        "Remote-derived recommendations: "
        f"{report['remote_recommendations']['status']} "
        f"({report['remote_recommendations']['reason']})"
    )
    print(f"Memory: {memory_path}")
    print(f"JSON report: {json_path}")


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    memory_path = args.memory_path or (root / "memory.md")
    json_path = args.json_path or (root / "catalog" / "daily_skill_watch_last.json")

    report = build_report(root, pull_requested=args.pull)
    write_memory(memory_path, report)
    report["memory_written"] = True
    report["memory_path"] = str(memory_path)
    report["json_path"] = str(json_path)
    write_json(json_path, report)
    print_report(report, memory_path, json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
