# Skill Consultation Workflow

Use this workflow when a request raises the question:

- which skill should handle this
- should an existing skill be updated
- should a new `young` skill draft be created
- should the work be done directly with no new skill

## Inputs

- the incoming request
- any relevant repo or workflow context
- current catalog results
- existing house skills that seem relevant
- evaluation assets when they exist

## Workflow

1. Read [docs/skill-consultation-decision-template.md](/Users/wangwu/claude/skills/docs/skill-consultation-decision-template.md).
2. Normalize the need:
   write the real user outcome and the workflow layer before searching.
3. Search the catalog before proposing any new draft:

```bash
python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root /Users/wangwu/claude/skills --query "<keywords>"
```

4. Review the best current fit:
   prefer house skills over upstream skills when the fit is real.
   Consult a house skill through the runtime to load its body and record usage:

   ```bash
   python3 house-skills/core/skill-librarian/scripts/skill_consult.py --root /Users/wangwu/claude/skills <skill-name>
   ```
5. Run the gap assessment:
   identify whether the missing behavior is central, repeated, and distinct enough to justify maintenance.
6. Choose exactly one decision:
   `reuse existing`, `update existing`, `create draft`, or `no skill needed`.
7. If the decision is `update existing` or `create draft`, cite the evidence that justifies the change:
   repo workflows, evaluation assets, repeated failure modes, or repeated session patterns.
8. If a new draft is justified, keep it in `house-skills/young`.
9. Report the decision using the consultation output shape from the template.

## Done Criteria

- the catalog was searched first
- the best current fit was checked explicitly
- the result contains exactly one decision
- the next move is obvious to the next agent
- no new skill is proposed without repeated-value justification
