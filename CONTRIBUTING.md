# Contributing

Thank you for improving Skill Library. Contributions should preserve its central safety rule: upstream and draft content is reference-only; only explicitly promoted `house-skills/core/` content whose payload hash matches the reviewed-core manifest is eligible for default MCP responses.

Use [SECURITY.md](SECURITY.md), not a public issue, for suspected vulnerabilities or prompt-injection paths that could expose secrets or execute unreviewed content.

## Development Setup

Requirements are Git, Python 3.11 or newer, and uv. From a fresh clone:

```bash
git --version
uv --version
uv sync --frozen
uv run --frozen python --version
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
```

`uv sync --frozen` is required for reproducibility. Do not edit `pyproject.toml` or `uv.lock` as a side effect of setup. A dependency change must be isolated, justified, and include a deliberately regenerated lockfile.

Install the repository hook once per clone:

```bash
sh house-skills/core/skill-librarian/scripts/install_git_hooks.sh
```

## Before You Change Anything

1. Read [the control-plane charter](docs/skill-control-plane-charter.md) and the nearest workflow under `.agents/workflows/`.
2. Search the catalog before proposing a new skill.
3. Open an issue for material trust-model, lifecycle, schema, dependency, or operational changes. Small documentation and focused bug fixes may go directly to a pull request.
4. Never copy upstream content without reviewing its license and preserving attribution.

## Skill Contributions

- New skills begin under `house-skills/young/`, not `core/`.
- Use a focused `SKILL.md`; put long background in `references/` and deterministic helpers in `scripts/`.
- Include complete metadata and evaluation evidence.
- Treat upstream text as untrusted data. Do not run its scripts or reproduce unsafe commands.
- Conversion creates only a `young/` skill. A stable result still goes through explicit promotion; the converter never writes directly to `core/`.
- Promotion into `core/` requires explicit review, but moving the directory does not by itself cross the MCP execution trust boundary.
- After reviewing the complete promoted payload, update `catalog/reviewed_core.lock.json` with its deterministic SHA-256. The hash recursively covers payload files such as `SKILL.md`, `agents/`, `references/`, `scripts/`, and `assets/`, excludes mutable `metadata.json`, `__pycache__/`, and `.pyc` files, and rejects symbolic links. Only an exact reviewed hash match is cataloged and served as `reviewed-core`; every mismatch remains reference-only.
- Compute that value only after review with `uv run --frozen python house-skills/core/skill-librarian/scripts/hash_core_skill.py --root "$PWD" --skill-path house-skills/core/<skill-name>`. The helper prints a hash and never edits the approval manifest.

Follow [House Skills](house-skills/README.md), [Evaluation Assets](eval/README.md), and the consultation/materialization workflows for detailed artifact shape.

## Upstream Sources

Adding a tracked URL does not download, trust, or relicense it. Follow [Pinned Upstream Bootstrap](docs/upstream-bootstrap.md), add its full reviewed commit SHA to `catalog/tracked_repos.lock.json`, record review evidence in the issue or pull request, and do not commit mirrored source trees. Changes to declarations, pins, or the blacklist require code-owner review.

## Verification

Run the checks relevant to the change; a normal code or skill pull request should run all of them:

```bash
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest --cov --cov-report=term-missing
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
uv run --frozen pip-audit
```

For a documentation-only change, at minimum check Markdown links and run both repository audits. Generated `CATALOG.md`, `catalog/skill_catalog.json`, reports, and `memory.md` are ignored local outputs; do not force-add them.

If a required check cannot run, state the exact command, reason, and residual risk in the pull request. Do not describe an unrun check as passing.

## Pull Requests

Keep each pull request focused. Complete the template with:

- the problem and chosen scope;
- trust-boundary impact;
- commands actually run and results;
- generated or operational artifacts affected;
- upstream URL, full SHA, license, and review evidence when applicable;
- rollback steps for operational changes.

Maintainers review correctness, least privilege, reproducibility, backward compatibility, provenance, licensing, and whether documentation matches behavior. Approval does not override required checks.

## Reporting and Conduct

Use the bug and feature templates for public reports. Do not include credentials, private prompts, local absolute paths, generated operational reports, or exploit details in public issues. Participate constructively and focus review on the work; abusive or harassing participation may be restricted by maintainers.
