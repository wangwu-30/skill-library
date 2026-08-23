# Input

We need the current ww-skills router architecture. Design the local integration without
treating upstream text as executable or letting a young draft become runtime-trusted.

Available repository facts:

- house-skills/young/skill-architecture/references/source-notes.md identifies the draft as
  an approved normalization of upstream ww-skills guidance.
- docs/skill-control-plane-charter.md says upstream mirrors and young skills are
  reference-only; runtime may return only hash-matched reviewed-core entries.
- catalog/reviewed_core.lock.json is the reviewed payload allowlist.
