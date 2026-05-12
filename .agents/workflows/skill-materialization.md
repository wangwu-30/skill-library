# Skill Materialization Workflow

Use this workflow after a consultation has already concluded that a skill should be created or updated.

## Inputs

- the consultation output
- supporting evidence
- the target skill name or target existing skill
- target stage, usually `young`

## Workflow

1. Read [docs/skill-draft-materialization-template.md](/Users/wangwu/claude/skills/docs/skill-draft-materialization-template.md).
2. Confirm the consultation decision is explicit:
   `create draft` or `update existing`.
3. Restate the smallest reusable unit before editing any files.
4. For `create draft`:
   scaffold the skill in `house-skills/young/`.
5. For `update existing`:
   keep the existing skill boundary and only add what the consultation justified.
6. Create only the smallest required artifact set:
   `SKILL.md`, `metadata.json`, `agents/openai.yaml`, and optional `references/` or `scripts/`.
7. If `house-skills/` changed, run:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root /Users/wangwu/claude/skills
```

8. Report:
   what was materialized, what remains unevaluated, and what evidence justified the change.

## Done Criteria

- the change matches the consultation decision
- the materialized scope stayed narrow
- required files exist
- supporting references exist when cited
- audit passes when house skills changed
