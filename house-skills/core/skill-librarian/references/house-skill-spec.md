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
│   └── optional-domain-notes.md
└── scripts/
    └── optional-deterministic-helper.py
```

## Required frontmatter

`SKILL.md` must include:

- `name`: lowercase hyphen-case
- `description`: short trigger description that explains when to use the skill

## Lifecycle metadata

`metadata.json` should include at least:

- `stage`: `young`, `core`, or `archive`
- `status`: short lifecycle status such as `active`, `stable`, or `archived`
- `schema_version`: metadata schema version
- `version`: semver for the skill contract itself
- `owner`: current maintainer
- `created_at`
- `updated_at`
- `last_used_at`
- `use_count`
- `expires_at`
- `usage_tracking`: object with at least `mode`
- `derives_from`: null or one lineage object for a prior house-skill ancestor
- `replaces`: list of prior house-skill versions or sibling skills superseded by this version
- `compatibility`: object with `backward_compatible` and optional notes
- `source`

Shared lifecycle thresholds should come from `house-skills/config/lifecycle.json`.
Do not embed tracking commands or telemetry instructions inside skill content.

## Versioning Rules

- `schema_version` tracks metadata format changes only.
- `version` should use semver and describe the skill contract another agent depends on.
- `derives_from` should be used only when this skill is a direct evolution of another house skill, not just because both talk about the same topic.
- `replaces` should capture the old version or skill path this version superseded.
- `compatibility.backward_compatible=false` is the flag that says callers should expect changed behavior.
- Patch: wording, examples, reference cleanup, or non-behavioral edits.
- Minor: backward-compatible workflow additions, clearer guardrails, or extra validation that does not break expected outputs.
- Major: breaking trigger changes, output-contract changes, or validation requirements that would surprise an agent using the previous version.
- When rollback value matters, archive the replaced version instead of silently erasing it.
- Prefer `python3 house-skills/core/skill-librarian/scripts/bump_house_skill_version.py --root "$PWD" --skill-path <path> --bump <patch|minor|major> --snapshot-current` when changing house-skill versions.

## Usage Tracking Modes

- `none`: no trustworthy recording surface exists yet, so counts are not evidence.
- `manual`: counts were recorded by a maintainer or script and are advisory.
- `hub`: counts came from an authoritative skill hub or equivalent system.

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

## Consultation response format

When another agent asks for the right skill, answer with:

1. Best-fit skill path
2. Why it fits
3. Gaps or risks
4. Whether a conversion or wrapper skill is needed

## Conversion rules

- Prefer copying the smallest useful subset instead of mirroring large upstream trees.
- Rewrite the trigger description so it is specific and searchable.
- Move large docs into `references/` instead of bloating `SKILL.md`.
- Add scripts only when deterministic execution matters.
- Keep the normalized skill understandable without reading the upstream repo first.
