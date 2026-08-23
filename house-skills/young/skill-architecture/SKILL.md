---
name: skill-architecture
description: "Design a composable skill system: capability boundaries, carriers, ownership, DAG routing, handoffs, and evaluation contracts."
---

# Purpose

Design the architecture of a skill system before catalog, runtime, or lifecycle work begins. Define one capability boundary, its carrier layer, accountable owner, dependency DAG, routing and handoff contracts, and evidence needed to evolve it safely.

This skill does not search a catalog; convert or materialize content; run or score evaluations; promote, archive, or version lifecycle state; calculate trust hashes; deliver at runtime; or own operational state. Hand those concerns to their canonical owners.

## When To Use

- Design, split, merge, or retire skill capabilities.
- Decide which layer carries instructions, deterministic tools, reference knowledge, or templates.
- Define ownership, routing, handoffs, compatibility, rollout, or rollback for a multi-skill system.
- Design evaluation intent and acceptance evidence before an evaluation owner implements or runs it.
- Recommend how a skill system should evolve without changing its catalog, runtime, or lifecycle.

Do not use for a single-skill edit with no boundary decision, catalog discovery, conversion, execution/scoring, promotion/archive, trust verification, runtime delivery, or state mutation.

## Inputs

- Goal, users, tasks, constraints, and failure costs.
- Existing skills, carriers, owners, runtime entrypoints, and known state authorities.
- Required interfaces, compatibility promises, evaluation evidence, and rollout constraints.
- Known unknowns and the decision deadline.

Read [principles](references/principles.md) first. Read [capability and composition](references/capability-and-composition.md) when selecting boundaries, carriers, ownership, or routes. Read [evaluation contract](references/evaluation-contract.md) when designing evidence.

## Workflow

1. State the decision, in-scope users and tasks, non-goals, constraints, and success criterion. List unknowns; do not invent runtime facts.
2. Map user-visible capabilities. Give every capability one job, one owner, one canonical carrier, declared inputs and outputs, and a state authority only when it genuinely owns state. Reject overlapping catch-all skills.
3. Choose the narrowest carrier: instructions for judgment, references for conditional detail, scripts for deterministic repeat work, and assets for output material. Do not introduce a carrier merely for organization.
4. Build an acyclic composition DAG. Mark entry capabilities, reusable components, dependency direction, routing predicates, handoff payloads, terminal outcomes, and failure returns. Keep selection separate from execution and state mutation.
5. Specify component contracts: trigger, required and optional inputs, output schema, errors, side effects, ownership, compatibility boundary, and evidence anchor. Name the canonical owner for catalog search, materialization, evaluation execution/scoring, lifecycle, trust, runtime delivery, and state when they participate.
6. Choose one recommendation: `reuse`, `refactor`, `create`, `deprecate`, or `defer`. Explain alternatives rejected, migration and rollback, compatibility impact, and what must remain unchanged.
7. Define evaluation design, not execution: representative triggers, expected routing, contract assertions, negative cases, safety boundaries, and pass/fail evidence. Hand implementation and scoring to the evaluation owner.
8. Return the architecture package. Escalate unresolved authority, state, compatibility, or safety decisions instead of disguising them as implementation detail.

## Output Contract

Return one decision-ready architecture package containing:

1. **Recommendation** — exactly one enum value: `reuse`, `refactor`, `create`, `deprecate`, or `defer`; include rationale and rejected alternatives.
2. **Capability map** — each capability's purpose, boundary, users/tasks, carrier layer, inputs, outputs, side effects, and state authority or `none`.
3. **Owner matrix** — accountable owner and consulted/dependent owners for every capability and control-plane concern.
4. **DAG** — nodes, directed dependencies, entrypoints, routing predicates, handoff payloads, terminal outcomes, failure paths, and proof that no cycle remains.
5. **Component contracts** — trigger, input/output schema, error and side-effect boundary, compatibility promise, and evidence anchor for each component.
6. **Exact artifacts** — paths and minimal changes for skill bodies, references, scripts/assets if justified, catalog records, runtime adapters, lifecycle records, and evaluation fixtures; mark each as `create`, `modify`, `none`, or `owned elsewhere`.
7. **Compatibility** — callers affected, preservation rules, migration sequence, deprecation signal, and rollback point.
8. **Evaluation** — designed cases, assertions, negative cases, evidence required, and the owner who executes and scores them.
9. **Rollback** — trigger, safe restoration target, owner, and data/state limitations.
10. **Unknowns** — unresolved facts, decision owner, risk, and the evidence needed to close each.

Use stable names and artifact paths. State `none` or `unknown` explicitly; do not imply that this architecture recommendation has created, searched, converted, evaluated, promoted, hashed, delivered, or mutated anything.

## Validation

- Every capability has one purpose, one accountable owner, and one canonical carrier; overlapping ownership is resolved or listed as an unknown.
- The DAG is acyclic, every route has a terminal or failure outcome, and every handoff names its payload and receiving owner.
- Carrier choices follow [principles](references/principles.md); scripts and assets exist only when justified.
- Catalog search, materialization, evaluation execution/scoring, lifecycle, trust, runtime delivery, and state are explicitly outside this skill or assigned to canonical owners.
- Recommendation, artifacts, compatibility, evaluation design, rollback, and unknowns are complete enough for their owners to act without reopening the boundary decision.
- No recommendation claims evidence that has not been gathered or validation that has not been run.

## Sources

- [principles](references/principles.md)
- [capability and composition](references/capability-and-composition.md)
- [evaluation contract](references/evaluation-contract.md)
- [source notes](references/source-notes.md)
