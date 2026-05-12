# Skill Quality Rubric

Use this rubric to judge whether something is a good skill, a bad skill, or simply the wrong packaging layer.

## Important Distinction

This rubric evaluates a file **as a skill**, not as knowledge in the abstract.

A skill can be low quality because:

- it is badly packaged as a skill
- it should have been a reference file, workflow, or repo entrypoint instead
- it tries to encode tacit judgment in abstract slogans rather than in examples, process, or environment

So "bad skill" does not always mean "useless content."

## Core Test

A good skill should answer all of these:

1. When should it trigger?
2. What inputs must be gathered?
3. What workflow should the agent follow?
4. What output shape is expected?
5. How is completion validated?

If a file cannot answer most of these, it may still contain useful ideas, but it is weak **as a skill**.

## Rating Levels

### Strong Skill

- frontmatter is searchable and specific
- `When To Use`, `Inputs`, `Workflow`, `Output Contract`, `Validation`, and `Sources` are present or clearly equivalent
- the workflow changes execution behavior rather than repeating principles
- detailed material is pushed into `references/` or `scripts/`
- another agent could use it without upstream context

### Medium Skill

- trigger is clear
- at least part of the workflow is operational
- some validation exists
- still missing one or two critical pieces such as inputs, output contract, or source boundaries

These are often salvageable by compression and normalization.

### Weak Skill

- broad or fuzzy trigger
- mostly principles, style advice, or role-play framing
- little or no explicit workflow
- no output contract
- no real validation
- skill body duplicates what should live in references, scripts, or environment

These are weak as reusable execution contracts even if the topic is good.

## Common Failure Modes

- instruction pile: keeps adding principles instead of changing process
- persona theater: tells the model to "be expert" instead of giving operational support
- wrong layer: reference material stuffed into `SKILL.md`
- boundary blur: one skill tries to do search, conversion, implementation, and review at once
- unverifiable completion: no way to tell when the task is actually done

## Repository-Level Interpretation

When evaluating a whole repository:

- do not ask whether every file is useless
- ask whether the repository mostly contains strong skill-shaped execution contracts
- distinguish "knowledge quality" from "skill packaging quality"
- prefer a few strong, reusable skills over a large pile of weak wrappers

## Practical Rule

If a skill feels informative but not executable, it is probably a weak skill and should be converted into one of:

- a smaller skill
- a `references/` document
- a script
- a repo-level `Agent.md`
- a workflow file
