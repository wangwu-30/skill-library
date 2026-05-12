# Agent Usage

This project is meant to be used by agents, not only read by humans.

The simple rule is: give the skill librarian one task intent and use the skill it returns.

Internally, the librarian searches first, consults the best match when one exists, creates a small
`house-skills/young` skill when nothing fits, and lets lifecycle checks keep useful skills or
archive stale ones later.

## Install For An MCP Client

Copy [examples/mcp-client-config.json](../examples/mcp-client-config.json) into your agent client's MCP config and replace `/path/to/skills` with this repository path.

This is a client-side launch entry. It is not something the project reads at runtime. For MCP stdio servers, the client starts a local process using `command` and `args`, then communicates with that process over stdin/stdout.

For a clone at `/path/to/skills`, the server entry is:

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

The server is implemented with the official Python MCP SDK (`mcp.server.fastmcp.FastMCP`). It auto-builds `catalog/skill_catalog.json` if the generated catalog is missing.

## Direct Commands

Search before creating:

```bash
python3 house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "technical blog"
```

Consult a skill and record usage:

```bash
python3 house-skills/core/skill-librarian/scripts/skill_consult.py --root "$PWD" technical-blog-editor
```

Run the MCP server manually:

```bash
uv run --with mcp python house-skills/core/skill-librarian/scripts/skill_mcp_server.py --root "$PWD"
```

Audit the library:

```bash
python3 house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
python3 house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

## MCP Tool

The MCP server exposes only one normal agent-facing tool:

- `skill_request(intent, context="", allow_temporary=true)`

Example intent:

```text
The agent needs to deploy a GitHub project, but it has not done this workflow before.
```

The response is either an existing skill or a temporary `house-skills/young` skill. The caller does
not need to call search, consult, draft, or lifecycle tools directly.

Search, audit, promotion, archive, sync, and experiment management are still available as internal
scripts for the live librarian and maintainers.

## Agent Policy

Do not make skill creation mystical.

If you do not know how a good skill should be written, collect good examples, compare them, and write down the parts that survive contact with real work.

If the library gets large, do not browse by hand. Ask the skill-library MCP server. Use what fits. Write what is missing. Archive what goes stale.

## Live Maintenance

Run one deterministic maintenance pass:

```bash
python3 house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD"
```

Run as a long-lived local loop:

```bash
python3 house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --interval-minutes 1440
```

The live loop does not make reasoning decisions. It refreshes, indexes, audits, reviews lifecycle signals, and writes reports. Host agents or users decide when to create, promote, archive, or experiment.
