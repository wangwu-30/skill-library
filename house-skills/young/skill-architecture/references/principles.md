# Principles

Read this reference before defining boundaries or carriers.

## Capability before artifact

Define a user-visible capability by its job, inputs, outputs, failure boundary, and owner before naming files or folders. One capability should solve one coherent decision or execution problem. Split only when users, triggers, outputs, authority, risk, or release cadence differ materially.

Do not treat a directory, prompt, provider, or tool as a capability. Do not create a broad coordinator that silently owns every unresolved concern.

## Carrier fit

Choose the narrowest carrier that preserves the contract:

- `SKILL.md`: concise trigger, decision sequence, and required output.
- `references/`: detailed or conditional knowledge loaded only when needed.
- `scripts/`: deterministic, repeatable behavior whose correctness should not depend on prose interpretation.
- `assets/`: output material to copy or transform, not instructions to reason over.

Keep the carrier separate from authority. A script can implement a deterministic step without becoming the owner of policy, lifecycle, state, or evaluation.

## Single authority

Every fact that must be kept current has one authority. Every decision has one accountable owner. Other components may read, propose, validate, or execute under contract, but may not silently become a second source of truth.

Name state only when it is necessary. If no persistent fact is required, declare state authority `none`; do not introduce state merely to coordinate.

## Explicit handoffs

A handoff names the sender, receiver, payload schema, routing predicate, expected outcome, error return, and side-effect boundary. Plain-language “then use X” is not a contract. Preserve data needed for audit and rollback without leaking credentials or private content.

## Evolution is designed

Prefer compatible additions and stable interfaces. When a boundary must change, name callers, migration order, deprecation signal, rollback point, and evidence that permits removal. A deprecation without an owner or safe restoration target is not a plan.
