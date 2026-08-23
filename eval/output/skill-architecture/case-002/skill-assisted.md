# Skill-assisted response — manual-seeded illustration, not a live run

Create one carrier per concern:

| Concern | Carrier | Rule |
| --- | --- | --- |
| Trigger, inputs, bounded workflow, output, validation | SKILL.md | Keep only the reusable execution contract. |
| Rationale, vendor examples, taxonomy, long decision tables | references/ | Link from the step that needs it; references do not become a second workflow. |
| Repeatable parsing, checks, or transformations | scripts/ | Add only with explicit inputs/outputs and a verification command. |
| Selection ownership and conflict/no-match policy | router/control-plane policy | The skill declares its boundary; it does not self-route. |
| Promotion and payload-hash approval | lifecycle/governance artifacts | Do not embed a self-approval checklist in a draft skill. |

Move only details required by a workflow step into linked references. Keep examples out of the
main contract unless they disambiguate its trigger. Do not run materialization: this request is
an architecture decision, and any subsequent file change should follow the consultation and
materialization paths.
