# House Skills

This directory contains locally governed skills. Its lifecycle is also the runtime trust boundary.

## Layout

- `core/`: explicitly promoted skills; only payloads matching the reviewed-core manifest are eligible for default MCP responses
- `young/`: drafts and experiments; reference-only until explicit promotion and payload-hash approval
- `archive/`: retired skills retained for provenance and never selected
- `config/lifecycle.json`: shared review thresholds and safety defaults

Tracked upstream repositories are not house skills. They remain reference-only even when the catalog indexes them.

## Lifecycle

1. New or converted skills start in `young/`.
2. Every house skill carries `schema_version`, semantic `version`, `owner`, provenance, compatibility, and `usage_tracking.mode` in `metadata.json`.
3. Trigger and output evaluation must use the conventions in [eval/README.md](../eval/README.md).
4. Usage is supporting evidence, not proof of quality; `usage_tracking.mode=none` means `use_count=0` is not trustworthy evidence of non-use.
5. Promotion requires explicit human review of content, provenance, license, permissions, validation, and evaluation evidence. Moving a directory into `core/` does not itself make the skill eligible for default MCP responses.
6. Non-trivial version changes should use the versioning script and preserve a snapshot before breaking changes.
7. GC may recommend promotion or archival but must not silently cross the reviewed-core boundary.
8. Archive replaced or stale skills instead of deleting provenance.
9. After explicit promotion and full payload review, update `catalog/reviewed_core.lock.json` through code-owner review. Its deterministic SHA-256 recursively covers payload files such as `SKILL.md`, `agents/`, `references/`, `scripts/`, and `assets/`, excludes mutable `metadata.json`, `__pycache__/`, and `.pyc` files, and rejects symbolic links. The catalog and MCP server grant `reviewed-core` status only when the current payload exactly matches that hash.

## Safe Review Checklist

Before promotion to `core/`, confirm that the skill:

- has a narrow, accurate trigger and an executable workflow;
- does not inherit unreviewed commands or prompt instructions from an upstream source;
- requests no broader filesystem, network, credential, or destructive access than necessary;
- links only to present, reviewed local resources;
- preserves required upstream attribution and compatible licensing;
- passes the house-skill audit and relevant evaluation cases.

Run validation through the locked project environment:

```bash
uv sync --frozen
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen pytest
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full change and review process and [the charter](../docs/skill-control-plane-charter.md) for the trust model.
