# Skill Maintain Agent

## What This Project Is

This workspace is a local skill library and house-skill runtime.

It has two jobs:

1. mirror and index external skill repositories
2. create, refine, promote, and archive internally managed house skills

Work here should optimize for reuse, retrieval quality, and operational clarity, not for collecting more files.

The maintained unit for upstream sources is the tracked repository list in `catalog/tracked_repos.json`, not deep semantic ownership of every mirrored repository. By default, treat upstream mirrors as indexed source pools unless the current task explicitly requires deeper inspection of one of them.

## Reading Order

Read in this order before doing substantial work:

1. [README.md](README.md)
2. [docs/skill-control-plane-charter.md](docs/skill-control-plane-charter.md)
3. [CATALOG.md](CATALOG.md)
4. [house-skills/README.md](house-skills/README.md)
5. the relevant house skill under `house-skills/core` or `house-skills/young`
6. the relevant decision template under `docs/` if the task is consultation or materialization
7. the workflow file in `.agents/workflows/` if the task matches it

For current run facts, prefer `CATALOG.md` and `memory.md` over assumptions.

## IDE Adapter Policy

`Agent.md` is the canonical project guidance file for this repository.

If this repo also exposes `AGENTS.md`, `CLAUDE.md`, or Cursor rule files, treat them as thin compatibility adapters that defer to `Agent.md` instead of becoming parallel sources of truth.

## Repo Map

- `catalog/tracked_repos.json`: source of truth for tracked upstream repositories
- `catalog/blacklisted_repos.json`: repositories intentionally excluded from the tracked list so they are not reintroduced casually
- `catalog/skill_catalog.json`: generated machine-readable index of discovered skills
- `CATALOG.md`: generated human-readable summary of the indexed library
- `memory.md`: durable notes from deterministic maintenance runs
- `docs/skill-control-plane-charter.md`: repo charter plus roadmap for the control plane
- `docs/skill-consultation-decision-template.md`: internal decision template for reuse, update, draft, or no-skill-needed
- `docs/skill-draft-materialization-template.md`: bounded template for turning a consultation decision into a controlled repo change
- `eval/`: trigger and output evaluation assets for skill quality
- `house-skills/core/`: stable house skills that should be preferred
- `house-skills/young/`: trial house skills under TTL and promotion review
- `house-skills/archive/`: expired or replaced house skills kept for provenance
- `house-skills/config/lifecycle.json`: shared lifecycle thresholds
- `.agents/workflows/skill-consultation.md`: repeatable consultation flow for deciding reuse vs update vs draft
- `.agents/workflows/skill-evaluation.md`: repeatable flow for trigger and output evaluation
- `.agents/workflows/skill-materialization.md`: repeatable flow for materializing a consultation decision into repo artifacts

## Bootstrap

Search before you create:

```bash
python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "<keywords>"
```

Consult a house skill through the CLI runtime (records usage automatically):

```bash
python3 house-skills/core/skill-librarian/scripts/skill_consult.py --root "$PWD" <skill-name>
```

For control-plane work, start from the charter and matching workflow:

- consultation: [docs/skill-consultation-decision-template.md](docs/skill-consultation-decision-template.md) and [skill-consultation.md](.agents/workflows/skill-consultation.md)
- evaluation: [eval/README.md](eval/README.md) and [skill-evaluation.md](.agents/workflows/skill-evaluation.md)
- materialization: [docs/skill-draft-materialization-template.md](docs/skill-draft-materialization-template.md) and [skill-materialization.md](.agents/workflows/skill-materialization.md)

Rebuild the catalog when repository contents change:

```bash
python3 house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
```

Refresh tracked repositories when the task actually requires upstream updates:

```bash
uv run house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD"
```

Run the deterministic daily maintenance flow when the request is operational rather than ad hoc:

```bash
python3 house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --pull
```

Audit house-skill integrity after changing `house-skills/`:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
```

Audit tracked repository integrity after changing `catalog/tracked_repos.json`:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

Install repo-tracked git hooks once per clone:

```bash
sh house-skills/core/skill-librarian/scripts/install_git_hooks.sh
```

Maintain the tracked repository list first. Only open or inspect a specific upstream repository deeply when the current task actually depends on that repository's internals.

## Work Types

Classify each request into one primary mode before acting:

1. `Query`
   recommend, search, explain, or triage the skill library
2. `Consultation`
   decide whether to reuse, update, draft, or skip skill work
3. `Evaluation`
   create or update trigger and output evidence for a skill
4. `Refresh`
   maintain the tracked repository list, pull tracked repositories, rebuild indexes, or update generated catalog outputs
5. `Author`
   create a new house skill from repeated local need
6. `Refactor`
   compress, normalize, or tighten an existing house skill
7. `Lifecycle`
   review `young` skills for promotion, retention, or archival

Do not mix modes unless the later step is required to complete the first one correctly.

## Execution Contract

You are maintaining a skill system, not performing random one-off edits.

An agent may stop only in one of these states:

1. `Verified Done`
   the requested library or house-skill change is complete and the affected outputs were checked
2. `Real Blocker`
   progress now requires missing credentials, network approval, or an actual user decision
3. `Safety Stop`
   continuing would risk destructive or misleading repository changes

Not acceptable:

- recommending or creating a skill before searching the existing catalog when search is available
- treating every mirrored upstream repository as something that must be deeply understood or actively edited
- creating a new house skill when a small refactor of an existing one would solve the problem
- promoting a skill to `core` without repeated successful reuse
- claiming an upstream refresh happened when it did not
- writing telemetry instructions into skill bodies
- keeping divergent guidance across `Agent.md`, `AGENTS.md`, `CLAUDE.md`, or Cursor rules
- treating generated files as current if the underlying inputs changed and regeneration was skipped
- editing house skills without re-checking metadata, required sections, and linked reference files

## House Skill Rules

- Prefer `house-skills/core` over `young` when both fit.
- New house skills start in `house-skills/young` unless the user explicitly asks otherwise.
- Keep `SKILL.md` focused on execution contract: trigger, inputs, workflow, output, validation, sources.
- Move long detail into `references/`.
- Add `scripts/` only when deterministic execution matters.
- When converting or compressing, preserve only the minimum reusable unit.
- If a lesson is durable, update a project guidance file; if it is run-specific, write it to `memory.md` only when a maintenance flow actually updates it.

## Control Plane Rules

- Treat this repository as the `Skill Control Plane`, not the public runtime.
- The core system is the skill quality pipeline: source trust, structural validation, trigger evaluation, output evaluation, consultation, and lifecycle.
- Search is required before proposing new draft skills.
- Consultation should produce exactly one decision: `reuse existing`, `update existing`, `create draft`, or `no skill needed`.
- Materialization should follow an explicit consultation decision; do not jump straight from vague need to new skill files.
- Seeded evaluation examples are useful, but they are not authoritative promotion evidence by themselves.

## Repo Development Skills

Use only the smallest set of house skills that materially improve the task:

- `skill-librarian`: search, index, recommend, refresh, and lifecycle-manage the library
- `skill-converter`: normalize external skills into house format
- `perfect-skill-template`: compress a draft or bloated skill into a minimal execution contract
- `project-agent-bootstrap`: update this repository's own agent entrypoint or maintenance workflow when the operating model drifts

If none fit cleanly, create a new `young` house skill instead of overloading an existing one.

## Reporting Contract

Every completion report should make four things obvious:

- what changed
- what was verified
- what remains unverified
- why the result is done, blocked, or intentionally left in `young`
