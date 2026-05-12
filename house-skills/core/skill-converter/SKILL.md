---
name: skill-converter
description: Convert an external skill into the internal house format, preserve source attribution, and keep the normalized result concise, searchable, and operational. Use when a useful upstream skill should become a local house skill.
---

# Purpose

Use this skill to turn an external or upstream skill into a local house skill.

This skill is for conversion from outside the house library. It is not the right tool for searching the library or for tightening an existing house skill body.

## When To Use

Use this skill when one or more of these are true:

- an upstream skill is useful but too large, noisy, or vendor-specific to keep as-is
- a repository contains a good pattern that should become a local house skill
- only a small reusable slice of a large skill pack should be preserved locally
- a normalized house-format wrapper is needed for repeated local use

Do not use this skill for library search, refresh, or lifecycle triage. Hand that work to `$skill-librarian`.

Do not use this skill to compress or refactor an existing house skill. Hand that work to `$perfect-skill-template`.

## Inputs

- source repository URL or local upstream path
- source skill path or the closest reusable unit inside the upstream source
- target house skill name
- one-sentence searchable trigger description
- the scripts, references, or assets worth preserving

If any of these are missing, infer the smallest safe subset and state the assumption.

## Workflow

1. Read [references/house-skill-spec.md](references/house-skill-spec.md).
2. Inspect the upstream source and identify the minimum independently triggerable unit.
3. Keep only the operating instructions, references, and scripts needed for repeated local use.
4. Rewrite the frontmatter description so another agent can discover the skill by task words, artifacts, and constraints.
5. Preserve attribution in the `## Sources` section and in `references/source-notes.md`.
6. Put new converted skills in `house-skills/young` first unless the user explicitly asks for a stable core skill.
7. If you are creating a new normalized skill, scaffold it with:

```bash
python3 house-skills/core/skill-converter/scripts/init_converted_skill.py \
  --name "<skill-name>" \
  --description "<trigger description>" \
  --source-repo "<repo-url>" \
  --source-path "<path>" \
  --author "<owner or org>"
```

8. Move large supporting material into `references/` instead of bloating `SKILL.md`.
9. Add scripts only when deterministic behavior matters or the same logic would otherwise be rewritten repeatedly.
10. Keep the normalized skill understandable without reading the upstream repository first.

## Output Contract

Return:

1. the normalized house skill path
2. what was preserved from upstream
3. what was intentionally removed or externalized
4. its lifecycle stage, usually `young`
5. any remaining gaps or follow-up work

## Validation

- Confirm the normalized skill contains `SKILL.md`, `metadata.json`, and `agents/openai.yaml`.
- Confirm the frontmatter `name` is hyphen-case and the `description` is searchable.
- Confirm attribution is preserved.
- Confirm the normalized skill can be understood without reading the upstream repository first.
- Confirm the result is actually a conversion from external source material, not a refactor of an existing house skill.

## Sources

- [references/house-skill-spec.md](references/house-skill-spec.md)
- [references/conversion-checklist.md](references/conversion-checklist.md)
