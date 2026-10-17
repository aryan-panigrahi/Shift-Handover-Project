"""
Event Normalizer: Transforms raw logs, notes, and speech transcripts into canonical Events.
Applies asset baselines and extracts priority signals with provenance.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.schemas import Event, SignalReading, SourceRef, Asset


DEFAULT_BASELINES = {
    "motor_temperature": {"normal_max": 80.0, "trip_max": 85.0, "unit": "°C"},
    "vibration_rms": {"normal_max": 3.2, "trip_max": 4.5, "unit": "mm/s"},
    "pressure": {"normal_min": 190.0, "normal_max": 230.0, "trip_min": 170.0, "unit": "bar"},
    "hydraulic_pressure": {"normal_min": 190.0, "normal_max": 230.0, "trip_min": 170.0, "unit": "bar"}
}


def normalize_log_rows(rows: List[Dict[str, Any]], asset: Optional[Asset] = None) -> List[Event]:
    """Converts machine log rows into canonical Events."""
    events = []
    baselines = (asset.baseline_metrics if asset and asset.baseline_metrics else DEFAULT_BASELINES)

    for r in rows:
        sig = r.get("signal", "").lower().replace(" ", "_")
        val = r.get("numeric_value")
        raw_val = r.get("raw_value", "")
        unit = r.get("unit")
        timestamp = r.get("timestamp")
        source_id = r.get("source_id")
        locator = r.get("locator", f"row:{r.get('row_number', '?')}")
        asset_id = r.get("asset_id") or (asset.asset_id if asset else "press-07")

        event_type = "unknown"
        severity_level = "info"
        deviation = 0.0
        summary = f"{r.get('signal')} recorded at {raw_val} {unit or ''}".strip()

        # Check against baseline limits
        baseline = baselines.get(sig)
        if baseline and val is not None:
            unit = unit or baseline.get("unit")
            if "trip_max" in baseline and val >= baseline["trip_max"]:
                event_type = "threshold_exceeded"
                severity_level = "critical"
                deviation = round(val - baseline["trip_max"], 2)
                summary = f"{r.get('signal')} exceeded trip threshold: {val} {unit} (limit {baseline['trip_max']} {unit}, +{deviation} {unit})"
            elif "normal_max" in baseline and val > baseline["normal_max"]:
                event_type = "threshold_exceeded"
                severity_level = "warning"
                deviation = round(val - baseline["normal_max"], 2)
                summary = f"{r.get('signal')} elevated above nominal: {val} {unit} (nominal {baseline['normal_max']} {unit})"
            elif "trip_min" in baseline and val <= baseline["trip_min"]:
                event_type = "threshold_exceeded"
                severity_level = "critical"
                deviation = round(baseline["trip_min"] - val, 2)
                summary = f"{r.get('signal')} dropped below trip limit: {val} {unit} (min {baseline['trip_min']} {unit}, -{deviation} {unit})"
            elif "normal_min" in baseline and val < baseline["normal_min"]:
                event_type = "threshold_exceeded"
                severity_level = "warning"
                deviation = round(baseline["normal_min"] - val, 2)
                summary = f"{r.get('signal')} below nominal range: {val} {unit} (normal {baseline['normal_min']} {unit})"
            else:
                summary = f"{r.get('signal')} reading: {val} {unit}"

        # If signal name or value explicitly indicates an alarm
        if "alarm" in sig or "alarm" in raw_val.lower() or "trip" in raw_val.lower():
            event_type = "alarm"
            severity_level = "critical"
            summary = f"Alarm triggered: {r.get('signal')} = {raw_val}"

        evt_id = f"evt-log-{r.get('row_number', len(events)+1)}"
        events.append(Event(
            event_id=evt_id,
            asset_id=asset_id,
            occurred_at=timestamp,
            event_type=event_type,
            summary=summary,
            signals=[SignalReading(name=r.get("signal"), value=val if val is not None else 0.0, unit=unit)],
            source_refs=[SourceRef(
                source_id=source_id,
                locator=locator,
                snippet=f"{timestamp} | {r.get('signal')} = {raw_val} {unit or ''}".strip()
            )],
            confidence=1.0,
            priority_signals={
                "severity_level": severity_level,
                "deviation": deviation,
                "signal_name": sig,
                "numeric_value": val,
                "is_abnormal": severity_level in ("critical", "warning")
            }
        ))

    return events


def normalize_maintenance_blocks(blocks: List[Dict[str, Any]], asset_id: str = "press-07") -> List[Event]:
    """Converts maintenance note sections into canonical maintenance events."""
    events = []
    for idx, b in enumerate(blocks, start=1):
        text = b.get("text", "")
        locator = b.get("locator", f"block:{idx}")
        source_id = b.get("source_id", "maint-doc")

        # Try extracting timestamp from note header (e.g., "04:30" or "2026-10-13T04:30:00")
        import re
        time_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(:\d{2})?|\d{1,2}:\d{2})", text)
        occurred_at = time_match.group(1) if time_match else "2026-10-13T04:30:00+02:00"
        if len(occurred_at) <= 5:  # "04:30"
            occurred_at = f"2026-10-13T{occurred_at}:00+02:00"

        is_maintenance = any(k in text.lower() for k in ["replace", "filter", "oil", "service", "pm", "repair", "seal", "torque"])
        event_type = "maintenance" if is_maintenance else "operator_observation"

        events.append(Event(
            event_id=f"evt-maint-{idx}",
            asset_id=asset_id,
            occurred_at=occurred_at,
            event_type=event_type,
            summary=text.split("\n")[0][:120],
            signals=[],
            source_refs=[SourceRef(
                source_id=source_id,
                locator=locator,
                snippet=text[:160]
            )],
            confidence=1.0,
            priority_signals={
                "severity_level": "info" if not any(w in text.lower() for w in ["leak", "crack", "urgent", "failed"]) else "warning",
                "is_maintenance_action": True,
                "is_abnormal": False
            }
        ))
    return events


def normalize_transcript_segments(transcript_data: Dict[str, Any], source_id: str, asset_id: str = "press-07") -> List[Event]:
    """Converts audio transcript segments into operator observation events."""
    events = []
    segments = transcript_data.get("segments", [])
    # The database keeps a numeric field; zero means no measured confidence was
    # supplied, which is the case for the canned synthetic demo transcript.
    confidence = transcript_data.get("confidence") or 0.0

    # If no segments, treat entire text as one event
    if not segments and transcript_data.get("text"):
        segments = [{"start": 0.0, "end": 10.0, "text": transcript_data["text"]}]

    for idx, seg in enumerate(segments, start=1):
        text = seg.get("text", "")
        # Look for explicit times mentioned in speech (e.g., "around 10:30", "at 13:20")
        import re
        time_match = re.search(r"(\d{1,2}:\d{2})", text)
        if time_match:
            occurred_at = f"2026-10-13T{time_match.group(1)}:00+02:00"
        else:
            occurred_at = "2026-10-13T13:20:00+02:00"

        is_concern = any(k in text.lower() for k in ["hot", "whine", "noise", "vibration", "leak", "high-pitch", "smell", "unusual"])
        severity = "warning" if is_concern else "info"

        events.append(Event(
            event_id=f"evt-audio-{idx}",
            asset_id=asset_id,
            occurred_at=occurred_at,
            event_type="operator_observation",
            summary=f"Operator Observation: {text[:110]}...",
            signals=[],
            source_refs=[SourceRef(
                source_id=source_id,
                locator=f"offset:{int(seg.get('start', 0))}s-{int(seg.get('end', 0))}s",
                snippet=text
            )],
            confidence=confidence,
            priority_signals={
                "severity_level": severity,
                "operator_concern": is_concern,
                "is_abnormal": is_concern
            }
        ))
    return events
