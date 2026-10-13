---
title: Shift Handover Briefing Technical Design
type: architecture
status: draft
updated: 2026-10-13
---

# Technical Design

## 1. Design principles

- **Evidence before fluency:** the model may summarize evidence but must not create sensor facts.
- **Traceability:** every event and recommendation links to its source; manual guidance includes page/section.
- **Human-owned decisions:** the app drafts and organizes; operators approve and act under existing procedures.
- **Hackathon-sized:** one asset, one shift window, a handful of input formats, seeded demo data.
- **AMD is in the live path:** core extraction/synthesis inference runs on AMD Developer Cloud or event-approved AMD hardware via ROCm.

## 2. Proposed architecture

```text
Browser UI
   │ HTTPS / JSON / file upload
   ▼
FastAPI application ─────────────── SQLite (demo metadata, jobs, edits)
   │
   ├── ingestion: CSV/JSON, TXT/MD, PDF
   ├── audio transcription adapter (swappable)
   ├── event normalization + deterministic priority rules
   ├── manual chunking/retrieval with source/page metadata
   └── handover orchestration
          │ OpenAI-compatible or provider adapter (confirm endpoint)
          ▼
     Open model served on AMD GPU / ROCm
```

Suggested implementation choices are Python + FastAPI for the API and ingestion, and React/Next.js or a compact Streamlit UI for the demo. Prefer the team’s fastest familiar UI. Keep the model client behind an adapter because endpoint details and model availability must be confirmed at kickoff. For the MVP, SQLite is sufficient; it is not a production multi-user database.

## 3. Processing pipeline

1. **Ingest:** accept files, record filename/type/hash, asset, shift window, and upload time.
2. **Parse:** validate schema, normalize timestamps to UTC internally, preserve original timezone if supplied, and retain raw source references.
3. **Transcribe:** send audio to the selected transcription service/model; retain transcript with time offsets if returned; require user confirmation/edit before using low-confidence text.
4. **Normalize events:** convert log rows, notes, and transcript segments into a common event representation while preserving provenance.
5. **Retrieve evidence:** split manual text by page/section; retrieve lexical/embedding matches for event terms; return passages with stable source IDs. For MVP, use a local vector index or SQLite FTS and avoid introducing a separate service unless needed.
6. **Prioritize:** calculate a transparent heuristic from configured severity, repetition, deviation, and recency. Record the contributing signals.
7. **Synthesize:** ask the AMD-hosted model for JSON matching a strict schema, using only provided events/passages. Require citation IDs on claims. Validate output; retry once or fall back to a templated summary on invalid JSON or missing citations.
8. **Review/export:** render evidence-linked draft; user edits and acknowledges; export Markdown.

## 4. AMD workload

The live demo should show the handover synthesis request going to an open model hosted on AMD GPU infrastructure with ROCm. If feasible, run embeddings or transcription on the same AMD instance too, but the requirement is met by a meaningful core workload only if the production demo path actually depends on AMD inference. Do not rely solely on a slide, precomputed response, or a local non-AMD model. Capture endpoint/model/runtime metadata in the project README and demo notes after the environment is confirmed.

## 5. Reliability and fallback

- File parsing failure: show the file and row/page error; continue with valid inputs.
- Transcription unavailable: allow manual transcript entry and label audio as not processed.
- AMD endpoint unavailable: keep the app usable for ingestion and timeline review; clearly mark synthesis unavailable. For judging, prepare a screen recording as backup, but disclose if the live endpoint is down.
- Invalid model response: strict schema validation, one repair attempt, then deterministic template output from known records.
- Missing citations: reject the affected claim or render as unverified for human review.

## 6. Security and privacy

- Use synthetic/public/sanitized data for the hackathon.
- Store uploaded files only for the active demo session; provide delete/reset.
- Never commit API keys or endpoint credentials; load secrets from environment variables.
- Avoid logging raw audio, notes, or document contents in application logs.
- Validate file type and size; sanitize filenames; restrict PDF/text parsing resources.

## 7. Deployment shape

- Frontend and API can run in one container for simplest demo; model server remains on AMD infrastructure.
- Configure the AMD model URL/key through environment variables.
- Provide a Dockerfile and `.env.example` with placeholders only.
- README must describe local app startup, AMD endpoint configuration, demo dataset loading, and troubleshooting.
- Pin dependencies after a successful run in the chosen environment.

## 8. Observability for demo

Show upload/parse status, inference duration, model identifier, and source citations. Keep a request ID for each synthesis. Avoid exposing secrets. A small “AMD inference: connected” indicator should be backed by a health check, not a static badge.
