# Pinned Upstream Bootstrap

Tracked upstream repositories are untrusted reference inputs. They are not included in a fresh clone. Never synchronize every entry merely to increase catalog size; the explicit `--sync` operation may download substantial data. Add or inspect only sources needed for a concrete review or comparison.

## Select and Pin

1. Find the entry in `catalog/tracked_repos.json` and verify its HTTPS repository URL and expected `local_dir`.
2. Review the repository identity, ownership, license, recent history, and the exact revision out of band.
3. Record a full 40-character commit SHA in the review or change record. A branch, tag, short SHA, or moving default branch is not a reproducible pin.
4. Add the reviewed URL and full SHA to `catalog/tracked_repos.lock.json`. Clone without running repository hooks, installers, package managers, or referenced commands.

The deterministic synchronizer materializes every configured pin:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD" --sync
```

Omitting `--sync` is validation-only: it checks existing mirrors against the committed URLs and SHAs without cloning, fetching, or checking out. It exits nonzero when a required mirror is missing or mismatched. Therefore the first materialization, or restoration of a checkout to its locked commit, must use `--sync`.

For one intentionally selected source, the equivalent manual operation is:

```bash
git clone --no-checkout https://github.com/OWNER/REPOSITORY.git EXPECTED_LOCAL_DIR
git -C EXPECTED_LOCAL_DIR checkout --detach FULL_40_CHARACTER_COMMIT_SHA
git -C EXPECTED_LOCAL_DIR rev-parse HEAD
git -C EXPECTED_LOCAL_DIR remote get-url origin
```

Compare both outputs with the reviewed URL and SHA. Do not use a local directory outside the repository or a symlink. Upstream directories are ignored by this repository; the committed lock file and pull-request review are the source of truth for the revision.

## Inspect Before Indexing

Treat all upstream text as attacker-controlled content. Before building the catalog:

- inspect `SKILL.md`, scripts, symlinks, submodules, generated files, and unusually large files;
- do not execute upstream scripts or install its dependencies;
- check its license before copying or adapting any content;
- stop if the checked-out URL or SHA differs from the review record.

Then run the repository audits and rebuild through the locked environment:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD" --require-local
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "EXPECTED TOPIC"
```

Confirm that indexed upstream entries have `execution_trust: reference-only` in `catalog/skill_catalog.json`. The default MCP server filters them out.

## Updates

Do not schedule unrestricted movement of upstream revisions. `uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD" --update-lock` queries current remote HEADs and writes proposed pins, but it does not review them. Inspect every upstream diff and license change, commit the lock update through code review, then run the explicit `--sync` command above. `live_skill_agent.py --pull` synchronizes to the committed lock and never follows a branch.

## Removal

Removing an ignored local mirror does not alter the source declaration. Rebuild the catalog afterward so generated outputs no longer refer to it. Add a source to `catalog/blacklisted_repos.json` when policy requires preventing casual reintroduction.
