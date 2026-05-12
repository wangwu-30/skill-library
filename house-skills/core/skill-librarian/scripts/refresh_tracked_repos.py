#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from skill_library_utils import locate_library_root


STATUS_SKIP_LOCAL = "skip_local"
STATUS_MISSING = "missing"
STATUS_SKIP_NOT_GIT = "skip_not_git"
STATUS_SKIP_NO_REMOTE = "skip_no_remote"
STATUS_SKIP_DIRTY = "skip_dirty"
STATUS_READY = "ready"
STATUS_OK = "ok"
STATUS_FAIL = "fail"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh tracked git repositories.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Run git pull --ff-only on clean repositories with remotes",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def read_tracked_repos(root: Path) -> list[dict]:
    tracked_file = root / "catalog" / "tracked_repos.json"
    data = json.loads(tracked_file.read_text(encoding="utf-8"))
    return data["repos"]


def run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def inspect_repo(root: Path, repo: dict, pull: bool = False) -> dict:
    repo_path = root / repo["local_dir"]
    result = {
        "id": repo["id"],
        "local_dir": repo["local_dir"],
        "path": str(repo_path),
        "repo_url": repo["repo_url"],
        "status": "",
        "remote_url": "",
        "head_before": "",
        "head_after": "",
        "error": "",
    }

    if repo["repo_url"].startswith("local://"):
        result["status"] = STATUS_SKIP_LOCAL
        return result

    if not repo_path.exists():
        result["status"] = STATUS_MISSING
        result["error"] = "path does not exist"
        return result

    probe = run_git(repo_path, "rev-parse", "--is-inside-work-tree")
    if probe.returncode != 0:
        result["status"] = STATUS_SKIP_NOT_GIT
        result["error"] = "not a git repository"
        return result

    remote = run_git(repo_path, "remote", "get-url", "origin")
    remote_url = remote.stdout.strip()
    result["remote_url"] = remote_url
    if remote.returncode != 0 or not remote_url or remote_url.startswith("local://"):
        result["status"] = STATUS_SKIP_NO_REMOTE
        result["error"] = "no remote origin"
        return result

    dirty = run_git(repo_path, "status", "--porcelain")
    if dirty.stdout.strip():
        result["status"] = STATUS_SKIP_DIRTY
        result["error"] = "working tree is dirty"
        return result

    head_before = run_git(repo_path, "rev-parse", "--short", "HEAD").stdout.strip()
    result["head_before"] = head_before

    if not pull:
        result["status"] = STATUS_READY
        result["head_after"] = head_before
        return result

    pulled = run_git(repo_path, "pull", "--ff-only")
    if pulled.returncode != 0:
        result["status"] = STATUS_FAIL
        result["error"] = (pulled.stderr or pulled.stdout).strip().replace("\n", " ")
        result["head_after"] = head_before
        return result

    head_after = run_git(repo_path, "rev-parse", "--short", "HEAD").stdout.strip()
    result["status"] = STATUS_OK
    result["head_after"] = head_after
    return result


def refresh_repositories(root: Path, pull: bool = False) -> list[dict]:
    repos = read_tracked_repos(root)
    return [inspect_repo(root, repo, pull=pull) for repo in repos]


def format_result(result: dict, pull: bool) -> str:
    label = result["local_dir"]
    status = result["status"]
    if status == STATUS_SKIP_LOCAL:
        return f"SKIP  {label}: local workspace"
    if status == STATUS_MISSING:
        return f"MISS  {label}: {result['error']}"
    if status == STATUS_SKIP_NOT_GIT:
        return f"SKIP  {label}: {result['error']}"
    if status == STATUS_SKIP_NO_REMOTE:
        return f"SKIP  {label}: {result['error']}"
    if status == STATUS_SKIP_DIRTY:
        return f"SKIP  {label}: {result['error']}"
    if status == STATUS_READY:
        return f"READY {label}: clean repo at {result['head_before']}"
    if status == STATUS_FAIL:
        return f"FAIL  {label}: {result['error']}"
    if status == STATUS_OK:
        if not pull or result["head_after"] == result["head_before"]:
            return f"OK    {label}: already up to date at {result['head_after']}"
        return f"OK    {label}: {result['head_before']} -> {result['head_after']}"
    raise ValueError(f"Unknown refresh status: {status}")


def summarize_results(results: list[dict]) -> dict:
    summary = {
        "total": len(results),
        "local_workspaces": 0,
        "missing": 0,
        "not_git": 0,
        "no_remote": 0,
        "dirty": 0,
        "refreshable": 0,
        "ready": 0,
        "pull_ok": 0,
        "pull_fail": 0,
    }
    for result in results:
        status = result["status"]
        if status == STATUS_SKIP_LOCAL:
            summary["local_workspaces"] += 1
        elif status == STATUS_MISSING:
            summary["missing"] += 1
        elif status == STATUS_SKIP_NOT_GIT:
            summary["not_git"] += 1
        elif status == STATUS_SKIP_NO_REMOTE:
            summary["no_remote"] += 1
        elif status == STATUS_SKIP_DIRTY:
            summary["dirty"] += 1
        elif status == STATUS_READY:
            summary["refreshable"] += 1
            summary["ready"] += 1
        elif status == STATUS_OK:
            summary["refreshable"] += 1
            summary["pull_ok"] += 1
        elif status == STATUS_FAIL:
            summary["refreshable"] += 1
            summary["pull_fail"] += 1
    return summary


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    results = refresh_repositories(root, pull=args.pull)
    for result in results:
        print(format_result(result, pull=args.pull))

    summary = summarize_results(results)
    if args.pull:
        print(
            "Summary: "
            f"refreshable={summary['refreshable']}, "
            f"pull_ok={summary['pull_ok']}, "
            f"pull_fail={summary['pull_fail']}, "
            f"dirty={summary['dirty']}, "
            f"local_workspaces={summary['local_workspaces']}"
        )
    else:
        print(
            "Summary: "
            f"refreshable={summary['refreshable']}, "
            f"ready={summary['ready']}, "
            f"dirty={summary['dirty']}, "
            f"local_workspaces={summary['local_workspaces']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
