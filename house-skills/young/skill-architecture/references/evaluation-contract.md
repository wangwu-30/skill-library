# Evaluation Contract

Read this reference when the architecture needs evidence or an evaluation design. This skill designs the contract; an evaluation owner implements, executes, and scores it.

## Required evaluation design

For every recommendation that creates, refactors, or deprecates a capability, specify:

| Area | Design requirement |
|---|---|
| Representative triggers | Typical requests that should select the intended capability |
| Boundary negatives | Similar requests that must not select it |
| Routing | Expected entrypoint, selected path, and terminal outcome |
| Contract | Required inputs, outputs, typed errors, side-effect limits |
| Composition | Handoff payload and owner at each edge |
| Compatibility | Existing callers and preserved behavior |
| Safety | Forbidden authority, secret handling, state mutation, or unsafe fallback |
| Evidence | Artifact, trace, fixture, contract test, or review record needed to decide pass/fail |

Use observable assertions. “Looks useful” or “agent understood” is not pass/fail evidence. Do not require a specific provider narrative when the contract can be asserted from outputs, routing, and controlled side effects.

## Minimum case set

Design at least one case for each applicable category:

1. intended trigger routes to the correct capability;
2. near-miss trigger is rejected or routed elsewhere;
3. missing or malformed input returns the declared error;
4. downstream handoff preserves the required schema;
5. compatibility caller follows the migration path;
6. forbidden action is not taken;
7. rollback restores the named safe boundary.

Record omissions with reason and risk. Keep test data synthetic or redacted.

## Decision evidence

The architecture output must name who will execute and score each case, where evidence will live, and which failure blocks rollout. It must not report cases as passed unless the evaluation owner provides actual results.
