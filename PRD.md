---
title: Shift Handover Briefing PRD
type: product-requirements
status: draft
updated: 2026-10-13
---

# Product Requirements: Shift Handover Briefing

## 1. Summary

Shift Handover Briefing collects machine events, maintenance notes, operator voice memos, and equipment manual passages for a selected machine and time window. It produces a concise, prioritized handover that tells the incoming shift what changed, what to check, why it is prioritized, and which sources support each statement.

The product is a decision-support prototype for the AMD Developer Hackathon Intelligent Industry track. The MVP demonstrates a complete workflow on a realistic, seeded dataset and runs the core language-model inference on AMD infrastructure.

## 2. Problem

Operational context is spread across structured machine logs, informal notes, spoken observations, and long manuals. The incoming shift spends time reconciling these sources, may miss a repeated or escalating issue, and often cannot quickly verify why a suggested check appears in the handover.

## 3. Target users

- **Primary:** Incoming shift supervisor or maintenance technician at a small manufacturing line.
- **Secondary:** Outgoing operator recording a handover; reliability/maintenance lead reviewing recurring issues.

### Jobs to be done

- As an outgoing operator, I need to capture an observation quickly, including by voice, so the next shift gets the context.
- As an incoming technician, I need a short prioritized list with timestamps and source evidence so I can decide what to inspect first.
- As a supervisor, I need to edit and acknowledge the handover so generated interpretation is not mistaken for an approved work order.

## 4. Goals and non-goals

### Goals

- Turn multiple input types into one time-bounded equipment handover.
- Keep every factual statement traceable to one or more source records or manual passages.
- Rank items using transparent, rule-based severity/recency/repetition signals; use the model to summarize and explain, not invent telemetry.
- Make uncertainty, missing data, and human-review needs visible.
- Demonstrate meaningful inference on AMD hardware/cloud.
- Show measurable reduction in handover preparation time on a repeatable sample scenario.

### Non-goals for MVP

- Direct machine control, PLC/SCADA integration, or automatic work-order execution.
- Autonomous diagnosis, maintenance authorization, or safety-critical decision-making.
- General-purpose predictive maintenance claims or validated failure prediction.
- Multi-tenant production security, enterprise SSO, or long-term data retention.
- Support for every industrial log format, language, or equipment vendor.

## 5. Core user flow

1. User chooses a demo equipment asset and shift window.
2. User uploads log data, notes, audio, and manuals (or loads a clearly labeled demo bundle).
3. App validates timestamps and source metadata; reports parse/transcription failures.
4. App extracts events, transcribes audio, and retrieves manual passages relevant to the events.
5. App creates a prioritized handover. Each item shows priority, what changed, recommended check, evidence, and uncertainty.
6. User opens evidence, edits wording/priority, acknowledges or assigns follow-up, and exports the approved draft.

## 6. Functional requirements

### P0: required for demo

- Upload CSV or JSON machine logs with timestamp, asset ID, signal/event, value, and optional unit.
- Upload text/Markdown maintenance notes and operator notes.
- Upload an audio memo and transcribe it, with transcript editable before inclusion.
- Upload/searchable PDF or text manuals and show page/section citations.
- Select asset and time window; show data coverage and ingestion errors.
- Generate a structured handover with:
  - observed change/event and timestamp(s)
  - priority and a short explanation
  - next check phrased as a suggestion, not an instruction to override SOP
  - source links/citations and quoted evidence snippets
  - confidence/uncertainty and human-review flag
- Allow user edit, acknowledge, defer, and export as Markdown.
- Clearly label demo/synthetic data and model-generated content.

### P1: desirable if time permits

- Compare current and previous shift summaries.
- Deduplicate related alerts and show event timeline.
- Export PDF and generate a shareable read-only handover view.
- Add a simple feedback control: useful / incorrect / missing context.

## 7. Prioritization approach

The MVP uses explainable deterministic ranking, not an LLM-only score. Candidate factors: configured severity, repeated occurrences, deviation from supplied baseline, recency, and explicit operator concern. Keep the factor values and reason visible. The score is a triage aid and must be calibrated to the demo dataset; it is not a validated risk score.

## 8. UX requirements

- The first screen makes the asset, shift window, data sources, and processing status obvious.
- A handover item can be understood without opening a chat.
- Evidence is one click away and citations identify the source file plus timestamp or manual page/section.
- Missing or contradictory inputs are surfaced rather than silently resolved.
- No red/green color alone conveys status; use labels and icons as well.
- Human review and operator edits remain visible in the exported result.

## 9. Success measures

Hackathon prototype targets (measure on the same seeded scenario):

- Prepare a draft handover in under 2 minutes after upload completes.
- At least 90% of factual claims in the generated handover have a valid source citation in the test set.
- At least 80% of seeded high-priority events appear in the top-ranked items (small, labeled evaluation set).
- Zero unsupported machine-control actions; all safety-sensitive recommendations are labeled for human review.
- Record baseline manual preparation time versus assisted preparation time with at least 3 reviewers if available.

These are prototype targets, not production guarantees.

## 10. Dependencies and constraints

- AMD Developer Cloud or another event-approved AMD environment with ROCm-compatible model serving.
- Event access to an AMD GPU and working model endpoint; verify quota and setup early.
- Open model and runtime selected based on actual event availability and license.
- Sample manuals/logs must be public, synthetic, or sanitized; do not upload confidential plant data.

## 11. Open questions

- What GPU instance, model-serving image, and network access does the event provide?
- Which speech-to-text approach is available and permitted in the cloud environment?
- Is the intended demo browser-local, deployed public web app, or both?
- Which priority rules best fit the selected synthetic machine scenario?
