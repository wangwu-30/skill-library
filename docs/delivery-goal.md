# Delivery Goal

The project should become a live skill librarian agent.

The core job is simple:

1. keep syncing and indexing good public skill sources
2. keep local house skills organized through their full lifecycle
3. provide skill consultation to other agents for a target scenario
4. provide or scaffold a skill when a matching one does not exist
5. support multi-version skill experiments before promotion

## Target Shape

The system has three layers.

```text
host agent
  decides what scenario needs a skill
  sends one task intent and uses the returned skill

MCP server
  exposes one agent-facing intent tool
  hides search, draft, usage, and lifecycle machinery

deterministic scripts
  sync tracked repositories
  rebuild catalog
  scaffold drafts
  record usage
  review lifecycle state
  promote/archive/experiment with explicit calls
```

## Live Agent

The live agent is the scheduled maintenance loop.

It should:

- refresh tracked sources when requested
- rebuild the generated catalog
- run house-skill and tracked-repo audits
- review young skills for keep/promote/archive candidates
- write machine-readable reports
- avoid applying destructive lifecycle changes unless explicitly requested

The live loop should be runnable from cron, launchd, Codex automation, or a long-running local process.

## Consultation

For a target scenario, the host agent should be able to ask:

- here is what I am trying to do; give me the skill I should use

The skill librarian then decides internally:

- whether an existing skill is strong enough
- whether usage should be recorded
- whether a temporary `house-skills/young` skill should be created
- which nearby examples are useful as source material

If a strong skill exists, the system returns it. If no skill exists, the system creates a controlled
temporary skill draft and returns that. The host agent should not need to understand the catalog or
lifecycle internals.

## Lifecycle

House skills move through:

- `young`: new, experimental, or recently converted
- `core`: proven, stable, repeatedly useful
- `archive`: stale, replaced, expired, or low-value

Lifecycle movement should be evidence-led. Usage counts alone are not enough for promotion, but they are useful signals.

Default behavior:

- review and recommend
- apply only on explicit tool call or user/agent decision

## Multi-Version Experiments

Skill experiments should not overwrite a working skill.

Instead:

1. fork the base skill into a `young` variant
2. preserve lineage in `metadata.json`
3. mark the variant as an experiment
4. run it in real tasks
5. promote, merge, or archive later

This keeps experimentation cheap without making the library unstable.
