---
title: Shift Handover Briefing Data Model and API
type: technical-specification
status: draft
updated: 2026-10-13
---

# Data Model and API

## Canonical entities

### Asset

```json
{
  "asset_id": "press-07",
  "display_name": "Hydraulic Press 07",
  "timezone": "Europe/Rome",
  "signals": ["motor_temperature", "vibration_rms", "pressure"]
}
```

### SourceDocument

```json
{
  "source_id": "src-123",
  "asset_id": "press-07",
  "kind": "machine_log|maintenance_note|operator_audio|manual",
  "filename": "shift-b-log.csv",
  "content_hash": "sha256:...",
  "captured_at": "2026-10-13T08:30:00+02:00",
  "metadata": {"shift": "B"}
}
```

### Event

```json
{
  "event_id": "evt-123",
  "asset_id": "press-07",
  "occurred_at": "2026-10-13T08:22:10+02:00",
  "event_type": "threshold_exceeded|alarm|maintenance|operator_observation|unknown",
  "summary": "Motor temperature reached 91 °C",
  "signals": [{"name": "motor_temperature", "value": 91, "unit": "°C"}],
  "source_refs": [{"source_id": "src-123", "locator": "row:18"}],
  "confidence": 1.0
}
```

### HandoverItem

```json
{
  "item_id": "item-123",
  "priority": "high|medium|low",
  "priority_score": 0.82,
  "priority_factors": ["repeated 3 times", "recent", "operator flagged"],
  "what_changed": "...",
  "suggested_check": "Verify the cooling path and compare the reading with the approved operating procedure.",
  "evidence_refs": [{"event_id": "evt-123"}, {"source_id": "manual-1", "locator": "page:42"}],
  "uncertainty": "The log has no baseline reading for this shift.",
  "human_review_required": true,
  "status": "draft|acknowledged|deferred|assigned",
  "edited_by_user": false
}
```

## API sketch

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | App health and AMD model endpoint availability (no secrets returned). |
| `GET` | `/api/assets` | List demo assets. |
| `POST` | `/api/sources` | Upload source file with asset and shift metadata. |
| `GET` | `/api/jobs/{job_id}` | Ingestion/transcription status and errors. |
| `POST` | `/api/handovers` | Generate a handover for asset/time window. |
| `GET` | `/api/handovers/{handover_id}` | Read generated handover and linked evidence. |
| `PATCH` | `/api/handovers/{handover_id}/items/{item_id}` | Save edit/status/assignment. |
| `GET` | `/api/handovers/{handover_id}/export.md` | Export Markdown handover. |
| `DELETE` | `/api/demo-session` | Clear uploaded demo data and derived records. |

## Handover generation input

```json
{
  "asset_id": "press-07",
  "window_start": "2026-10-13T06:00:00+02:00",
  "window_end": "2026-10-13T14:00:00+02:00",
  "previous_window_start": "2026-10-12T22:00:00+02:00",
  "previous_window_end": "2026-10-13T06:00:00+02:00"
}
```

## Output contract

Return `handover_id`, asset and time range, input coverage summary, ranked items, unresolved questions, and generation metadata (model ID, AMD endpoint status, duration). Every item must have evidence references. If there is no evidence, use an explicit “unverified observation” category and require human review. The API should reject or clearly mark malformed model output rather than silently accepting it.
