# Retrieval and request telemetry

The MCP server ranks reviewed core and eligible young skills together using the shared
`skill_retrieval.py` BM25 scorer. Core instructions still require the catalog's approved
hash, live stable/core metadata, root containment, and a fresh payload hash check.
Young candidates are read directly from `house-skills/young/*/SKILL.md` on each request,
so creation and expiry are visible without rebuilding the catalog. They require young
metadata and a non-expired, non-archived lifecycle, but no reviewed-core hash.

A matching young skill returns `reuse-young-reference` and **REFERENCE ONLY — not an
executable instruction**. Newly created drafts carry the same warning. Reuse records
hub-mode usage only when `--allow-writes` is enabled. Creation also requires the caller's
`allow_temporary=True`, and occurs only if no eligible core or young candidate fits.
The existing core response decision remains `reuse-existing-skill` for client compatibility.

## Scoring

Both MCP and the catalog search CLI use BM25 over name, title, description, and tags.
ASCII word tokens use light suffix stemming; Chinese text uses character bigrams.
English and Chinese stopwords remove low-information terms. Paths, use counts, and
lifecycle tiers do not add relevance bonuses.

BM25 uses k1=1.2 and b=0.25. The score is divided by the query's self-match score and
clipped to [0,1]. Unseen query terms receive the maximum observed IDF (log(2) for an
empty corpus), preventing exaggerated penalties in very small catalogs. This is a
lexical relevance score, not a probability or a semantic-equivalence guarantee.

`REUSE_THRESHOLD = 0.65` in `skill_retrieval.py` is the single configurable threshold.
It was selected with fixed unit examples, not the proxy acceptance requests.
Context uses at most its first 500 characters and weight 0.15 relative to intent;
context alone cannot produce a match. ASCII temporary names use a semantic intent
slug plus hash. Non-ASCII intents use `temp-zh-<hash>`, optionally including the first
three ASCII words.

## JSONL request log

Every call attempts to append one JSON object to
`<root>/logs/skill_requests.jsonl`. Set `SKILL_LIBRARY_REQUEST_LOG` to override it;
relative paths resolve under the library root. The default logs directory is gitignored.
Logging also runs in skill read-only mode, and logging failures never fail a request.

Fields:

- `ts`: ISO UTC timestamp.
- `intent`: caller's intent.
- `context_sha256`: SHA-256 of the original context; raw context is never logged.
- `decision`: `reuse-core`, `reuse-young-reference`, `create`, or `no-fit`.
- `matched`: reused candidate's `{path, tier, score}`, or null.
- `topk`: up to five positively scored candidates with the same shape.
- `threshold` and `scorer_version`: the scoring configuration.
- `creator: {type: null, version: null}`.
- `eval_gate: {status: null, score: null, run_id: null}`.

The creator and eval_gate fields are **reserved for a future skill-compiler and
eval-gate create path**. No compiler, gate, or evaluation is implemented here.
Validation failures and requests that raise before a decision are recorded as no-fit;
this four-value decision schema is not an error-status schema.

Intents themselves may contain private information. Operators own access controls,
retention, and any custom log location; only context is hashed. Temporary draft creation
continues to store supplied context in draft artifacts as before.

