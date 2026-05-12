# Skill Library

This project has one plain idea:

> Do not guess how skills should work. Collect good ones, study them, keep the useful patterns, and let an agent manage the library.

There are two problems here.

First, writing a good skill is not obvious. A lot of skills are just prompts with a fancy folder name. Some are useful because they change the agent's actual workflow: when to trigger, what to read, what to do, what to output, and how to verify that the job is done. The fastest way to learn the difference is to collect good public examples, compare them, and distill a local house style.

Second, once skills start to pile up, humans should not manage them by memory. The library needs an agent-facing interface: search first, consult when a fit exists, write a new skill only when there is a real gap, and recycle old skills that stop being useful.

That is all this repo is trying to do. It is not a grand platform. It is a practical skill shelf with a librarian.

Status: this is still an early demo. The important part is the loop, not this exact implementation.

## What It Does

- tracks public skill repositories in `catalog/tracked_repos.json`
- indexes discovered `SKILL.md` files into a generated catalog
- keeps local house skills under `house-skills/`
- provides scripts to search, consult, audit, refresh, and lifecycle-manage skills
- runs a live maintenance loop for scheduled sync and lifecycle review
- exposes the library to agents through one small MCP intent tool

The mirrored upstream repositories are local source pools. They are used for learning, search, and comparison. They are not the main thing this repo publishes.

## Install For Agents

Use the MCP server from your agent client. The JSON below is not a project runtime config; it is a client-side MCP server entry. In stdio mode, the MCP client starts the server process with `command` and `args`, then talks to it over stdin/stdout.

```json
{
  "mcpServers": {
    "skill-library": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "python",
        "/path/to/skills/house-skills/core/skill-librarian/scripts/skill_mcp_server.py",
        "--root",
        "/path/to/skills"
      ]
    }
  }
}
```

The same template lives in [examples/mcp-client-config.json](examples/mcp-client-config.json).

The MCP server exposes one tool:

- `skill_request(intent, context="", allow_temporary=true)`

The caller says what it is trying to do. The skill librarian handles the rest:
search the catalog, reuse a strong match, record house-skill usage, or create a
temporary `house-skills/young` skill when nothing good exists.

The maintenance operations are intentionally not MCP tools. Search, audit,
promotion, archive, sync, and experiment management stay behind the librarian as
CLI scripts and scheduled jobs. A normal agent should not need to know that
machinery exists.

The server uses the official Python MCP SDK (`mcp.server.fastmcp.FastMCP`). The `uv run --with mcp ...` form makes the client entry copy-pasteable for a fresh clone: the client launches the server with that command, and `uv` provides the `mcp` package.

See [docs/agent-usage.md](docs/agent-usage.md) for direct commands and agent policy.
See [docs/delivery-goal.md](docs/delivery-goal.md) for the full target: live agent, lifecycle management, consultation, on-demand skill materialization, and multi-version experiments.

On a fresh clone, the MCP server will build `catalog/skill_catalog.json` if it is missing. You can also build it explicitly:

```bash
python3 house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
```

## Human Commands

Search for a skill:

```bash
python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "react playwright"
```

Consult a house skill and record usage:

```bash
python3 house-skills/core/skill-librarian/scripts/skill_consult.py --root "$PWD" technical-blog-editor
```

Rebuild the generated catalog:

```bash
python3 house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
```

Run audits:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
python3 house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

Review young skills:

```bash
python3 house-skills/core/skill-librarian/scripts/gc_young_skills.py --root "$PWD"
```

Run one live maintenance pass:

```bash
python3 house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD"
```

Run continuously every 24 hours:

```bash
python3 house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --interval-minutes 1440
```

## Repository Layout

- `catalog/tracked_repos.json`: curated upstream source list
- `catalog/blacklisted_repos.json`: sources that should not be casually reintroduced
- `catalog/skill_catalog.json`: generated machine-readable catalog
- `CATALOG.md`: generated human-readable catalog summary
- `house-skills/core`: stable local skills
- `house-skills/young`: new or experimental local skills
- `house-skills/archive`: retired skills kept for provenance
- `house-skills/core/skill-librarian`: search, audit, catalog, MCP, and lifecycle scripts
- `house-skills/core/skill-converter`: helpers for turning external patterns into house skills
- `eval/`: trigger and output evaluation assets
- `.agents/workflows/`: repeatable maintenance workflows

Generated catalog outputs and mirrored upstream repositories are ignored by git by default. The open-source surface should stay focused on the control logic and house skills.

## Why Not Just Use Existing Skill Repos?

| Approach | What Works | Where It Breaks |
| --- | --- | --- |
| Random prompt collection | Fast to start | Hard to know which ones are executable |
| One big awesome list | Good discovery | No lifecycle, no local quality bar |
| Hand-written local skills only | Fits your work | Easy to overfit and miss better patterns |
| This repo | Collect first, distill second, manage with an agent | Needs ongoing curation |

The important move is not the specific tooling. The move is to stop treating skills as one-off prompt files and start treating them as reusable work contracts.

## What A Good Skill Looks Like Here

A strong house skill answers:

- when should it trigger
- what inputs should the agent gather
- what workflow should it follow
- what output shape should it return
- how should completion be verified

Long explanations go into `references/`. Deterministic work goes into `scripts/`. The `SKILL.md` should stay small enough that another agent can actually use it.

## Current Status

The local catalog has indexed thousands of `SKILL.md` files from tracked public sources. The exact count changes when the catalog is rebuilt, so treat `CATALOG.md` as generated output, not source truth.

The public repository is a sanitized open-source slice. It keeps the librarian, scripts, specs, and generic house skills. Private archives, raw conversation traces, mirrored upstream checkouts, and generated catalog outputs are intentionally left out.

The maintained source of truth is:

- `catalog/tracked_repos.json` for upstream sources
- `house-skills/` for local reusable skills
- `house-skills/core/skill-librarian/scripts/` for the management loop

## Roadmap

- keep the MCP server as a one-intent agent entrypoint
- add better ranking than simple token matching
- improve temporary skill quality from nearby examples
- add outcome scoring for skill experiments
- add more trigger and output evaluation cases
- add an HTTP/daemon MCP mode for team or hosted use
- keep promotion and archival explicit unless policy says otherwise

The near-term goal is simpler: make it easy for an agent to ask, "Is there already a skill for this?" and get a useful answer.
