# Skill Evaluation Workflow

Use this workflow when you need evidence that a house skill is actually good, not just well formatted.

## Inputs

- target skill path
- why the skill is being evaluated now
- whether the goal is trigger quality, output quality, or both
- whether a client-observed trigger run is available

## Workflow

1. Read [docs/skill-control-plane-charter.md](/Users/wangwu/claude/skills/docs/skill-control-plane-charter.md) to confirm the evaluation goal.
2. Read [eval/README.md](/Users/wangwu/claude/skills/eval/README.md) for directory and evidence conventions.
3. Create or update `eval/trigger/<skill-name>/`:
   add `train_queries.json`, `validation_queries.json`, and `run-notes.md`.
4. If a client can reveal whether the skill was consulted:
   run the train and validation sets multiple times and record the observed trigger behavior.
5. Create or update at least one case under `eval/output/<skill-name>/<case-id>/`:
   include `brief.md`, `input.md`, `baseline.md`, `skill-assisted.md`, and `scorecard.md`.
6. Score the baseline and skill-assisted outputs using [eval/rubrics/house-skill-output-scorecard.md](/Users/wangwu/claude/skills/eval/rubrics/house-skill-output-scorecard.md).
7. Decide the next action:
   tighten description, tighten workflow, keep in `young`, or archive.
8. If the evaluation changes house-skill files, run:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root /Users/wangwu/claude/skills
```

## Done Criteria

- the evaluation artifacts are checked into `eval/`
- the evaluation mode is labeled clearly
- seeded examples are not presented as authoritative usage evidence
- the result produces one clear next action for the skill
