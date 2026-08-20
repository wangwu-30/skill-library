# Delivery Goal

The project is a production-oriented skill control plane with one conservative runtime boundary.

## Required Outcomes

1. A fresh clone installs reproducibly with Python 3.11+ and `uv sync --frozen`.
2. Local house skills can be cataloged and audited without downloading upstream repositories.
3. The default MCP server returns only explicitly promoted `core` skills whose deterministic payload SHA-256 matches `catalog/reviewed_core.lock.json`, and performs no caller-triggered writes.
4. Upstream repositories and `young` drafts remain reference-only. Conversion only creates `young`; explicit promotion plus code-reviewed payload-hash approval is required for `reviewed-core` status.
5. Scheduled maintenance produces machine-readable status and makes one-shot refresh failures observable through a nonzero exit.
6. Lifecycle changes preserve provenance and require review rather than relying on usage counts alone.

## System Boundary

```text
host agent
  sends a bounded task intent
        |
        v
read-only MCP server (default)
  selects hash-approved house-skills/core content only
        |
        v
generated local catalog
  includes reviewed core plus reference-only young/upstream metadata
```

Upstream source trees are optional, ignored local inputs. Indexing is not execution, endorsement, or relicensing. See [the charter](skill-control-plane-charter.md) and [bootstrap policy](upstream-bootstrap.md).

## Operational Definition of Done

- setup and smoke commands work from a clean clone using the lockfile;
- MCP results cannot escape `house-skills/core/` in default mode;
- audit and test commands pass;
- generated files remain local and are treated as potentially sensitive operational output;
- automation checks process exit status and report fields;
- documentation distinguishes implemented behavior from roadmap ideas.

Possible future features, including hosted transport or richer ranking, are not current operating promises.
