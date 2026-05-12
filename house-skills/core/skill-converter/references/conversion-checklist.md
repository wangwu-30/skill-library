# Conversion Checklist

Use this checklist when turning an upstream skill into a house skill.

## Keep

- the core trigger conditions
- the minimum workflow steps that make the skill reusable
- deterministic helper scripts if they are clearly valuable
- domain reference files that are likely to be reused

## Remove

- marketplace or vendor-specific promotion
- duplicate examples that do not change behavior
- giant catalogs when only one subskill is needed
- setup notes that are irrelevant in the local environment

## Preserve

- upstream URL
- upstream path
- upstream author or organization
- short conversion notes explaining what changed
- lifecycle metadata for the new house skill
- skill `version`, metadata `schema_version`, and current `owner`
- default lineage fields: `derives_from`, `replaces`, and `compatibility`

## Review Questions

Ask these questions before finalizing:

1. Can another agent discover this skill from the description alone?
2. Is the output contract explicit enough to compare results?
3. Did we preserve the smallest useful slice instead of copying a whole pack?
4. Would a wrapper skill be better than a full conversion?
5. Should this begin life in `young` instead of `core`?
