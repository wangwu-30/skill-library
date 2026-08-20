#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from skill_library_utils import (
    canonical_upstream_repo_url,
    locate_library_root,
    read_json,
    resolve_relative_path,
    write_json,
)

STATUS_SKIP_LOCAL = "skip_local"
STATUS_MISSING = "missing"
STATUS_READY = "ready"
STATUS_OK = "ok"
STATUS_FAIL = "fail"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
GIT_TIMEOUT_SECONDS = 120


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify or sync repositories at reviewed commits.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--sync",
        "--pull",
        dest="sync",
        action="store_true",
        help="Clone missing repositories and check out only their locked commits",
    )
    parser.add_argument(
        "--update-lock",
        action="store_true",
        help="Explicitly query remote HEADs and update the lock file for review",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def read_tracked_repos(root: Path) -> list[dict]:
    return read_json(root / "catalog" / "tracked_repos.json")["repos"]


def read_lock(root: Path) -> dict[str, dict]:
    data = read_json(root / "catalog" / "tracked_repos.lock.json")
    entries = data.get("repos", [])
    return {entry["id"]: entry for entry in entries}


def safe_repo_path(root: Path, local_dir: str) -> Path:
    try:
        return resolve_relative_path(root, local_dir, label="local_dir")
    except ValueError as exc:
        raise ValueError(f"unsafe local_dir {local_dir}: {exc}") from exc


def canonical_url(value: str) -> str:
    return canonical_upstream_repo_url(value)


def run_git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-c",
        "protocol.allow=never",
        "-c",
        "protocol.https.allow=always",
        "-c",
        "credential.helper=",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.fsmonitor=",
        "-c",
        "init.templateDir=",
        "-c",
        "http.sslVerify=true",
    ]
    if cwd is not None:
        command.extend(["-C", str(cwd)])
    command.extend(args)
    environment = os.environ.copy()
    for key in list(environment):
        if (
            key
            in {
                "GIT_ALLOW_PROTOCOL",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_ASKPASS",
                "GIT_CEILING_DIRECTORIES",
                "GIT_COMMON_DIR",
                "GIT_CONFIG_COUNT",
                "GIT_CONFIG_PARAMETERS",
                "GIT_DIR",
                "GIT_EXEC_PATH",
                "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY",
                "GIT_PROXY_COMMAND",
                "GIT_SSH",
                "GIT_SSH_COMMAND",
                "GIT_SSL_NO_VERIFY",
                "GIT_TEMPLATE_DIR",
                "GIT_WORK_TREE",
                "SSH_ASKPASS",
            }
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
        ):
            environment.pop(key, None)
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": os.devnull,
            "SSH_ASKPASS": os.devnull,
        }
    )
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            command,
            124,
            "",
            f"git command timed out after {GIT_TIMEOUT_SECONDS} seconds",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, 127, "", "git executable was not found")


def failure(repo: dict, path: Path, message: str) -> dict:
    return {
        "id": repo.get("id", ""),
        "local_dir": repo.get("local_dir", ""),
        "path": str(path),
        "repo_url": repo.get("repo_url", ""),
        "status": STATUS_FAIL,
        "remote_url": "",
        "head_before": "",
        "head_after": "",
        "error": message,
    }


def inspect_repo(root: Path, repo: dict, lock: dict | None = None, sync: bool = False) -> dict:
    try:
        repo_path = safe_repo_path(root, repo["local_dir"])
    except (KeyError, ValueError) as exc:
        return failure(repo, root, str(exc))
    result = failure(repo, repo_path, "")

    if repo.get("repo_url", "").startswith("local://"):
        result["status"] = STATUS_SKIP_LOCAL
        return result
    try:
        tracked_url = canonical_upstream_repo_url(repo.get("repo_url", ""))
        locked_url = canonical_upstream_repo_url(lock.get("repo_url", "")) if lock else ""
    except ValueError as exc:
        return failure(repo, repo_path, str(exc))
    if lock is None:
        return failure(repo, repo_path, "missing lock entry")
    locked_commit = lock.get("commit", "")
    if locked_url != tracked_url or not COMMIT_RE.fullmatch(locked_commit):
        return failure(
            repo, repo_path, "lock entry does not match tracked URL or commit is invalid"
        )

    freshly_cloned = False
    if not repo_path.exists():
        if not sync:
            result["status"] = STATUS_MISSING
            result["error"] = "path does not exist; run with --sync to bootstrap"
            return result
        cloned = run_git("clone", "--no-checkout", "--", tracked_url, str(repo_path))
        if cloned.returncode != 0:
            return failure(repo, repo_path, (cloned.stderr or cloned.stdout).strip())
        freshly_cloned = True

    probe = run_git("rev-parse", "--is-inside-work-tree", cwd=repo_path)
    if probe.returncode != 0:
        return failure(repo, repo_path, "not a git repository")
    remote = run_git("remote", "get-url", "origin", cwd=repo_path)
    result["remote_url"] = remote.stdout.strip()
    try:
        remote_matches = (
            remote.returncode == 0 and canonical_url(result["remote_url"]) == tracked_url
        )
    except ValueError:
        remote_matches = False
    if not remote_matches:
        return failure(repo, repo_path, "origin URL does not match tracked repo_url")
    if not freshly_cloned:
        dirty = run_git("status", "--porcelain", cwd=repo_path)
        if dirty.returncode != 0 or dirty.stdout.strip():
            return failure(repo, repo_path, "working tree is dirty or unreadable")

    before = run_git("rev-parse", "HEAD", cwd=repo_path)
    result["head_before"] = before.stdout.strip() if before.returncode == 0 else ""
    exists = run_git("cat-file", "-e", f"{locked_commit}^{{commit}}", cwd=repo_path)
    if exists.returncode != 0 and sync:
        fetched = run_git("fetch", "--no-tags", tracked_url, locked_commit, cwd=repo_path)
        if fetched.returncode != 0:
            return failure(repo, repo_path, (fetched.stderr or fetched.stdout).strip())
        exists = run_git("cat-file", "-e", f"{locked_commit}^{{commit}}", cwd=repo_path)
    if exists.returncode != 0:
        return failure(repo, repo_path, f"locked commit is unavailable: {locked_commit}")

    if sync and (freshly_cloned or result["head_before"] != locked_commit):
        checked = run_git("checkout", "--detach", locked_commit, cwd=repo_path)
        if checked.returncode != 0:
            return failure(repo, repo_path, (checked.stderr or checked.stdout).strip())
    after = run_git("rev-parse", "HEAD", cwd=repo_path)
    result["head_after"] = after.stdout.strip() if after.returncode == 0 else ""
    if result["head_after"] != locked_commit:
        return failure(repo, repo_path, f"HEAD is not locked commit {locked_commit}")
    result["status"] = STATUS_OK if sync else STATUS_READY
    result["error"] = ""
    return result


def refresh_repositories(root: Path, pull: bool = False, sync: bool | None = None) -> list[dict]:
    do_sync = pull if sync is None else sync
    locks = read_lock(root)
    return [
        inspect_repo(root, repo, locks.get(repo.get("id")), do_sync)
        for repo in read_tracked_repos(root)
    ]


def update_lock(root: Path) -> list[str]:
    entries = []
    errors = []
    for repo in read_tracked_repos(root):
        if repo["repo_url"].startswith("local://"):
            continue
        try:
            repo_url = canonical_upstream_repo_url(repo["repo_url"])
        except ValueError as exc:
            errors.append(f"{repo.get('id', '<unknown>')}: {exc}")
            continue
        queried = run_git("ls-remote", "--", repo_url, "HEAD")
        commit = (
            queried.stdout.split()[0] if queried.returncode == 0 and queried.stdout.split() else ""
        )
        if not COMMIT_RE.fullmatch(commit):
            errors.append(f"{repo['id']}: unable to resolve remote HEAD")
            continue
        entries.append({"id": repo["id"], "repo_url": repo_url, "commit": commit})
    if errors:
        return errors
    path = root / "catalog" / "tracked_repos.lock.json"
    write_json(path, {"schema_version": 1, "repos": entries})
    return []


def format_result(result: dict, pull: bool = False) -> str:
    labels = {
        STATUS_SKIP_LOCAL: "SKIP",
        STATUS_MISSING: "MISS",
        STATUS_READY: "READY",
        STATUS_OK: "OK",
        STATUS_FAIL: "FAIL",
    }
    detail = result["error"] or result["head_after"] or "local workspace"
    return f"{labels[result['status']]:5} {result['local_dir']}: {detail}"


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
        if result["status"] == STATUS_SKIP_LOCAL:
            summary["local_workspaces"] += 1
        elif result["status"] == STATUS_MISSING:
            summary["missing"] += 1
        elif result["status"] == STATUS_READY:
            summary["refreshable"] += 1
            summary["ready"] += 1
        elif result["status"] == STATUS_OK:
            summary["refreshable"] += 1
            summary["pull_ok"] += 1
        elif result["status"] == STATUS_FAIL:
            summary["refreshable"] += 1
            summary["pull_fail"] += 1
    return summary


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    if args.update_lock:
        errors = update_lock(root)
        for error in errors:
            print(f"FAIL  {error}")
        if not errors:
            print("Updated tracked_repos.lock.json; review and commit the proposed SHAs.")
        return 1 if errors else 0
    results = refresh_repositories(root, sync=args.sync)
    for result in results:
        print(format_result(result, pull=args.sync))
    summary = summarize_results(results)
    print(
        f"Summary: ready={summary['ready']}, synced={summary['pull_ok']}, missing={summary['missing']}, failed={summary['pull_fail']}"
    )
    return 1 if summary["missing"] or summary["pull_fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
