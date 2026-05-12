#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from search_skill_catalog import score_entry
from skill_consult import record_usage
from skill_library_utils import locate_library_root


ROOT: Path | None = None
HOUSE_REUSE_SCORE = 45
ANY_REUSE_SCORE = 70

mcp = FastMCP(
    "skill-library",
    instructions=(
        "Accept one task intent from an agent. Internally search, reuse, or scaffold a "
        "temporary skill. Return the skill the caller should use, not the library internals."
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the skill library over MCP stdio.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    return parser.parse_args()


def root_path() -> Path:
    if ROOT is None:
        raise RuntimeError("server root is not initialized")
    return ROOT


def run_script(script_name: str, *args: str) -> tuple[int, str, str]:
    root = root_path()
    script = root / "house-skills" / "core" / "skill-librarian" / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_catalog() -> None:
    root = root_path()
    catalog_path = root / "catalog" / "skill_catalog.json"
    if catalog_path.exists():
        return
    code, _stdout, stderr = run_script("build_skill_catalog.py")
    if code != 0:
        raise RuntimeError(stderr or "failed to build skill catalog")


def read_catalog() -> dict[str, Any]:
    ensure_catalog()
    catalog_path = root_path() / "catalog" / "skill_catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def query_tokens(intent: str, context: str) -> tuple[str, list[str]]:
    phrase = " ".join(f"{intent} {context}".lower().split())
    return phrase, [token for token in phrase.split() if token]


def ranked_candidates(intent: str, context: str, limit: int = 6) -> list[tuple[int, dict[str, Any]]]:
    catalog = read_catalog()
    phrase, tokens = query_tokens(intent, context)
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in catalog.get("skills", []):
        stage = entry.get("lifecycle_stage", "upstream")
        if stage == "archive" or entry.get("expired"):
            continue
        score = score_entry(entry, tokens, phrase)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda item: (-item[0], item[1].get("repo_id", ""), item[1].get("skill_dir", "")))
    return scored[:limit]


def skill_path(entry: dict[str, Any]) -> Path | None:
    rel_path = entry.get("skill_root_path")
    if not rel_path:
        return None
    path = root_path() / rel_path
    if not (path / "SKILL.md").exists():
        return None
    return path


def read_skill(entry: dict[str, Any]) -> tuple[Path, str] | None:
    path = skill_path(entry)
    if path is None:
        return None
    return path, (path / "SKILL.md").read_text(encoding="utf-8")


def should_reuse(score: int, entry: dict[str, Any]) -> bool:
    stage = entry.get("lifecycle_stage", "upstream")
    if stage in {"core", "young"} and score >= HOUSE_REUSE_SCORE:
        return True
    return score >= ANY_REUSE_SCORE


def record_house_usage(entry: dict[str, Any], path: Path) -> None:
    if entry.get("lifecycle_stage") not in {"core", "young"}:
        return
    try:
        record_usage(root_path(), path, "hub")
    except Exception as exc:  # pragma: no cover - best effort telemetry
        print(f"[warn] usage recording failed: {exc}", file=sys.stderr)


def normalize_name(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    return normalized[:40].strip("-") or "task"


def safe_description(intent: str) -> str:
    cleaned = " ".join(intent.strip().split())
    cleaned = cleaned.replace(":", " -").replace("---", "-")
    if len(cleaned) > 180:
        cleaned = cleaned[:177].rstrip() + "..."
    return f"Use when an agent needs task-specific help for {cleaned}"


def source_note(candidates: list[tuple[int, dict[str, Any]]]) -> str:
    if not candidates:
        return "No matching skill was found in the local catalog."
    parts = []
    for score, entry in candidates[:3]:
        display = entry.get("skill_root_path") or entry.get("skill_dir") or entry.get("repo_id")
        parts.append(f"{display} score={score}")
    return "Closest catalog examples: " + "; ".join(parts)


def create_temporary_skill(intent: str, context: str, candidates: list[tuple[int, dict[str, Any]]]) -> str:
    digest = hashlib.sha1(f"{intent}\n{context}".encode("utf-8")).hexdigest()[:8]
    name = f"temp-{normalize_name(intent)}-{digest}"
    code, stdout, stderr = run_script(
        "create_house_skill_draft.py",
        "--name",
        name,
        "--description",
        safe_description(intent),
        "--source-note",
        source_note(candidates),
        "--context",
        context or "No extra context was provided by the caller.",
        "--source-summary",
        candidate_summary(candidates),
    )
    if code != 0 and "Destination already exists" not in stderr:
        raise RuntimeError(stderr or stdout or "failed to create temporary skill")

    path = root_path() / "house-skills" / "young" / name
    if not (path / "SKILL.md").exists():
        raise RuntimeError(f"temporary skill was not created: {path}")
    return f"{path.relative_to(root_path())}\n\n{(path / 'SKILL.md').read_text(encoding='utf-8')}"


def candidate_summary(candidates: list[tuple[int, dict[str, Any]]]) -> str:
    if not candidates:
        return "No close catalog examples."
    lines = []
    for score, entry in candidates[:3]:
        display = entry.get("skill_root_path") or entry.get("skill_dir") or entry.get("repo_id")
        stage = entry.get("lifecycle_stage", "upstream")
        description = entry.get("description") or entry.get("title") or "No description"
        lines.append(f"- [{score}] [{stage}] {display}: {description}")
    return "\n".join(lines)


@mcp.tool()
def skill_request(intent: str, context: str = "", allow_temporary: bool = True) -> str:
    """Return one ready-to-use skill for the caller's task intent."""
    intent = intent.strip()
    context = context.strip()
    if not intent:
        return "error: intent is required"

    candidates = ranked_candidates(intent, context)
    for score, entry in candidates:
        loaded = read_skill(entry)
        if loaded is None:
            continue
        path, skill_md = loaded
        if not should_reuse(score, entry):
            continue
        record_house_usage(entry, path)
        rel_path = path.relative_to(root_path())
        return (
            "# Skill Agent Result\n\n"
            "decision: reuse-existing-skill\n"
            f"skill_path: {rel_path}\n"
            f"match_score: {score}\n\n"
            "Use this skill for the requested task:\n\n"
            "----- BEGIN SKILL -----\n"
            f"{skill_md.rstrip()}\n"
            "----- END SKILL -----\n"
        )

    if not allow_temporary:
        return (
            "# Skill Agent Result\n\n"
            "decision: no-fit\n\n"
            "No strong existing skill matched this intent.\n\n"
            "Closest examples:\n"
            f"{candidate_summary(candidates)}\n"
        )

    temporary = create_temporary_skill(intent, context, candidates)
    path_line, _, skill_md = temporary.partition("\n\n")
    return (
        "# Skill Agent Result\n\n"
        "decision: temporary-skill-created\n"
        f"skill_path: {path_line}\n\n"
        "Use this temporary skill for the requested task. It starts in `house-skills/young`; "
        "the live librarian can later keep, improve, or archive it.\n\n"
        "Closest examples considered internally:\n"
        f"{candidate_summary(candidates)}\n\n"
        "----- BEGIN SKILL -----\n"
        f"{skill_md.rstrip()}\n"
        "----- END SKILL -----\n"
    )


def main() -> int:
    global ROOT
    args = parse_args()
    ROOT = locate_library_root(args.root, Path(__file__))
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
