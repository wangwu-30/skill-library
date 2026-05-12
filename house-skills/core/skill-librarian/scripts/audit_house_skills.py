#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

from skill_library_utils import (
    METADATA_SCHEMA_VERSION,
    VALID_USAGE_TRACKING_MODES,
    is_semver,
    locate_library_root,
    parse_datetime,
    read_json,
)


REQUIRED_METADATA_FIELDS = [
    "schema_version",
    "version",
    "owner",
    "stage",
    "status",
    "created_at",
    "updated_at",
    "last_used_at",
    "use_count",
    "expires_at",
    "usage_tracking",
    "derives_from",
    "replaces",
    "compatibility",
    "source",
]

REQUIRED_SECTIONS = [
    "## When To Use",
    "## Inputs",
    "## Workflow",
    "## Output Contract",
    "## Validation",
    "## Sources",
]

STAGE_ROOTS = {
    "core": "stable",
    "young": "active",
    "archive": "archived",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit house-skill integrity.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--check-freshness",
        action="store_true",
        help="Also compare metadata updated_at against file mtimes. This is useful in a live worktree but noisy in fresh git clones.",
    )
    return parser.parse_args()


def resolve_root(cli_root: Path | None) -> Path:
    return locate_library_root(cli_root, Path(__file__))


def expected_stage(skill_dir: Path, root: Path) -> str | None:
    house_root = root / "house-skills"
    try:
        relative = skill_dir.resolve().relative_to(house_root.resolve())
    except ValueError:
        return None
    parts = relative.parts
    if not parts:
        return None
    return parts[0] if parts[0] in STAGE_ROOTS else None


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_frontmatter(skill_md: Path, issues: list[str]) -> None:
    text = load_text(skill_md)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        issues.append("missing frontmatter")
        return
    frontmatter = match.group(1)
    if "name:" not in frontmatter:
        issues.append("frontmatter missing name")
    if "description:" not in frontmatter:
        issues.append("frontmatter missing description")


def check_sections(skill_md: Path, issues: list[str]) -> None:
    text = load_text(skill_md)
    positions = []
    for section in REQUIRED_SECTIONS:
        match = re.search(rf"(?m)^{re.escape(section)}\s*$", text)
        if match is None:
            issues.append(f"missing section: {section}")
            positions.append(-1)
        else:
            positions.append(match.start())
    filtered = [p for p in positions if p != -1]
    if filtered and filtered != sorted(filtered):
        issues.append("required sections out of order")


def extract_markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def check_source_links(skill_md: Path, issues: list[str]) -> None:
    text = load_text(skill_md)
    source_match = re.search(r"(?ms)^## Sources\s*(.*)$", text)
    if source_match is None:
        return
    source_block = source_match.group(1)
    for target in extract_markdown_links(source_block):
        if "://" in target:
            continue
        link_path = (skill_md.parent / target).resolve()
        if not link_path.exists():
            issues.append(f"missing linked source file: {target}")


def check_metadata(skill_dir: Path, root: Path, issues: list[str], check_freshness: bool) -> None:
    metadata_path = skill_dir / "metadata.json"
    if not metadata_path.exists():
        issues.append("missing metadata.json")
        return

    metadata = read_json(metadata_path, {})
    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            issues.append(f"metadata missing field: {field}")

    stage = metadata.get("stage")
    expected = expected_stage(skill_dir, root)
    if expected and stage != expected:
        issues.append(f"metadata stage mismatch: expected {expected}, got {stage}")

    expected_status = STAGE_ROOTS.get(stage)
    if expected_status and metadata.get("status") != expected_status:
        issues.append(
            f"metadata status mismatch for stage {stage}: expected {expected_status}, got {metadata.get('status')}"
        )

    source = metadata.get("source")
    if not isinstance(source, dict):
        issues.append("metadata source must be an object")

    schema_version = metadata.get("schema_version")
    if schema_version != METADATA_SCHEMA_VERSION:
        issues.append(
            f"metadata schema_version mismatch: expected {METADATA_SCHEMA_VERSION}, got {schema_version}"
        )

    if not is_semver(metadata.get("version")):
        issues.append("metadata version must be semver, for example 0.1.0")

    owner = metadata.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        issues.append("metadata owner must be a non-empty string")

    usage_tracking = metadata.get("usage_tracking")
    if not isinstance(usage_tracking, dict):
        issues.append("metadata usage_tracking must be an object")
    else:
        mode = usage_tracking.get("mode")
        if mode not in VALID_USAGE_TRACKING_MODES:
            issues.append(
                "metadata usage_tracking.mode must be one of: "
                + ", ".join(sorted(VALID_USAGE_TRACKING_MODES))
            )

    derives_from = metadata.get("derives_from")
    if derives_from is not None and not isinstance(derives_from, dict):
        issues.append("metadata derives_from must be null or an object")

    replaces = metadata.get("replaces")
    if not isinstance(replaces, list):
        issues.append("metadata replaces must be a list")
    else:
        for index, item in enumerate(replaces):
            if not isinstance(item, dict):
                issues.append(f"metadata replaces[{index}] must be an object")
                continue
            if not isinstance(item.get("skill_path"), str) or not item.get("skill_path"):
                issues.append(f"metadata replaces[{index}] missing skill_path")
            if not is_semver(item.get("version")):
                issues.append(
                    f"metadata replaces[{index}] version must be semver, for example 0.1.0"
                )

    compatibility = metadata.get("compatibility")
    if not isinstance(compatibility, dict):
        issues.append("metadata compatibility must be an object")
    else:
        backward_compatible = compatibility.get("backward_compatible")
        if not isinstance(backward_compatible, bool):
            issues.append("metadata compatibility.backward_compatible must be a boolean")
        notes = compatibility.get("notes")
        if notes is not None and not isinstance(notes, str):
            issues.append("metadata compatibility.notes must be a string when present")

    updated_at = parse_datetime(metadata.get("updated_at"))
    if updated_at is None:
        issues.append("metadata updated_at is missing or invalid")
        return
    if not check_freshness:
        return

    newest_mtime = 0.0
    newest_path: Path | None = None
    for file_path in skill_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name.endswith(".pyc") or "__pycache__" in file_path.parts:
            continue
        if file_path.name == "metadata.json":
            continue
        stat = file_path.stat()
        if stat.st_mtime > newest_mtime:
            newest_mtime = stat.st_mtime
            newest_path = file_path

    if newest_path is not None:
        # Compare via timestamps to avoid local timezone formatting issues.
        if updated_at.timestamp() + 1 < newest_path.stat().st_mtime:
            rel = newest_path.relative_to(root)
            issues.append(
                f"metadata updated_at older than latest file change: {rel}"
            )


def check_agents(skill_dir: Path, issues: list[str]) -> None:
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        issues.append("missing agents/openai.yaml")


def audit_skill(skill_dir: Path, root: Path, check_freshness: bool) -> list[str]:
    issues: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ["missing SKILL.md"]
    check_frontmatter(skill_md, issues)
    check_sections(skill_md, issues)
    check_source_links(skill_md, issues)
    check_metadata(skill_dir, root, issues, check_freshness)
    check_agents(skill_dir, issues)
    return issues


def iter_house_skills(root: Path) -> list[Path]:
    skills: list[Path] = []
    for stage in ("core", "young", "archive"):
        stage_root = root / "house-skills" / stage
        if not stage_root.exists():
            continue
        for skill_dir in sorted(stage_root.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir)
    return skills


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    failures = 0
    skills = iter_house_skills(root)
    for skill_dir in skills:
        issues = audit_skill(skill_dir, root, args.check_freshness)
        if issues:
            failures += 1
            print(f"FAIL  {skill_dir.relative_to(root)}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"OK    {skill_dir.relative_to(root)}")

    print(f"Summary: skills={len(skills)}, failing={failures}, passing={len(skills) - failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
