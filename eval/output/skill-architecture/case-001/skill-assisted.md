# Skill-assisted response — manual-seeded illustration, not a live run

Use three layers with one owner each:

1. **Catalog evidence** indexes ww-skills as an upstream/reference source. Its text may
   inform a local draft but cannot be selected for execution.
2. **Router policy** compares the request against owned capabilities and returns one
   reviewed-core candidate only when its trigger and trust status both fit. Resolve equal
   fits by the narrower declared capability; if still tied, return a conflict/no-match for
   human or consultation handling rather than selecting both.
3. **Runtime retrieval** independently enforces reviewed-core: resolved path under
   house-skills/core plus exact payload hash in catalog/reviewed_core.lock.json. It must
   reject upstream and house-skills/young/skill-architecture even if the router describes
   them as useful references.

Keep the current young draft as an evaluation subject, not a runtime fallback. Record router
selection/no-match observations separately from trigger expectations before considering a
lifecycle action.
