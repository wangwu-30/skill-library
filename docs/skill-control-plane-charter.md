# Skill Control Plane Charter

## Purpose

Skill Library helps maintainers discover reusable agent workflows without treating arbitrary downloaded instructions as trusted code. The repository owns source declarations, local house skills, structural policy, evaluation assets, and deterministic maintenance scripts.

## Trust Zones

| Zone | Purpose | Default execution status | Promotion path |
| --- | --- | --- | --- |
| `house-skills/core/` | explicitly promoted local skills | eligible only with an approved matching payload hash | review changes and update the reviewed-core manifest |
| `house-skills/young/` | drafts and experiments | reference-only | evaluate, audit, explicitly promote, then approve the payload hash |
| upstream mirrors | comparison and research | reference-only | adapt the minimum needed content into a reviewed house skill |
| `house-skills/archive/` | retained provenance | never selected | explicit restoration and review |

Repository URLs and catalog entries are metadata, not trust decisions. Text in upstream skills can contain prompt injection, unsafe commands, data-exfiltration requests, or incompatible license terms. Agents and maintainers must inspect it as untrusted input.

## Runtime Contract

The production MCP server supports local stdio and the standard Streamable HTTP transport; stdio remains the default. Both transports are read-only by default. They may return only catalog entries marked `reviewed-core`, whose resolved path is under `house-skills/core/` and whose deterministic payload SHA-256 matches `catalog/reviewed_core.lock.json`. The hash recursively covers payload files such as `SKILL.md`, `agents/`, `references/`, `scripts/`, and `assets/`, excludes mutable `metadata.json`, `__pycache__/`, and `.pyc` files, and rejects symbolic links. A no-match response is preferable to returning unreviewed instructions.

Streamable HTTP binds only to loopback, validates Host and Origin headers against explicit allowlists, rejects oversized request bodies, and does not trust proxy headers. Remote exposure requires an SSH tunnel or a same-host TLS/authenticating reverse proxy. The optional environment-sourced pre-shared Bearer token is a controlled-environment gate, not OAuth; federated or multi-tenant deployment requires a standards-based authorization service or authentication proxy.

`--allow-writes` is an explicit operator override for trusted maintenance sessions. It permits draft creation and usage recording; it does not confer review status on a draft.

## Upstream Policy

- clone only repositories required for a concrete task;
- verify repository URL and a reviewed full commit SHA before indexing;
- do not execute upstream setup scripts or install upstream dependencies during review;
- retain reviewed full SHAs in `catalog/tracked_repos.lock.json`;
- repeat review when advancing a revision;
- preserve attribution and comply with each upstream license.

The exact procedure is in [Pinned Upstream Bootstrap](upstream-bootstrap.md).

## Lifecycle and Evidence

A skill enters `young`, gathers trigger/output evidence, passes structural and content review, and may be promoted explicitly. Converters create only `young` skills and cannot bypass that decision. Usage counts alone are insufficient. Promotion must establish a narrow trigger, executable workflow, bounded permissions, validation steps, ownership, provenance, and acceptable licensing.

Promotion and runtime approval are distinct. After promotion, a code owner reviews the complete payload and updates its deterministic SHA-256 in `catalog/reviewed_core.lock.json`. Until that manifest entry exists and exactly matches, the catalog and MCP server keep the skill reference-only. Any later payload change invalidates the match and requires renewed review and a deliberate manifest update.

Archival is preferred over destroying provenance. Automated maintenance may recommend lifecycle actions but must not silently promote unreviewed content into the MCP trust boundary.

## Operations

Generated catalog and run reports are replaceable local artifacts. Maintainers monitor both command exit status and the JSON report. Remote update failure is an operational failure even when local catalog generation succeeds. Credentials must not be stored in tracked repository declarations, generated reports, skill bodies, or examples.

## Governance

Changes to the trust model, MCP write defaults, promotion criteria, tracked source policy, or security controls require code-owner review. Vulnerabilities follow [SECURITY.md](../SECURITY.md); ordinary changes follow [CONTRIBUTING.md](../CONTRIBUTING.md).
