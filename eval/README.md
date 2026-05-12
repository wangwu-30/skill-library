# Skill Evaluation Assets

This directory holds evaluation assets for the local skill library.

The goal is to make skill quality review concrete instead of relying on taste.

Use this directory to answer two separate questions:

1. `Trigger quality`: does a skill get consulted when it should, and stay out of the way when it should not
2. `Output quality`: once the skill is consulted, does it improve the result

Do not treat all evaluation artifacts as equally trustworthy.

Evaluation artifacts should always declare their mode:

- `manual-seeded`: created by hand to define the case shape or a worked example
- `manual-reviewed`: a human reviewed real outputs and recorded the result
- `client-observed`: a client run was observed and the trigger decision was recorded
- `automated`: a repeatable script generated the result

`manual-seeded` artifacts are useful for examples and templates, but they are not enough for promotion decisions by themselves.

## Layout

```text
eval/
├── README.md
├── rubrics/
│   └── house-skill-output-scorecard.md
├── templates/
│   ├── output-case.md
│   ├── trigger-train-queries.json
│   └── trigger-validation-queries.json
├── trigger/
│   └── <skill-name>/
│       ├── README.md
│       ├── train_queries.json
│       ├── validation_queries.json
│       └── run-notes.md
└── output/
    └── <skill-name>/
        └── <case-id>/
            ├── brief.md
            ├── input.md
            ├── baseline.md
            ├── skill-assisted.md
            └── scorecard.md
```

## Trigger Evaluation Conventions

Use trigger evaluation to test the `description` field.

Each skill under `eval/trigger/<skill-name>/` should include:

- `train_queries.json`: the queries used to improve or challenge the current description
- `validation_queries.json`: a held-out set used only to check whether improvements generalize
- `run-notes.md`: how the run was observed, by which client, and whether the results are trustworthy enough to cite

Each query object should include:

- `id`
- `query`
- `should_trigger`
- `why`

If you have actual trigger observations, record them in `run-notes.md` or in a sibling `results/` directory.

Do not silently mix synthetic judgments with real client-observed trigger data.

## Output Evaluation Conventions

Use output evaluation to test whether the skill changes the answer in a useful way.

Each case under `eval/output/<skill-name>/<case-id>/` should include:

- `brief.md`: what is being tested and why it matters
- `input.md`: the request or artifact being worked on
- `baseline.md`: a response without explicitly using the skill
- `skill-assisted.md`: a response shaped by the skill workflow
- `scorecard.md`: a scored comparison using the shared rubric

If the case uses real client output, say so clearly.

If the case is a seeded example, say so clearly.

## Naming Rules

- Skill directory names must match the skill folder name, for example `technical-writing-editor`
- Case IDs should be stable and sequential, for example `case-001`
- Do not overwrite an old scored case unless it was incorrect; add a new case instead

## Promotion Rule

Promotion to `core` should not rely on:

- one seeded example
- one manual opinion
- one successful trigger case

Promotion evidence should eventually combine:

- trigger quality
- output quality
- repeated use
- maintenance burden

## First Use

If you are starting from scratch:

1. copy the trigger and output templates from `eval/templates/`
2. choose one existing `young` skill
3. create train and validation query sets
4. create one output case
5. score the baseline and skill-assisted versions
6. decide whether the next move is `tighten description`, `tighten workflow`, `keep in young`, or `archive`
