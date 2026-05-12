# Tracked Repository Policy

This policy defines what it means to maintain upstream sources in the local skill library.

## Maintained Unit

The maintained unit is the tracked repository list in `catalog/tracked_repos.json`, plus the generated catalog views derived from it.

The mirrored upstream repositories are source pools for indexing and selective inspection. They are not all treated as actively maintained codebases.

Removed repositories should be recorded in `catalog/blacklisted_repos.json` so low-signal sources are not casually reintroduced later.

## Add A Repository When

- it contributes a meaningful number of real `SKILL.md` files or a high-value reference spec
- it adds distinct task coverage not already well represented in the local library
- it is official, high-signal, or repeatedly useful for local conversion/search
- its local directory, repo URL, kind, priority, tags, and notes can be stated clearly

## Do Not Add A Repository When

- it is mostly duplicates, placeholders, or thin wrappers around better sources
- it adds little beyond repositories already tracked
- it is too noisy to index and has no clear conversion value
- the only reason to add it is "more skills"

## Review Rules

- prefer official and high-signal sources over novelty
- treat large aggregators as candidate pools, not import targets
- keep notes short and decision-oriented
- update the tracked list before rebuilding policy around a repository
- inspect a specific upstream repository deeply only when the current task requires triage, conversion, or verification

## Removal Or Downgrade Signals

- repository disappeared or is no longer accessible
- repository became low-signal, abandoned, or dominated by duplicates
- a better maintained source now covers the same ground
- the local mirror no longer helps search, triage, or conversion work

When a repository is removed for one of these reasons, add it to the blacklist with a concrete reason and date.
