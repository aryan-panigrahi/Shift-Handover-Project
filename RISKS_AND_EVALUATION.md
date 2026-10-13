---
title: Shift Handover Briefing Risks and Evaluation
type: risk-register
status: draft
updated: 2026-10-13
---

# Risks and Evaluation

## Product risks and mitigations

| Risk | Mitigation in MVP |
|---|---|
| Model invents a sensor fact or manual instruction | Supply only normalized event/evidence records; require citations; validate references; reject unsupported claims. |
| Priority score appears authoritative | Expose heuristic factors; label as triage; avoid “risk probability” language; let operator reorder. |
| Transcript errors change meaning | Show transcript and allow correction; label low-confidence segments; preserve audio source/time references. |
| Incorrect or stale manual passage | Cite exact page/section; show excerpt; identify manual/version; require human verification before action. |
| Missing or conflicting timestamps | Show source timezone/coverage and conflict warning; do not silently merge ambiguous events. |
| Unsafe operational advice | Phrase as checks for qualified staff under existing approved procedures; require human review; no control commands or autonomous action. |
| Cloud GPU or endpoint failure | Test early; health check; keep ingestion/timeline usable; backup demo recording with transparent disclosure. |
| Confidential operational data exposure | Synthetic or sanitized hackathon inputs; environment secrets; session deletion; no raw content in logs. |

## Small evaluation set

Create 8–12 expected handover items across a synthetic shift and label:

- source event(s) and exact timestamp/row/page
- expected urgency bucket and reason
- whether a manual citation is required
- whether human review is required
- acceptable summary/check wording

### Metrics

- **Citation validity:** fraction of factual claims whose source ID and locator exist and support the claim.
- **High-priority recall@3:** fraction of seeded high-priority events among the top three results.
- **Unsupported-claim rate:** factual claims without support divided by all factual claims.
- **Input coverage:** fraction of parseable source records represented in the timeline.
- **Draft time:** elapsed user time from complete upload to editable handover.
- **Perceived usefulness:** reviewer rating and correction count, reported with sample size.

Do not present a tiny synthetic evaluation as industrial validation. Describe it as a prototype benchmark.
