from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from conftest import CONVERTER_SCRIPTS, LIBRARIAN_SCRIPTS, load_script

audit = load_script("audit_house_skills", LIBRARIAN_SCRIPTS / "audit_house_skills.py")
drafts = load_script("create_house_skill_draft", LIBRARIAN_SCRIPTS / "create_house_skill_draft.py")
converter = load_script("init_converted_skill", CONVERTER_SCRIPTS / "init_converted_skill.py")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def test_draft_round_trips_yaml_sensitive_description(library_root: Path) -> None:
    description = 'Use when input contains: quotes "like this" and # markers.'
    skill = drafts.create_draft(
        root=library_root,
        name="safe-draft",
        description=description,
        source_note="A reviewed gap: issue #42",
        ttl_days=3,
        context="Repository context",
        source_summary="No trusted match.",
    )

    assert frontmatter(skill / "SKILL.md") == {
        "name": "safe-draft",
        "description": description,
    }
    interface = yaml.safe_load((skill / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert interface["policy"]["allow_implicit_invocation"] is True
    assert "$safe-draft" in interface["interface"]["default_prompt"]
    assert not (skill / "scripts").exists()
    assert audit.audit_skill(skill, library_root, check_freshness=False) == []


@pytest.mark.parametrize(
    ("name", "description", "ttl"),
    [
        ("../escape", "Use when testing paths safely.", 1),
        ("Bad_Name", "Use when testing names safely.", 1),
        ("valid-name", "line one\nname: injected", 1),
        ("valid-name", "Use when the TTL is invalid.", 0),
    ],
)
def test_draft_rejects_unsafe_inputs(
    library_root: Path, name: str, description: str, ttl: int
) -> None:
    with pytest.raises(ValueError):
        drafts.create_draft(
            root=library_root,
            name=name,
            description=description,
            source_note="Reviewed source",
            ttl_days=ttl,
            context="",
            source_summary="",
        )


def test_audit_rejects_invalid_frontmatter_and_openai_yaml(library_root: Path) -> None:
    skill = library_root / "house-skills/young/broken"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: broken\ndescription: ok\nextra: forbidden\n---\n", encoding="utf-8"
    )
    (skill / "agents/openai.yaml").write_text("interface: [not-a-map]\n", encoding="utf-8")

    issues = audit.audit_skill(skill, library_root, check_freshness=False)

    assert any("unsupported fields" in issue for issue in issues)
    assert any("interface must be a mapping" in issue for issue in issues)
    assert any("missing metadata.json" in issue for issue in issues)
    assert any("missing section" in issue for issue in issues)


def test_audit_rejects_reference_escape(library_root: Path) -> None:
    skill = drafts.create_draft(
        library_root,
        "escape-link",
        "Use when checking that skill references stay local.",
        "Reviewed source",
        1,
        "",
        "",
    )
    with (skill / "SKILL.md").open("a", encoding="utf-8") as handle:
        handle.write("\n[escape](../../../../outside.md)\n")
    issues = audit.audit_skill(skill, library_root, check_freshness=False)
    assert any("escapes skill directory" in issue for issue in issues)


def test_converter_serializes_user_values_and_passes_audit(
    library_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    description = 'Use when converting input with: "quotes" and # markers.'
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_converted_skill.py",
            "--root",
            str(library_root),
            "--name",
            "converted-safe",
            "--description",
            description,
            "--source-repo",
            'https://example.test/repo?value="quoted"',
            "--source-path",
            "skills/example:latest",
            "--author",
            'Example "Org"',
        ],
    )

    assert converter.main() == 0
    skill = library_root / "house-skills/young/converted-safe"
    assert frontmatter(skill / "SKILL.md")["description"] == description
    metadata = json.loads((skill / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source"]["author"] == 'Example "Org"'
    assert not (skill / "scripts").exists()
    assert audit.audit_skill(skill, library_root, check_freshness=False) == []


def test_converter_rejects_destination_escape(
    library_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_converted_skill.py",
            "--root",
            str(library_root),
            "--dest-root",
            str(tmp_path / "outside"),
            "--name",
            "converted-safe",
            "--description",
            "Use when converting a reviewed external skill.",
            "--source-repo",
            "https://example.test/repo",
            "--source-path",
            "skill",
        ],
    )
    with pytest.raises(ValueError, match="dest-root"):
        converter.main()


def test_converter_rejects_direct_core_creation(
    library_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_converted_skill.py",
            "--root",
            str(library_root),
            "--name",
            "unreviewed-core",
            "--description",
            "Use when testing that conversion cannot bypass review.",
            "--source-repo",
            "https://github.com/example/source",
            "--source-path",
            "skill",
            "--stage",
            "core",
        ],
    )
    with pytest.raises(SystemExit):
        converter.main()
    assert not (library_root / "house-skills/core/unreviewed-core").exists()


def test_house_audit_enforces_reviewed_core_payload_manifest(library_root: Path) -> None:
    skill = drafts.create_draft(
        library_root,
        "reviewed-payload",
        "Use when testing the reviewed core payload manifest.",
        "Reviewed source",
        1,
        "",
        "",
    )
    core_skill = library_root / "house-skills/core/reviewed-payload"
    core_skill.parent.mkdir(parents=True)
    skill.rename(core_skill)
    metadata_path = core_skill / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({"stage": "core", "status": "stable", "expires_at": None})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    skills = audit.iter_house_skills(library_root)

    assert any(
        "missing reviewed payload hash" in issue
        for issue in audit.audit_reviewed_core(library_root, skills)
    )

    utils = load_script("skill_library_utils", LIBRARIAN_SCRIPTS / "skill_library_utils.py")
    content_hash = utils.skill_content_sha256(core_skill)
    (library_root / "catalog/reviewed_core.lock.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": [
                    {
                        "path": "house-skills/core/reviewed-payload",
                        "content_sha256": content_hash,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert audit.audit_reviewed_core(library_root, skills) == []

    (core_skill / "SKILL.md").write_text("changed after review\n", encoding="utf-8")
    assert any(
        "reviewed payload hash mismatch" in issue
        for issue in audit.audit_reviewed_core(library_root, skills)
    )
