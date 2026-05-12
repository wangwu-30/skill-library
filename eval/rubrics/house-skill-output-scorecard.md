# House Skill Output Scorecard

Use this rubric to compare a baseline answer against a skill-assisted answer.

Score each category from `0` to `5`.

- `0`: actively harmful
- `1`: much worse than needed
- `2`: weak
- `3`: acceptable
- `4`: strong
- `5`: excellent

## Categories

### 1. Intent Fit

Does the answer actually solve the user's task, not a nearby task.

### 2. Behavioral Lift

Does using the skill create a visible improvement over the baseline, rather than just making the answer longer.

### 3. Concrete Technical Grounding

Does the answer name real artifacts such as file paths, commands, components, APIs, schemas, or failure modes when they matter.

### 4. Boundary Accuracy

Does the answer stay inside the skill's intended scope and avoid solving the wrong layer of the problem.

### 5. Actionability

Can a reviewer tell what to do next, what not to do, or what changed because of the skill.

### 6. Noise Control

Does the answer remove fluff, boilerplate, and generic filler instead of adding more of it.

## Comparison Rules

When scoring a case:

1. score the baseline answer first
2. score the skill-assisted answer second
3. note any regression explicitly
4. write one short reason per category

## Passing Heuristic

Treat a case as a useful win only when all of these are true:

- the skill-assisted answer improves at least `2` categories by `1` point or more
- no important category regresses by more than `1`
- the skill-assisted answer does not become materially noisier

## Promotion Warning

One good output case is not enough to promote a skill.

Use this rubric to generate evidence, not to replace lifecycle judgment.
