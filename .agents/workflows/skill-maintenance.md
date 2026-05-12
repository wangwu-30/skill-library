# Skill Maintenance Workflow

Use this workflow for requests that change the library itself rather than only consuming it.

## Inputs

- the user request
- the relevant house skill or upstream source path
- whether upstream refresh is actually required
- the expected end state: query, refresh, author, refactor, or lifecycle decision

## Workflow

1. Classify the request into one primary work type.
2. Read `Agent.md`, then the relevant house skill, then any directly referenced `references/` files.
3. If the task is query-like, search the catalog before proposing creation or conversion.
4. If the task changes repository contents, update generated outputs only when the underlying inputs changed.
5. If the task creates or refactors a house skill:
   create the smallest reusable unit,
   keep it in `house-skills/young`,
   and include `metadata.json` plus `agents/openai.yaml`.
6. If the task reviews lifecycle state, prefer evidence from actual reuse over aesthetic preference.
7. Validate the changed artifact directly:
   commands exist, linked references exist, metadata is complete, and the skill can be used without upstream context.
8. If `house-skills/` changed, run:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root /Users/wangwu/claude/skills
```

9. If `catalog/tracked_repos.json` changed, run:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root /Users/wangwu/claude/skills
```

10. If hooks are not installed yet, run:

```bash
sh house-skills/core/skill-librarian/scripts/install_git_hooks.sh
```

11. Report using the repo reporting contract from `Agent.md`.

## Done Criteria

- the affected skill or catalog artifact exists in the correct place
- section order and metadata match house conventions
- no misleading claim is made about refresh, validation, or promotion
- the next agent can tell what to do without rereading the whole repository
