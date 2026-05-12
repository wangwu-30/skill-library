# Skill Consultation Decision Template

Last updated: 2026-04-08

Use this template when a new request arrives and the agent must decide whether to:

- reuse an existing skill
- update an existing skill
- create a new draft skill
- do no skill work at all

This template is for internal control-plane decisions.

It is the decision logic a future runtime may expose, but the reasoning and evidence should be produced here first.

## Purpose

The goal is to stop improvising "search or create" decisions.

Every consultation should answer:

1. what the user is actually trying to accomplish
2. what current skill assets already cover
3. where the real gap is, if any
4. whether that gap deserves a new house skill
5. what the next action should be

## Required Inputs

- the incoming request
- the intended user outcome, not just the literal wording
- current catalog candidates
- relevant house skills
- any repeated workflow evidence or prior evaluation assets
- any constraints that materially change the decision, such as repo scope, compliance, or runtime limits

## Decision Sequence

### Step 1: Normalize the Need

Write a one-paragraph statement of the need in this form:

```text
Need:
- The user is trying to achieve:
- The outcome should change:
- The task is repeated / likely repeated because:
- The likely workflow layer is:
```

Possible workflow layers:

- `editing`
- `research`
- `conversion`
- `project bootstrap`
- `library operations`
- `domain execution`
- `other`

If you cannot name the workflow layer, do not create a new skill yet.

### Step 2: Search Existing Coverage

Search the catalog first.

Record:

```text
Existing candidates:
- skill:
  fit:
  why:
- skill:
  fit:
  why:
```

Use at least:

- one search across the whole catalog
- one house-skill-first pass

If no meaningful candidates appear, say so explicitly instead of skipping the step.

### Step 3: Check the Best Existing Fit

For the strongest candidate, answer:

```text
Best current fit:
- skill:
- what it already covers:
- what it does not cover:
- whether the missing part is central or peripheral:
```

If the missing part is peripheral, prefer `reuse existing`.

If the missing part is central but still close to the skill's purpose, prefer `update existing`.

### Step 4: Run Gap Assessment

Only do this after checking the best fit.

Use this structure:

```text
Gap assessment:
- has_gap:
- missing capability:
- why existing skills are insufficient:
- evidence that this gap is repeated rather than one-off:
- maintenance cost if a new skill is created:
```

A gap is real only if all of these are true:

- the missing capability changes execution, not just wording
- the existing skill would become incoherent if stretched to absorb it
- the workflow is likely to recur
- the maintenance burden is justified

### Step 5: Choose One Decision

Use exactly one of these:

#### `reuse existing`

Choose this when:

- one current skill already covers the main workflow
- any missing detail can be handled by normal task reasoning
- creating or updating a skill would add more maintenance than leverage

Required output:

```text
Decision: reuse existing
Skill:
Why:
Next action:
```

#### `update existing`

Choose this when:

- an existing skill is clearly the right home
- the missing behavior is important
- adding that behavior does not break the skill boundary

Required output:

```text
Decision: update existing
Skill:
What is stale, weak, or missing:
Why this belongs in the existing skill:
Next action:
```

#### `create draft`

Choose this when:

- the workflow is distinct
- it is likely to recur
- existing skills are not a clean fit
- the gap changes execution enough to deserve its own trigger surface

Required output:

```text
Decision: create draft
Suggested name:
Suggested description:
Smallest reusable unit:
Why this is distinct:
Next action:
```

Use `draft` language on purpose. A consultation decision should not imply automatic promotion or automatic public exposure.

#### `no skill needed`

Choose this when:

- the request is one-off
- the task is better handled directly
- the request is just a fact lookup, explanation, or ordinary implementation step
- the only justification for a new skill is topic breadth or personal preference

Required output:

```text
Decision: no skill needed
Why:
What to do instead:
```

## Output Template

Use this full shape in consultation notes:

```text
Consultation summary:
- request:
- normalized need:
- workflow layer:

Existing candidates:
- skill:
  fit:
  why:

Best current fit:
- skill:
- what it covers:
- what it misses:

Gap assessment:
- has_gap:
- missing capability:
- repeated evidence:
- maintenance cost:

Decision:
- reuse existing | update existing | create draft | no skill needed

Action:
- exact next move

Evidence:
- docs, eval assets, prior sessions, or catalog hits used
```

## Anti-Patterns

Do not:

- create a new skill before searching the catalog
- recommend a new skill because the topic sounds important
- treat one bug or one awkward prompt as enough evidence for a new skill
- recommend `update existing` and `create draft` at the same time
- hide a weak decision behind long summaries

## Fast Heuristics

If you need a quick rule:

- `reuse existing` when the fit is already good
- `update existing` when the home is right but the guardrail is weak
- `create draft` when the workflow is distinct and likely to recur
- `no skill needed` when the task should just be done directly

## Relationship to Evaluation

Consultation should reference evaluation assets when they exist.

Strong signals include:

- trigger eval assets under `eval/trigger/`
- output eval assets under `eval/output/`
- repeated usage evidence
- prior documented failures

If a decision depends on a skill that has no evaluation assets yet, say that explicitly.
