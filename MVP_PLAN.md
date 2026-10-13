---
title: Shift Handover Briefing MVP Plan
type: project-plan
status: draft
updated: 2026-10-13
---

# MVP Plan

## Build order

### Phase 0 — Lock the demo scenario

- [ ] Choose one machine and one realistic shift window.
- [ ] Create synthetic logs, operator notes/audio, maintenance note, and a short manual excerpt with known evidence.
- [ ] Define 8–12 expected events and the correct priority ordering with a domain reviewer if available.
- [ ] Confirm AMD Developer Cloud access, GPU/runtime, model endpoint path, quotas, and network reachability.

**Exit:** repeatable demo bundle and confirmed AMD inference path.

### Phase 1 — Ingestion and evidence

- [ ] Parse CSV/JSON logs into normalized events.
- [ ] Ingest notes and PDF/text manual with page/section metadata.
- [ ] Add audio upload and transcription adapter; provide manual transcript fallback.
- [ ] Build event timeline and source viewer.

**Exit:** all seeded sources appear with accurate timestamps and locators.

### Phase 2 — Prioritization and handover

- [ ] Implement transparent priority heuristic and expose its factors.
- [ ] Retrieve relevant manual passages for each event cluster.
- [ ] Connect structured LLM synthesis to AMD-hosted endpoint.
- [ ] Validate output schema and require evidence references.
- [ ] Add deterministic fallback when model output is invalid/unavailable.

**Exit:** ranked handover is grounded in the seeded sources and does not invent facts in the evaluation set.

### Phase 3 — Operator review and polish

- [ ] Add edit, acknowledge, defer, and human-review states.
- [ ] Add Markdown export.
- [ ] Add health/status view with model ID, inference duration, and AMD connectivity.
- [ ] Add demo reset and remove-session-data action.
- [ ] Prepare 3-minute demo and a backup recording.

**Exit:** a new user can complete the core workflow without developer intervention.

## Definition of done for the hackathon MVP

- Working browser-accessible prototype or documented local demo.
- Complete flow from source upload to evidence-linked draft to user edit/export.
- AMD-hosted model performs live core synthesis during the normal demo path.
- Synthetic dataset and expected-answer/evidence checklist included.
- README has setup instructions, `.env.example`, architecture, limitations, and no credentials.
- Public repository and containerization completed if required by the final submission rules.

## Cut line

If schedule is tight, prioritize CSV logs + notes + manual PDF, evidence-linked synthesis, and live AMD inference. Treat audio transcription as a short manual transcript entry if the chosen transcription runtime is not reliable. Do not cut source citations, uncertainty labels, or the human-review boundary.
