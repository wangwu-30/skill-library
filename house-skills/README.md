# House Skills

This directory holds the internally managed skill lifecycle.

## Layout

- `config/lifecycle.json`: shared lifecycle policy for young/core/archive
- `core/`: stable skills that should be preferred in recommendations
- `young/`: newly generated skills with metadata, TTL, and promotion checks
- `archive/`: expired or replaced skills retained for provenance

## Lifecycle

1. New converted skills start in `young/`.
2. Telemetry should be collected in the managing agent layer, not embedded in skill content.
3. Every house skill should carry `schema_version`, semver `version`, current `owner`, and `usage_tracking.mode` in `metadata.json`.
4. `usage_tracking.mode=none` means the library does not yet have trustworthy usage evidence; do not overread `use_count=0`.
5. Keep lineage in metadata: `derives_from`, `replaces`, and `compatibility`.
6. For non-trivial version changes, use `scripts/bump_house_skill_version.py` and prefer `--snapshot-current` before breaking changes.
7. GC can propose promotion to `core/` or archival to `archive/`.
8. Search prefers `core`, then `young`, then upstream mirrors.
9. Thresholds and safety defaults come from `config/lifecycle.json`.
