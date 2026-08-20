---
name: skill-librarian
description: Search, recommend, refresh, and lifecycle-manage the local skill library. Use when the user needs the best existing skill for a task, a catalog refresh, repository triage, or a promotion/archive decision for house skills.
---

# Purpose

Use this skill to operate the library itself: search what already exists, refresh tracked sources, explain repository shape, and make lifecycle decisions for house skills.

This skill is for library operations. It is not the place to normalize an upstream skill body or compress an existing house skill in place.

For upstream sources, the maintained unit is the tracked repository list and its indexed outputs. Do not assume every mirrored repository needs deep understanding or active maintenance.

## When To Use

Use this skill when one or more of these are true:

- the user asks which skill fits a task
- the local catalog needs to be searched, rebuilt, or refreshed
- a skill repository needs to be triaged as source mirror, index-only source, or conversion candidate
- a `young` house skill needs promotion, retention, or archival review
- the user wants a compact view of what the local skill library contains

Do not use this skill to rewrite a specific upstream skill into house format. Hand that work to `$skill-converter`.

Do not use this skill to compress or tighten an existing house skill body. Handle that as direct skill-authoring work after reviewing the local skill-authoring conventions.

## Inputs

- the task query, repository path, or lifecycle question
- the repository root, either from the user's path or by locating `catalog/tracked_repos.json`
- whether upstream refresh is actually required
- the relevant catalog files, tracked repository list, or target house skill path

If the catalog or generated summaries are stale for the requested task, rebuild them before making strong claims.

## Workflow

1. Classify the request:
   decide whether the task is `query`, `refresh`, `repository triage`, or `lifecycle review`.
2. Treat the repository root as the default root:
   use `catalog/tracked_repos.json` as the source of truth for tracked repositories.
3. Maintain the list before the mirrors:
   update or reason about `catalog/tracked_repos.json` and generated catalog outputs first. Only inspect a specific upstream repository deeply when the current task actually depends on it.
4. Search before you create:
   for recommendations, search the catalog first:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "<task keywords>"
```

5. Verify or synchronize only when needed:
   without `--sync`, verify already-materialized repositories against their locked URLs and SHAs. This mode does not clone, fetch, or check out and exits nonzero when a mirror is missing or mismatched:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD"
```

   For first materialization or explicit restoration to the locked commits, add `--sync`.

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD" --sync
```

6. Rebuild generated views when inputs changed:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
```

7. Audit the tracked list when it changes:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

8. For recurring operational maintenance, prefer the single-entry daily flow:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --pull
```

9. Apply repository triage rules:
   identify whether a repository is an official library, aggregator, curated list, reference spec, or domain library, then say whether it should be mirrored, indexed, or partially converted.
10. Apply recommendation rules:
   prefer catalog entries marked `reviewed-core` for execution. Treat hash-mismatched or unlisted core skills, `house-skills/young`, and upstream mirrors as reference-only. Return the smallest set of high-fit options instead of long dumps.
11. Apply lifecycle rules:
   review `young` skills using actual reuse evidence and policy thresholds before proposing promotion or archival.

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/gc_young_skills.py --root "$PWD"
```

12. Keep telemetry out of skill bodies:
    retrieval counting belongs in the managing agent layer, not inside `SKILL.md`.
13. When operating the MCP entrypoint, retain stdio as the default and use standard Streamable HTTP only on loopback. Streamable HTTP is deliberately stateless; select JSON or SSE POST responses according to the client. Keep write mode off, and use an SSH tunnel or same-host TLS/authenticating reverse proxy for remote access. Treat `--auth-token-env` as a pre-shared-token gate, not OAuth.

## Output Contract

Return:

1. the smallest set of recommended skills, triage decisions, or lifecycle decisions that answers the request
2. the commands or generated artifacts actually used, when operational work was performed
3. a short note on anything skipped because refresh, verification, or evidence was not available

## Validation

- Do not recommend creating a new skill before searching the existing catalog when search is available.
- Do not treat a mirrored upstream repository as a managed codebase unless the task explicitly requires repository-level inspection or conversion.
- Do not claim a refresh happened unless the refresh command actually ran successfully.
- Do not report remote-derived recommendations when upstream refresh failed or was not verified.
- Only claim that `memory.md` or another output file was updated if it actually changed.
- Promotion to `core` should require repeated successful reuse, not aesthetic preference.
- Promotion is not runtime approval. After reviewing a promoted skill's complete payload, a code owner must update its deterministic SHA-256 in `catalog/reviewed_core.lock.json`; only an exact match receives catalog and MCP `reviewed-core` status.
- Verify MCP changes with a real client handshake and `tools/list` plus `tools/call`; an HTTP status-only check is insufficient.
- If a task requires rewriting a skill body rather than operating the library, hand off to the correct authoring skill.

## Sources

- [references/house-skill-spec.md](references/house-skill-spec.md)
- [references/skill-quality-rubric.md](references/skill-quality-rubric.md)
- [references/tracked-repo-policy.md](references/tracked-repo-policy.md)
