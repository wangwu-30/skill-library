# Agent Usage

The supported agent interfaces are MCP stdio and standard Streamable HTTP. Stdio remains the default. Both are read-only by default and return only skills that the catalog marks `reviewed-core`. A path under `house-skills/core/` is necessary but not sufficient: the current deterministic payload SHA-256 must also match the code-reviewed entry in `catalog/reviewed_core.lock.json`. Upstream mirrors, `young` drafts, unlisted core skills, and changed core payloads remain reference material.

## Install

From the repository root, verify Git, Python 3.11+, and uv, then install the locked environment:

```bash
git --version
uv --version
uv sync --frozen
uv run --frozen python --version
```

Build and audit the local catalog before connecting a client:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

Optional upstream repositories are not included. Follow [Pinned Upstream Bootstrap](upstream-bootstrap.md) if reference material beyond the included house skills is required.

## Configure a Client

Copy the `skill-library` entry from [the example](../examples/mcp-client-config.json) into the MCP configuration understood by your client. Replace both absolute-path placeholders; do not rely on `$PWD`, `~`, or client-specific variable expansion. Ensure the GUI or service process that launches the client can find `uv`, then restart the client.

The configuration starts:

```bash
uv run --frozen --project /absolute/path/to/skill-library python /absolute/path/to/skill-library/house-skills/core/skill-librarian/scripts/skill_mcp_server.py --root /absolute/path/to/skill-library
```

This is a client-side process launch, not a file read by the repository. Configuration locations differ by client; use the client's official MCP documentation rather than guessing a filename.

## Streamable HTTP

Use Streamable HTTP for URL-based MCP clients, local service supervisors, or a same-host reverse proxy. This request/response-only server always uses the protocol's stateless mode so long-running processes do not retain client sessions. JSON response mode also avoids long-lived SSE responses:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_mcp_server.py \
  --root "$PWD" \
  --transport streamable-http \
  --json-response
```

Configure the client endpoint as `http://127.0.0.1:8000/mcp`; [the URL client example](../examples/mcp-streamable-http-client-config.json) shows the common `url` form. Omit `--json-response` when a client requires SSE-formatted POST responses. Stateful sessions are intentionally unavailable because the pinned MCP SDK does not yet guarantee bounded cleanup after explicit session termination.

The HTTP service always binds to `127.0.0.1`, `localhost`, or `::1`; it refuses `0.0.0.0`, LAN, and public addresses. It also:

- validates `Host` and any supplied `Origin` to resist DNS rebinding;
- accepts additional trusted values through repeatable `--allowed-host` and `--allowed-origin`;
- limits each request body to 64 KiB before JSON parsing;
- ignores proxy-forwarding headers;
- keeps write mode disabled by default.

For a controlled local deployment, require a pre-shared Bearer token through an environment variable rather than argv:

```bash
export SKILL_LIBRARY_MCP_TOKEN='<at-least-32-random-non-whitespace-characters>'
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_mcp_server.py \
  --root "$PWD" \
  --transport streamable-http \
  --json-response \
  --auth-token-env SKILL_LIBRARY_MCP_TOKEN
```

Send `Authorization: Bearer <token>` on every POST, GET, and DELETE request. This is a pre-shared-token gate, not MCP OAuth discovery or token issuance. For remote access, keep the server on loopback and use an SSH tunnel or a same-host TLS/authenticating reverse proxy. Set proxy request limits no larger than 64 KiB. Multi-user or federated deployments require a standards-based OAuth resource server or authentication proxy.

HTTP write mode additionally requires `--allow-writes`, `--auth-token-env`, and the caller's `allow_temporary=true`. The process refuses unauthenticated HTTP write mode.

## Smoke Test

First verify that the server imports and reaches its stdio wait state:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_mcp_server.py --root "$PWD"
```

No normal stdout output is expected while it waits for MCP protocol input. Stop the manual check with `Ctrl-C`. Unexpected Python tracebacks indicate a setup or catalog error.

After configuring the client:

1. confirm `skill_request` appears in the client's MCP tool list;
2. call it with `intent="Find a skill for maintaining this skill catalog"`;
3. accept either `decision: reuse-existing-skill` or `decision: no-fit`;
4. if a skill is returned, confirm `skill_path` is under `house-skills/core/`.

The server may build the ignored catalog files on first use. It must not return or execute upstream or `young` content. For core skills, catalog generation recomputes the deterministic payload SHA-256 recursively across files including `SKILL.md`, `agents/`, `references/`, `scripts/`, and `assets/`; mutable `metadata.json`, `__pycache__/`, and `.pyc` files are excluded, and symbolic links are rejected. Only a value matching `catalog/reviewed_core.lock.json` receives `reviewed-core` status.

## Tool Contract

```text
skill_request(intent, context="", allow_temporary=false)
```

- `intent` is required and limited to 2,000 characters.
- `context` is optional and limited to 8,000 characters.
- `allow_temporary` defaults to `false`. It cannot enable writes unless the server operator also used `--allow-writes`.
- no strong reviewed-core match produces `decision: no-fit`; the host agent should continue without injecting unreviewed instructions.

## Write-Enabled Mode

Write-enabled mode can create a draft under `house-skills/young/` and record usage metadata. It does not make the new draft reviewed or executable in later default MCP requests. Enable it only for a trusted, single-user maintainer client:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_mcp_server.py --root "$PWD" --allow-writes
```

The caller must additionally pass `allow_temporary=true`. Review all resulting changes before retaining them.

## Direct Maintainer Commands

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "technical blog"
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_consult.py --root "$PWD" skill-librarian
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

CLI catalog search includes reference-only upstream entries. Search results are evidence for review, not permission to execute their instructions.

## Operations

Run one deterministic pass:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD"
```

Use `--pull` (the maintenance compatibility name for locked sync) to clone missing mirrors or restore clean mirrors to the committed pins:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --pull
```

The one-shot process exits nonzero if a requested remote update fails. Automation must fail or alert on that exit and inspect:

- stderr/stdout for the immediate error;
- `catalog/live_skill_agent_last.json` for `overall_status`, `refresh.remote_status`, and `refresh.failed_refreshes`;
- `memory.md` for the append-only human summary.

For long-running mode, process liveness is not sufficient because an individual iteration can report partial success and continue. Monitor the JSON file after every expected interval and alert unless `overall_status` is `success`. The command never advances pins or follows a moving branch.

Recovery sequence:

1. resolve authentication, network, dirty-worktree, or remote errors without discarding local work;
2. verify any intended upstream commit against the reviewed pin;
3. rerun the one-shot command;
4. rebuild and audit the catalog;
5. retain the failed report until the incident is understood.

Generated reports include local absolute paths and should not be published blindly.

## Troubleshooting

- `uv sync --frozen` fails: the checked-in lockfile and project metadata disagree, or the package source is unavailable. Do not bypass `--frozen` in production.
- client reports command not found: use an absolute `uv` path in the client config or fix the client's service environment.
- tool is absent: inspect client MCP logs, confirm both configured paths, and run the manual server check.
- Streamable HTTP returns `401`: supply the Bearer token configured by `--auth-token-env`; the token must be sent on all MCP requests.
- Streamable HTTP returns `403`: the request `Origin` is not approved; add only the exact trusted origin with `--allowed-origin`.
- Streamable HTTP returns `421`: the request `Host` is not approved; preserve the loopback Host or add the exact reverse-proxy host with `--allowed-host`.
- Streamable HTTP returns `413`: the request exceeds the 64 KiB transport limit; reduce `context` or client metadata instead of raising the service limit casually.
- `decision: no-fit`: this is a safe outcome, not a server failure. Add or promote a skill only through review.
- catalog seems stale: rebuild it explicitly; generated catalog files are not committed.
- core payload changed: review the complete change, update its hash in `catalog/reviewed_core.lock.json`, and rebuild the catalog. Do not rely on a previously generated catalog as current approval evidence.
- after that review, compute the exact value with `uv run --frozen python house-skills/core/skill-librarian/scripts/hash_core_skill.py --root "$PWD" --skill-path house-skills/core/<skill-name>`; the helper only prints the hash and does not approve or edit anything.

Report suspected security issues privately as described in [SECURITY.md](../SECURITY.md).
