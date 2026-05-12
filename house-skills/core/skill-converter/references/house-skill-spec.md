# House Skill Spec

This is the internal normalization format for skills that should be easy to search, compare, and maintain.

## Folder layout

```text
skill-name/
├── SKILL.md
├── metadata.json
├── agents/
│   └── openai.yaml
├── references/
│   ├── optional-domain-notes.md
│   └── source-notes.md
└── scripts/
    └── optional-deterministic-helper.py
```

## Required frontmatter

`SKILL.md` must include:

- `name`: lowercase hyphen-case
- `description`: short trigger description that explains when to use the skill

## Required body sections

Use these sections in this order:

1. `# Purpose`
2. `## When To Use`
3. `## Inputs`
4. `## Workflow`
5. `## Output Contract`
6. `## Validation`
7. `## Sources`

## Source attribution

For converted skills, always preserve:

- upstream repository URL
- upstream skill path
- original author or organization if obvious
- conversion notes describing what was changed

## Lifecycle rules

- New generated or converted skills should start in `house-skills/young`.
- `metadata.json` must track `stage`, `status`, `created_at`, `updated_at`, `last_used_at`, `use_count`, and `expires_at`.
- `metadata.json` should also track `schema_version`, skill `version`, current `owner`, `usage_tracking.mode`, `derives_from`, `replaces`, and `compatibility`.
- Default TTL and promotion thresholds come from `house-skills/config/lifecycle.json`.
- Promotion to `house-skills/core` should happen only after repeated successful reuse.
- Expired or replaced skills should move to `house-skills/archive`.
- Do not embed tracking commands or telemetry instructions inside skill content. Retrieval counting belongs in the managing agent layer.

## Versioning Rules

- `schema_version` tracks the metadata shape, not the skill contract.
- `version` tracks the skill contract and should use semver.
- `derives_from` is for prior house-skill lineage when the current skill is a direct descendant of another local skill shape.
- `replaces` records the older versions or sibling skills this version superseded.
- `compatibility.backward_compatible` tells maintainers whether the new version should be safe for existing callers.
- Bump patch for wording, examples, or references that do not change trigger or execution behavior.
- Bump minor for backward-compatible workflow additions or stronger guardrails.
- Bump major when trigger boundaries, output contract, validation expectations, or breaking workflow assumptions change.
- If a breaking version still matters for rollback or provenance, archive the replaced version instead of silently overwriting it.
- Prefer `python3 house-skills/core/skill-librarian/scripts/bump_house_skill_version.py --root "$PWD" --skill-path <path> --bump <patch|minor|major> --snapshot-current` for deterministic version changes.

## Usage Tracking Modes

- `none`: no trustworthy recording surface exists yet; treat `use_count` and `last_used_at` as non-authoritative.
- `manual`: usage was recorded by a maintainer or script outside a hub; counts are advisory.
- `hub`: usage came from the future skill hub or another authoritative tracking surface.

## Conversion rules

- Prefer copying the smallest useful subset instead of mirroring large upstream trees.
- Prefer the smallest independently triggerable unit. Split by user task intent, not by upstream repository or vendor branding.
- Rewrite the trigger description so it is specific and searchable.
- Prefer shipped CLIs, official plugins, and deterministic helper scripts as the primary workflow. Keep ad-hoc custom scripts as a fallback.
- Move large docs into `references/` instead of bloating `SKILL.md`.
- Keep `SKILL.md` focused on the execution contract: trigger, required inputs, workflow, output, validation, and verified caveats.
- Replace speculative advice with verified constraints. If browser, framework, SDK, or runtime behavior is version-sensitive, state the limitation and tell the agent how to verify it.
- Remove duplicated wrappers when the upstream official skill or plugin is already the better maintained source of truth. Link or attribute instead of re-wrapping by default.
- Treat large aggregators as candidate pools, not import targets. Normalize or discard placeholder text, duplicated copies, and template-grade descriptions before adoption.
- Add scripts only when deterministic execution matters.
- Keep the normalized skill understandable without reading the upstream repo first.
