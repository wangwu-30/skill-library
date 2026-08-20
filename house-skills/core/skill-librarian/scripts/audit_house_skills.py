#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml
from skill_library_utils import (
    METADATA_SCHEMA_VERSION,
    VALID_USAGE_TRACKING_MODES,
    is_semver,
    locate_library_root,
    parse_datetime,
    read_json,
    read_reviewed_core_manifest,
    skill_content_sha256,
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
FRONTMATTER_FIELDS = {"name", "description"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 63
MAX_DESCRIPTION_LENGTH = 1024
OPENAI_INTERFACE_FIELDS = {"display_name", "short_description", "default_prompt"}


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


def check_frontmatter(skill_md: Path, issues: list[str]) -> dict[str, object] | None:
    text = load_text(skill_md)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        issues.append("missing frontmatter")
        return None
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        issues.append(f"invalid frontmatter YAML: {exc}")
        return None
    if not isinstance(frontmatter, dict):
        issues.append("frontmatter must be a mapping")
        return None

    keys = set(frontmatter)
    missing = FRONTMATTER_FIELDS - keys
    extra = keys - FRONTMATTER_FIELDS
    for field in sorted(missing):
        issues.append(f"frontmatter missing {field}")
    if extra:
        issues.append("frontmatter has unsupported fields: " + ", ".join(sorted(map(str, extra))))

    name = frontmatter.get("name")
    if not isinstance(name, str):
        issues.append("frontmatter name must be a string")
    elif len(name) > MAX_NAME_LENGTH or not NAME_PATTERN.fullmatch(name):
        issues.append("frontmatter name must be lowercase hyphen-case and at most 63 characters")
    elif name != skill_md.parent.name:
        issues.append(f"frontmatter name must match directory name: {skill_md.parent.name}")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        issues.append("frontmatter description must be a non-empty string")
    elif "\n" in description or len(description) > MAX_DESCRIPTION_LENGTH:
        issues.append("frontmatter description must be single-line and at most 1024 characters")
    return frontmatter


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


def check_references(skill_md: Path, issues: list[str]) -> None:
    text = load_text(skill_md)
    skill_root = skill_md.parent.resolve()
    for target in extract_markdown_links(text):
        if "://" in target:
            continue
        target = target.split("#", 1)[0]
        if not target:
            continue
        link_path = (skill_root / target).resolve()
        try:
            link_path.relative_to(skill_root)
        except ValueError:
            issues.append(f"linked file escapes skill directory: {target}")
            continue
        if not link_path.exists():
            issues.append(f"missing linked file: {target}")


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

    # Compare via timestamps to avoid local timezone formatting issues.
    if newest_path is not None and updated_at.timestamp() + 1 < newest_path.stat().st_mtime:
        rel = newest_path.relative_to(root)
        issues.append(f"metadata updated_at older than latest file change: {rel}")


def check_agents(skill_dir: Path, skill_name: str | None, issues: list[str]) -> None:
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        issues.append("missing agents/openai.yaml")
        return
    try:
        document = yaml.safe_load(load_text(openai_yaml))
    except yaml.YAMLError as exc:
        issues.append(f"invalid agents/openai.yaml: {exc}")
        return
    if not isinstance(document, dict):
        issues.append("agents/openai.yaml must be a mapping")
        return
    interface = document.get("interface")
    if not isinstance(interface, dict):
        issues.append("agents/openai.yaml interface must be a mapping")
    else:
        for field in sorted(OPENAI_INTERFACE_FIELDS):
            value = interface.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"agents/openai.yaml interface.{field} must be a non-empty string")
        short_description = interface.get("short_description")
        if isinstance(short_description, str) and not 25 <= len(short_description) <= 64:
            issues.append("agents/openai.yaml interface.short_description must be 25-64 characters")
        prompt = interface.get("default_prompt")
        if skill_name and isinstance(prompt, str) and f"${skill_name}" not in prompt:
            issues.append(f"agents/openai.yaml default_prompt must mention ${skill_name}")
    policy = document.get("policy")
    if not isinstance(policy, dict) or not isinstance(
        policy.get("allow_implicit_invocation"), bool
    ):
        issues.append("agents/openai.yaml policy.allow_implicit_invocation must be a boolean")


def audit_skill(skill_dir: Path, root: Path, check_freshness: bool) -> list[str]:
    issues: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ["missing SKILL.md"]
    frontmatter = check_frontmatter(skill_md, issues)
    check_sections(skill_md, issues)
    check_references(skill_md, issues)
    check_metadata(skill_dir, root, issues, check_freshness)
    skill_name = frontmatter.get("name") if isinstance(frontmatter, dict) else None
    check_agents(skill_dir, skill_name if isinstance(skill_name, str) else None, issues)
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


def audit_reviewed_core(root: Path, skills: list[Path]) -> list[str]:
    issues: list[str] = []
    try:
        reviewed = read_reviewed_core_manifest(root)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    core_skills = {
        str(skill.resolve().relative_to(root.resolve())): skill
        for skill in skills
        if expected_stage(skill, root) == "core"
    }
    for skill_path in sorted(set(core_skills) - set(reviewed)):
        issues.append(f"core skill is missing reviewed payload hash: {skill_path}")
    for skill_path in sorted(set(reviewed) - set(core_skills)):
        issues.append(f"reviewed payload hash does not name a current core skill: {skill_path}")
    for skill_path in sorted(set(core_skills) & set(reviewed)):
        try:
            actual_hash = skill_content_sha256(core_skills[skill_path])
        except (OSError, ValueError) as exc:
            issues.append(f"cannot hash reviewed core payload {skill_path}: {exc}")
            continue
        if actual_hash != reviewed[skill_path]:
            issues.append(f"reviewed payload hash mismatch: {skill_path}")
    return issues


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    skill_failures = 0
    skills = iter_house_skills(root)
    for skill_dir in skills:
        issues = audit_skill(skill_dir, root, args.check_freshness)
        if issues:
            skill_failures += 1
            print(f"FAIL  {skill_dir.relative_to(root)}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"OK    {skill_dir.relative_to(root)}")

    policy_issues = audit_reviewed_core(root, skills)
    if policy_issues:
        print("FAIL  catalog/reviewed_core.lock.json")
        for issue in policy_issues:
            print(f"  - {issue}")
    else:
        print("OK    catalog/reviewed_core.lock.json")

    print(
        f"Summary: skills={len(skills)}, failing={skill_failures}, "
        f"passing={len(skills) - skill_failures}, policy_failing={int(bool(policy_issues))}"
    )
    return 1 if skill_failures or policy_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
