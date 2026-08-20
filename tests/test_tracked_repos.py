from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).parents[1] / "house-skills/core/skill-librarian/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "refresh_tracked_repos", SCRIPTS / "refresh_tracked_repos.py"
)
refresh = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(refresh)


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_remote(tmp_path: Path) -> tuple[Path, str]:
    work = tmp_path / "source"
    work.mkdir()
    git("init", cwd=work)
    git("config", "user.email", "test@example.com", cwd=work)
    git("config", "user.name", "Test", cwd=work)
    (work / "SKILL.md").write_text("# Test\n", encoding="utf-8")
    git("add", "SKILL.md", cwd=work)
    git("commit", "-m", "initial", cwd=work)
    commit = git("rev-parse", "HEAD", cwd=work)
    remote = tmp_path / "remote.git"
    git("clone", "--bare", str(work), str(remote))
    return remote, commit


def repo_url() -> str:
    return "https://github.com/example/sample"


def repo() -> dict:
    return {"id": "sample", "local_dir": "sample", "repo_url": repo_url()}


def lock(commit: str, url: str | None = None) -> dict:
    return {"id": "sample", "repo_url": url or repo_url(), "commit": commit}


def test_missing_clone_is_bootstrapped_at_locked_commit(tmp_path: Path) -> None:
    remote, commit = make_remote(tmp_path)
    root = tmp_path / "library"
    root.mkdir()
    real_run_git = refresh.run_git

    def local_clone(*args: str, cwd: Path | None = None):
        if args[:3] == ("clone", "--no-checkout", "--"):
            cloned = subprocess.run(
                ["git", "clone", "--no-checkout", "--", str(remote), args[-1]],
                capture_output=True,
                text=True,
                check=False,
            )
            if cloned.returncode == 0:
                real_run_git("remote", "set-url", "origin", repo_url(), cwd=Path(args[-1]))
            return cloned
        return real_run_git(*args, cwd=cwd)

    with patch.object(refresh, "run_git", side_effect=local_clone):
        result = refresh.inspect_repo(root, repo(), lock(commit), sync=True)
    assert result["status"] == refresh.STATUS_OK
    assert git("rev-parse", "HEAD", cwd=root / "sample") == commit


def test_remote_url_mismatch_fails(tmp_path: Path) -> None:
    remote, commit = make_remote(tmp_path)
    root = tmp_path / "library"
    root.mkdir()
    git("clone", str(remote), str(root / "sample"))
    tracked = repo()
    result = refresh.inspect_repo(root, tracked, lock(commit))
    assert result["status"] == refresh.STATUS_FAIL
    assert "origin URL" in result["error"]


def test_lock_url_mismatch_fails_before_git(tmp_path: Path) -> None:
    remote, commit = make_remote(tmp_path)
    root = tmp_path / "library"
    root.mkdir()
    result = refresh.inspect_repo(root, repo(), lock(commit, "https://github.com/example/other"))
    assert result["status"] == refresh.STATUS_FAIL
    assert "lock entry" in result["error"]


def test_main_returns_nonzero_for_missing_clone(tmp_path: Path, monkeypatch) -> None:
    remote, commit = make_remote(tmp_path)
    root = tmp_path / "library"
    (root / "catalog").mkdir(parents=True)
    (root / "catalog/tracked_repos.json").write_text(
        json.dumps({"repos": [repo()]}), encoding="utf-8"
    )
    (root / "catalog/tracked_repos.lock.json").write_text(
        json.dumps({"schema_version": 1, "repos": [lock(commit)]}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["refresh_tracked_repos.py", "--root", str(root)])
    assert refresh.main() == 1


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    remote, commit = make_remote(tmp_path)
    tracked = repo()
    tracked["local_dir"] = "../outside"
    result = refresh.inspect_repo(tmp_path / "library", tracked, lock(commit), sync=True)
    assert result["status"] == refresh.STATUS_FAIL
    assert "parent traversal" in result["error"]


def test_symlinked_local_dir_component_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "library"
    redirected = root / "house-skills/core"
    redirected.mkdir(parents=True)
    (root / "mirrors").symlink_to(redirected, target_is_directory=True)
    tracked = repo()
    tracked["local_dir"] = "mirrors/sample"

    result = refresh.inspect_repo(root, tracked, lock("a" * 40), sync=True)

    assert result["status"] == refresh.STATUS_FAIL
    assert "symlink" in result["error"]
    assert not (redirected / "sample").exists()


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:example/sample.git",
        "ssh://git@github.com/example/sample.git",
        "file:///tmp/sample.git",
        "/tmp/sample.git",
        "ext::sh -c evil",
        "https://user:token@github.com/example/sample",
        "https://github.com.evil.test/example/sample",
        "https://github.com/example/sample?ref=main",
    ],
)
def test_unsafe_transport_is_rejected_before_git(tmp_path: Path, url: str) -> None:
    tracked = repo()
    tracked["repo_url"] = url
    with patch.object(refresh, "run_git") as run_git_mock:
        result = refresh.inspect_repo(tmp_path / "library", tracked, lock("a" * 40, url), sync=True)
    assert result["status"] == refresh.STATUS_FAIL
    assert "repo_url" in result["error"]
    run_git_mock.assert_not_called()


def test_git_invocation_disables_config_rewrites_and_credentials(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "url.https://evil.test/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:https")
    monkeypatch.setenv("GIT_DIR", "/tmp/unrelated.git")
    monkeypatch.setenv("GIT_SSL_NO_VERIFY", "1")
    monkeypatch.setattr(refresh.subprocess, "run", fake_run)

    refresh.run_git("ls-remote", "--", repo_url(), "HEAD")

    assert "protocol.allow=never" in captured["command"]
    assert "protocol.https.allow=always" in captured["command"]
    assert "credential.helper=" in captured["command"]
    assert f"core.hooksPath={os.devnull}" in captured["command"]
    assert "core.fsmonitor=" in captured["command"]
    assert "init.templateDir=" in captured["command"]
    assert "http.sslVerify=true" in captured["command"]
    assert captured["environment"]["GIT_CONFIG_GLOBAL"] == os.devnull
    assert captured["environment"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert captured["environment"]["GIT_TERMINAL_PROMPT"] == "0"
    assert not any(
        key.startswith("GIT_CONFIG_")
        for key in captured["environment"]
        if key not in {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"}
    )
    assert "GIT_ALLOW_PROTOCOL" not in captured["environment"]
    assert "GIT_DIR" not in captured["environment"]
    assert "GIT_SSL_NO_VERIFY" not in captured["environment"]
    assert captured["environment"]["GIT_ASKPASS"] == os.devnull
    assert captured["environment"]["SSH_ASKPASS"] == os.devnull
    assert captured["command"][-3:] == ["--", repo_url(), "HEAD"]
