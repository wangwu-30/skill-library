# Skill Draft Materialization Template

Last updated: 2026-04-08

Use this template after a consultation ends with:

- `Decision: create draft`
- or `Decision: update existing`

This document defines how to turn a consultation decision into a controlled repository change.

It is intentionally narrower than a full implementation plan.

The purpose is to answer:

1. what should be written
2. where it should live
3. what evidence justifies it
4. what must be checked before calling the draft real

## When To Use

Use this template when:

- a consultation already concluded that a new draft skill is justified
- a consultation already concluded that an existing skill must be updated
- the next agent needs a bounded materialization plan instead of re-running the consultation

Do not use this template before the consultation decision is explicit.

## Required Inputs

- consultation summary
- decision type: `create draft` or `update existing`
- evidence that justified the decision
- target stage, usually `young`
- the smallest reusable unit being materialized

## Materialization Record

Use this shape:

```text
Materialization summary:
- consultation decision:
- target action:
- target skill:
- target stage:
- owner:

Reason:
- why this change is justified now

Scope:
- what will be added or changed
- what will not be added yet

Evidence:
- catalog evidence:
- eval evidence:
- repeated workflow evidence:
- known gaps that remain:

Planned artifacts:
- SKILL.md
- metadata.json
- agents/openai.yaml
- references/
- scripts/

Validation plan:
- audit steps:
- manual checks:
- follow-up eval needed:
```

## Decision Types

### `create draft`

Use this when the workflow is distinct enough to deserve a new trigger surface.

Required fields:

```text
Suggested name:
Suggested description:
Smallest reusable unit:
Why existing skills are not the right home:
Why this starts in young:
```

Default location:

```text
house-skills/young/<skill-name>/
```

### `update existing`

Use this when an existing skill is the right home, but it is stale, too vague, or missing an important guardrail.

Required fields:

```text
Target skill:
What is missing or stale:
Why this belongs in the existing skill:
What should remain unchanged:
```

## Planned Artifacts

Use the smallest set that supports repeated reuse.

### Always Required

- `SKILL.md`
- `metadata.json`
- `agents/openai.yaml`

### Add `references/` When

- the draft needs examples, rubrics, long notes, or source explanations
- keeping the detail in `SKILL.md` would make the trigger surface harder to read

### Add `scripts/` When

- deterministic execution matters
- the same transformation would otherwise be rewritten repeatedly

## Validation Checklist

Before calling the materialization done, confirm:

- the draft still matches the consultation decision
- the scope did not silently expand
- the description is specific enough to search for
- the workflow is bounded
- the output contract makes the stop condition obvious
- any supporting files actually exist
- house-skill integrity audit still passes if `house-skills/` changed

## Promotion Warning

Materializing a draft does not imply:

- promotion
- wide reuse
- external exposure
- stable public API

The draft starts as evidence-backed `young` inventory, not as a final answer.

## Anti-Patterns

Do not:

- turn one consultation result into a broad multi-purpose skill
- add references or scripts "just in case"
- upgrade a draft to `core` because the concept sounds important
- treat materialization as a replacement for later trigger or output evaluation

## Fast Heuristic

If the draft feels broad, shrink it.

If the draft feels like a topic summary, rewrite it as an execution contract.

If the draft feels correct but not repeatedly useful, do not materialize it yet.
