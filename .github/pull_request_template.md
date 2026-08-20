## Summary

Describe the problem, scope, and outcome.

## Trust and provenance

- Trust-boundary impact: none / reviewed-core / writes / upstream handling
- Upstream source URL and full commit SHA, if applicable:
- Upstream license and attribution review, if applicable:
- New filesystem, network, credential, or command-execution permissions:

## Verification

List commands actually run and their results. Do not mark an unrun check as passing.

- [ ] `uv sync --frozen`
- [ ] `uv run --frozen ruff check .`
- [ ] `uv run --frozen ruff format --check .`
- [ ] `uv run --frozen pytest --cov --cov-report=term-missing`
- [ ] `uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"`
- [ ] `uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"`
- [ ] `uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"`
- [ ] `uv run --frozen pip-audit`
- [ ] relevant smoke test or evaluation
- [ ] documentation links checked

Explain skipped checks and residual risk:

## Operations and rollback

Describe generated artifacts, monitoring changes, migration steps, and rollback. Write `Not applicable` when none.

## Checklist

- [ ] The change is focused and does not include generated catalog or operational reports.
- [ ] New skills start in `young`; any later promotion to `core` includes explicit review evidence.
- [ ] A promoted or changed core payload is marked `reviewed-core` only after code review updates its matching hash in `catalog/reviewed_core.lock.json`.
- [ ] Untrusted upstream content is not made executable by default.
- [ ] No credentials, private prompts, customer data, or sensitive local paths are included.
