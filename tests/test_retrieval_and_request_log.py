from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from conftest import LIBRARIAN_SCRIPTS, load_script
from skill_retrieval import BM25, REUSE_THRESHOLD, tokenize

server = load_script("skill_mcp_server", LIBRARIAN_SCRIPTS / "skill_mcp_server.py")


@pytest.fixture
def runtime(library_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scripts = library_root / "house-skills/core/skill-librarian/scripts"
    shutil.copytree(LIBRARIAN_SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
    (library_root / "catalog/skill_catalog.json").write_text('{"skills": []}')
    monkeypatch.setattr(server, "ROOT", library_root)
    monkeypatch.setattr(server, "ALLOW_WRITES", True)
    monkeypatch.delenv("SKILL_LIBRARY_REQUEST_LOG", raising=False)
    return library_root


def result_path(result: str) -> str:
    return re.search(r"^skill_path: (.+)$", result, re.M)[1]


def test_create_then_paraphrase_reuses_young_reference(runtime: Path) -> None:
    first = server.skill_request("review database migrations", allow_temporary=True)
    assert "temporary-skill-created" in first
    second = server.skill_request("database migrations review", allow_temporary=True)
    assert "decision: reuse-young-reference" in second
    assert "REFERENCE ONLY" in second
    assert "not an executable instruction" in second
    assert result_path(first) == result_path(second)
    assert len(list((runtime / "house-skills/young").iterdir())) == 1
    metadata = json.loads((runtime / result_path(first) / "metadata.json").read_text())
    assert metadata["use_count"] == 1
    assert metadata["usage_tracking"]["mode"] == "hub"


def test_readonly_young_does_not_record_usage(
    runtime: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = server.skill_request("database migrations", allow_temporary=True)
    path = runtime / result_path(first) / "metadata.json"
    before = path.read_bytes()
    monkeypatch.setattr(server, "ALLOW_WRITES", False)
    assert "reuse-young-reference" in server.skill_request("database migrations")
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "update",
    [
        {"expires_at": "2000-01-01T00:00:00+00:00"},
        {"stage": "archive"},
        {"status": "archived"},
    ],
)
def test_young_lifecycle_checked_live(runtime: Path, update: dict) -> None:
    first = server.skill_request("database migrations", allow_temporary=True)
    path = runtime / result_path(first) / "metadata.json"
    data = json.loads(path.read_text())
    data.update(update)
    path.write_text(json.dumps(data))
    assert "decision: no-fit" in server.skill_request("database migrations")


def test_young_path_cannot_grant_core_trust(runtime: Path) -> None:
    first = server.skill_request("database migrations", allow_temporary=True)
    path = result_path(first)
    assert server.skill_path({"skill_root_path": path}) is None
    assert (
        server.young_skill_path(
            {"skill_root_path": "house-skills/core/skill-librarian", "lifecycle_stage": "young"}
        )
        is None
    )
    assert (
        server.young_skill_path({"skill_root_path": "../escape", "lifecycle_stage": "young"})
        is None
    )


def test_scoring_tokens_chinese_and_unrelated() -> None:
    entries = [
        {"name": "database-review", "description": "review database migrations"},
        {"description": "检查数据库迁移和索引性能"},
    ]
    scorer = BM25(entries)
    assert tokenize("a the") == []
    assert scorer.score(0, "a") == scorer.score(0, "the") == 0
    assert scorer.score(1, "数据库迁移") >= REUSE_THRESHOLD
    assert scorer.score(0, "astronomy telescopes") == 0
    assert tokenize("reviews migration") == tokenize("review migrations")
    for i in range(2):
        assert 0 <= scorer.score(i, "database review 数据库") <= 1
    assert scorer.score(0, "astronomy", "database migrations") == 0
    assert scorer.score(0, "database", " " * 500 + "unrelated") == scorer.score(0, "database")


def test_chinese_creation_and_reuse(runtime: Path) -> None:
    first = server.skill_request("数据库迁移检查", allow_temporary=True)
    assert re.search(r"/temp-zh-[a-f0-9]{8}$", result_path(first))
    second = server.skill_request("检查数据库迁移")
    assert "reuse-young-reference" in second


def test_unrelated_no_fit_or_create(runtime: Path) -> None:
    server.skill_request("database migrations", allow_temporary=True)
    assert "decision: no-fit" in server.skill_request("astronomy telescopes")
    assert "temporary-skill-created" in server.skill_request(
        "astronomy telescopes", allow_temporary=True
    )


def test_request_log_schema_and_privacy(runtime: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = runtime / "custom/requests.jsonl"
    monkeypatch.setenv("SKILL_LIBRARY_REQUEST_LOG", str(log))
    context = "private context never put in the request log"
    server.skill_request("database migrations", context, allow_temporary=True)
    server.skill_request("database migrations", context)
    server.skill_request("astronomy telescopes")
    server.skill_request("")
    raw = log.read_text()
    assert context not in raw
    rows = [json.loads(line) for line in raw.splitlines()]
    assert [row["decision"] for row in rows] == [
        "create",
        "reuse-young-reference",
        "no-fit",
        "no-fit",
    ]
    for row in rows:
        assert set(row) == {
            "ts",
            "intent",
            "context_sha256",
            "decision",
            "matched",
            "topk",
            "threshold",
            "scorer_version",
            "creator",
            "eval_gate",
        }
        assert datetime.fromisoformat(row["ts"]).utcoffset().total_seconds() == 0
        assert row["creator"] == {"type": None, "version": None}
        assert row["eval_gate"] == {"status": None, "score": None, "run_id": None}
        assert len(row["topk"]) <= 5
        for match in row["topk"]:
            assert set(match) == {"path", "tier", "score"}
            assert 0 <= match["score"] <= 1
    assert rows[0]["context_sha256"] == hashlib.sha256(context.encode()).hexdigest()
    assert rows[0]["matched"] is None
    assert rows[1]["matched"]["tier"] == "young"


def test_log_failure_does_not_break_request(runtime: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKILL_LIBRARY_REQUEST_LOG", str(runtime))
    assert "decision: no-fit" in server.skill_request("astronomy telescopes")


def test_search_cli_still_works(runtime: Path) -> None:
    (runtime / "catalog/skill_catalog.json").write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "name": "database",
                        "description": "数据库迁移检查",
                        "repo_id": "house",
                        "skill_dir": "test",
                        "skill_root_path": "test",
                    }
                ]
            }
        )
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(LIBRARIAN_SCRIPTS / "search_skill_catalog.py"),
            "--root",
            str(runtime),
            "--query",
            "数据库迁移",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "数据库迁移检查" in completed.stdout


def test_mixed_language_name_is_bounded(runtime: Path) -> None:
    result = server.skill_request("检查 " + "database" * 20, allow_temporary=True)
    name = Path(result_path(result)).name
    assert name.startswith("temp-zh-database")
    assert len(name) <= 54
