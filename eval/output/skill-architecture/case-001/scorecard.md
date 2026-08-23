# Scorecard

Mode: manual-seeded; scores compare authored illustrations, not client output.

| Category | Baseline | Assisted | Reason |
| --- | ---: | ---: | --- |
| Intent Fit | 2 | 5 | Assisted answers the requested router architecture and trust constraint. |
| Behavioral Lift | 1 | 5 | Assisted introduces owned layers, tie-breaking, and no-match behavior. |
| Concrete Technical Grounding | 1 | 5 | Assisted grounds the design in young/core status and reviewed_core.lock.json. |
| Boundary Accuracy | 0 | 5 | Baseline would route untrusted material; assisted keeps source, policy, and runtime distinct. |
| Actionability | 2 | 5 | Assisted provides implementation responsibilities and fallback rules. |
| Noise Control | 3 | 4 | Assisted is compact despite necessary boundary detail. |

Passing heuristic: **passes** — assisted improves at least two categories by one or more,
has no material regression, and is not materially noisier. A trust-boundary violation would
fail this case regardless of total score. This single seeded pass is not promotion evidence.
