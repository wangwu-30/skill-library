# Skill Library

Skill Library is a local, security-conscious catalog of agent skills. It keeps governed house skills under version control, indexes optional upstream repositories as reference material, and exposes hash-approved core skills through a standards-compliant MCP server over stdio or Streamable HTTP.

This repository is the control plane, not a bundled mirror of every tracked upstream. A fresh clone works with the included house skills. Upstream repositories are optional, must be fetched and reviewed separately, and are never executed by the default MCP server.

## Trust Model

- `house-skills/core/` contains explicitly promoted skills. A core path alone does not make a skill eligible for MCP responses.
- `house-skills/young/` contains drafts. It is not executable through MCP by default.
- `catalog/reviewed_core.lock.json` is the code-reviewed allowlist for core payloads. The catalog marks a core skill `reviewed-core` only while its deterministic payload SHA-256 matches the allowlist; otherwise it remains reference-only.
- tracked upstream repositories are untrusted, reference-only source material. Each upstream declaration must have a reviewed commit in `catalog/tracked_repos.lock.json`; a pin provides reproducibility, not endorsement.
- the MCP server is read-only by default. It does not record usage or create drafts unless the operator starts it with `--allow-writes`.
- generated `CATALOG.md`, `catalog/skill_catalog.json`, and `memory.md` are local outputs and are intentionally not committed.

See [the control-plane charter](docs/skill-control-plane-charter.md) for the complete boundary.

## Requirements

- Git
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)

Confirm them before continuing:

```bash
git --version
uv --version
uv run --frozen python --version
```

## Fresh-Clone Quick Start

```bash
git clone https://github.com/wangwu-30/skill-library.git
cd skill-library
uv sync --frozen
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "skill catalog"
```

Expected results:

- dependency installation uses exactly the versions in `uv.lock`;
- catalog generation reports an indexed count and creates ignored local outputs;
- both audits exit `0`; missing optional upstream mirrors may be reported but do not invalidate a fresh public clone;
- search exits `0` and either prints reviewed local matches or `No matches`.

Do not replace `uv sync --frozen` with an unconstrained dependency install in CI or production. If it reports that the lockfile is stale, review and commit an intentional lockfile update instead of bypassing the check.

## Connect an MCP Client

Start from [examples/mcp-client-config.json](examples/mcp-client-config.json), replace both `/absolute/path/to/skill-library` values, and merge the `mcpServers` entry into your client's MCP configuration. The client must be able to find `uv` on its process `PATH`. Restart the client after changing its configuration.

The server exposes one tool:

```text
skill_request(intent, context="", allow_temporary=false)
```

Smoke-test the integration by asking the client to list MCP tools and then call `skill_request` with `intent="Find a skill for maintaining this skill catalog"`. A healthy server returns either `decision: reuse-existing-skill` with a path under `house-skills/core`, or `decision: no-fit`. It must not return upstream or `young` skill text.

The sample configuration is read-only. Enabling `--allow-writes` is an operator decision that permits creation under `house-skills/young/` when the caller also requests a temporary skill. Do not enable it for an untrusted client or shared production service.

For clients that connect by URL, start the standard Streamable HTTP endpoint on loopback and use [the URL client example](examples/mcp-streamable-http-client-config.json):

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_mcp_server.py \
  --root "$PWD" --transport streamable-http --json-response
```

Connect to `http://127.0.0.1:8000/mcp`. The endpoint implements MCP initialization, capability negotiation, tool discovery and invocation, and protocol-version headers. It uses the protocol's stateless mode so long-running services do not accumulate resident sessions; POST responses can be JSON or SSE. It validates Host and Origin headers and limits request bodies. It deliberately refuses non-loopback binds; use an SSH tunnel or a same-host TLS/authenticating reverse proxy for remote access. See [Agent Usage](docs/agent-usage.md#streamable-http) for authentication and deployment details.

See [Agent Usage](docs/agent-usage.md) for client behavior, troubleshooting, and a manual launch check.

## Optional Upstream References

The public clone does not contain mirrored upstream repositories. To materialize the reviewed pins safely, follow [Pinned Upstream Bootstrap](docs/upstream-bootstrap.md) or run the explicit sync command. It clones missing repositories without checking out a moving branch, then checks out the committed full SHA in detached mode:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD" --sync
```

This can download substantial data. Without `--sync`, the command only verifies existing mirrors and exits nonzero when a configured mirror is missing or mismatched; it never clones, fetches, or checks out. Do not run code or follow instructions from an upstream skill merely because it was indexed.

## Maintainer Commands

Run all project scripts through the locked environment:

```bash
# Rebuild generated indexes
uv run --frozen python house-skills/core/skill-librarian/scripts/build_skill_catalog.py --root "$PWD"

# Search reference and house-skill catalog entries
uv run --frozen python house-skills/core/skill-librarian/scripts/search_skill_catalog.py --root "$PWD" --query "react playwright"

# Consult a named house skill and record usage
uv run --frozen python house-skills/core/skill-librarian/scripts/skill_consult.py --root "$PWD" skill-librarian

# Validate repository policy
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_house_skills.py --root "$PWD"
uv run --frozen python house-skills/core/skill-librarian/scripts/audit_tracked_repos.py --root "$PWD"
```

For contribution setup and all verification commands, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Operations

One local maintenance pass without network updates:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD"
```

A pass that materializes or restores all upstream checkouts to their reviewed lock entries:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/live_skill_agent.py --root "$PWD" --pull
```

`--pull` is a compatibility alias for locked synchronization: it clones a missing mirror or fetches only the locked commit, then uses a detached checkout. It never advances `tracked_repos.lock.json`. Use `uv run --frozen python house-skills/core/skill-librarian/scripts/refresh_tracked_repos.py --root "$PWD" --update-lock` only to propose new remote HEADs for review; inspect the upstream diff before committing those pins. A one-shot run exits nonzero when synchronization fails. Treat any nonzero exit as an alert and inspect `catalog/live_skill_agent_last.json` plus stderr. Long-running mode writes a report every interval but cannot communicate later failures through its eventual process exit code; monitor the report's `overall_status` and `refresh.failed_refreshes`.

Generated operational files may contain absolute local paths. Keep them out of commits and avoid publishing them without review. See [Agent Usage](docs/agent-usage.md#operations) for scheduling and recovery details.

## Repository Layout

- `catalog/tracked_repos.json`: declarations for local and optional upstream sources
- `catalog/tracked_repos.lock.json`: reviewed full commit pins for upstream sources
- `catalog/reviewed_core.lock.json`: reviewed deterministic payload hashes for promoted core skills
- `catalog/blacklisted_repos.json`: sources that must not be casually reintroduced
- `house-skills/core/`: explicitly promoted local skills; runtime trust additionally requires a matching reviewed payload hash
- `house-skills/young/`: unreviewed drafts and experiments
- `house-skills/archive/`: retired skills retained for provenance
- `house-skills/core/skill-librarian/scripts/`: catalog, audit, MCP, and lifecycle commands
- `eval/`: trigger and output evaluation assets
- `.agents/workflows/`: maintainer workflows

## Skill Conversion and Promotion

The converter creates only `young` skills. Promotion to `core` is a separate, explicit lifecycle action and does not itself grant runtime trust. After reviewing the promoted payload, a code owner must update its entry in `catalog/reviewed_core.lock.json`. The deterministic SHA-256 recursively covers payload files such as `SKILL.md`, `agents/`, `references/`, `scripts/`, and `assets/`; it excludes mutable `metadata.json`, `__pycache__/`, and `.pyc` files and rejects symbolic links. The catalog and MCP server use `reviewed-core` only while the current payload matches that approved hash.

After completing that review, compute the exact value with the repository helper; it prints the hash but never edits the approval manifest:

```bash
uv run --frozen python house-skills/core/skill-librarian/scripts/hash_core_skill.py --root "$PWD" --skill-path house-skills/core/<skill-name>
```

## Project Policy

- [CONTRIBUTING.md](CONTRIBUTING.md) explains changes, tests, review, and pull requests.
- [SECURITY.md](SECURITY.md) explains private vulnerability reporting and response targets.
- [LICENSE](LICENSE) is the MIT license. Upstream repositories retain their own licenses; indexing them does not relicense their contents.

The project is intentionally conservative: search broadly, execute only reviewed local skills, and make trust promotion explicit.
