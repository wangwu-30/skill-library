# Capability and Composition

Read this reference when designing the capability map, ownership, DAG, route, or handoff.

## Capability map template

For each capability, record:

| Field | Required content |
|---|---|
| Name | Stable, user-meaningful noun or verb phrase |
| Boundary | What it does and explicitly does not do |
| Users/tasks | Triggering need, not an implementation label |
| Carrier | Skill body, reference, script, asset, or external service |
| Inputs/outputs | Minimum schema or typed shape |
| Side effects | `none` or declared external/persistent effects |
| State authority | Canonical owner or `none` |
| Accountable owner | One role, team, or component |
| Evidence | Stable artifact, test, contract, or decision record |

## Ownership matrix

Separate architecture ownership from adjacent operations:

| Concern | Architecture role | Canonical operational owner |
|---|---|---|
| Capability boundary and composition | Define and recommend | Architecture owner |
| Catalog discovery | Consume result only | Catalog/search owner |
| Conversion or materialization | Specify required contract only | Converter/authoring owner |
| Evaluation execution and scoring | Design assertions only | Evaluation owner |
| Lifecycle promotion/archive | State compatibility needs only | Lifecycle owner |
| Trust/hash verification | Name required trust boundary only | Trust owner |
| Runtime delivery | Specify entry/handoff boundary only | Runtime owner |
| Persistent or workflow state | Identify authority only | State owner |

If a row has no current owner, report it as an unknown with a decision owner. Do not make the architecture skill the default owner.

## DAG and routing rules

Draw a directed edge only when one component consumes the other component's declared output. A component may depend on shared references, but references do not create orchestration authority.

For every entrypoint specify:

1. trigger predicate and priority when predicates overlap;
2. selected first node;
3. handoff schema between nodes;
4. success terminal, expected failure terminal, and return path;
5. owner that resolves ambiguous routes.

Reject cycles. If a feedback loop is required, externalize it as a bounded stateful workflow owned elsewhere; specify its input/output interface and stop condition rather than embedding a hidden loop in skill routing.

## Component contract template

```text
component:
  trigger: <predicate>
  inputs: <required / optional schema>
  outputs: <success schema>
  errors: <typed failures and receiver>
  side_effects: <none or declared boundary>
  owner: <accountable owner>
  compatibility: <promise and callers>
  evidence: <artifact or test>
```

Use the smallest schema that permits routing and validation. Secrets, prompts, transient provider traces, and mutable state handles belong in their own guarded contracts, not generic handoff payloads.
