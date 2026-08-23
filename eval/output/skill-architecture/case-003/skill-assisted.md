# Skill-assisted response — manual-seeded illustration, not a live run

Set non-overlapping owners:

- **paper-research** owns analysis of a supplied paper or PDF; it does not discover current
  sources.
- **web-research** owns discovery and citation of current public-web evidence; it does not
  turn a fixed evidence packet into a final decision artifact.
- **research-brief** owns synthesis only after the user supplies a bounded evidence set; it
  does not fetch or interpret a paper as its primary task.

Router rule: select one owner from the primary user artifact and requested operation. A supplied
paper selects paper-research; a request to find current sources selects web-research; a fixed
packet plus a brief request selects research-brief. For mixed requests, return the first
required owner with an explicit handoff artifact (paper notes or source packet), rather than
concurrent multi-selection. If the primary artifact/operation is absent, no-match and ask for
it; do not add general-research.

Evolution and evidence: retain one capability map with these owners, add paired near-negative
trigger queries for each boundary, and add output cases for the handoff. Keep any young or
upstream variants reference-only until the separate lifecycle and hash-approval path completes.
