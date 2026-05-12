# Output Case Template

Use this file as the starting point for `brief.md`.

## Required Fields

- `case_id`
- `skill`
- `mode`
- `goal`
- `why_this_case_matters`
- `success_condition`
- `known_limits`

## Example

```text
case_id: case-001
skill: technical-writing-editor
mode: manual-seeded
goal: Check whether the skill turns vague technical prose into direct, concrete writing.
why_this_case_matters: This skill should improve real engineering docs, not just paraphrase them.
success_condition: The skill-assisted output is more concrete and more actionable than the baseline without changing the meaning.
known_limits: This case is seeded by hand and should not be used as the only evidence for promotion.
```
