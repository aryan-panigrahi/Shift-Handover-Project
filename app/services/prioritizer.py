"""
Prioritization Service: Explainable, transparent heuristic ranking engine.
Calculates priority scores and generates factor breakdowns based on severity,
repetition, baseline deviation, recency, and operator concern.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from app.models.schemas import Event


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        # Replace Z with +00:00
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def cluster_and_prioritize_events(
    events: List[Event],
    window_start: str,
    window_end: str
) -> List[Dict[str, Any]]:
    """
    Groups events by related operational topic (e.g., motor thermal issue, vibration surge,
    routine maintenance, operator notes), computes transparent scores and factors, and ranks them.
    """
    if not events:
        return []

    w_start_dt = parse_timestamp(window_start)
    w_end_dt = parse_timestamp(window_end)
    window_total_seconds = (w_end_dt - w_start_dt).total_seconds() if (w_start_dt and w_end_dt) else 28800.0
    if window_total_seconds <= 0:
        window_total_seconds = 28800.0

    # Cluster events into conceptual groups
    clusters: Dict[str, Dict[str, Any]] = {}

    for evt in events:
        cluster_key = "general"
        sig_name = evt.priority_signals.get("signal_name", "")
        summary_lower = evt.summary.lower()

        if "motor_temp" in sig_name or "temp" in summary_lower or "heat" in summary_lower:
            cluster_key = "motor_temperature"
        elif "vibration" in sig_name or "vibration" in summary_lower:
            cluster_key = "vibration_rms"
        elif "pressure" in sig_name or "pressure" in summary_lower:
            cluster_key = "hydraulic_pressure"
        elif evt.event_type == "maintenance" or "filter" in summary_lower or "oil" in summary_lower:
            cluster_key = "filter_maintenance"
        elif evt.event_type == "operator_observation":
            if "whine" in summary_lower or "hot" in summary_lower or "cooling" in summary_lower:
                cluster_key = "motor_temperature"  # correlates with thermal issue!
            else:
                cluster_key = f"operator_obs_{evt.event_id}"
        else:
            cluster_key = f"evt_{evt.event_type}_{evt.event_id}"

        if cluster_key not in clusters:
            clusters[cluster_key] = {
                "key": cluster_key,
                "events": [],
                "max_severity": "info",
                "max_deviation": 0.0,
                "latest_event_dt": None,
                "operator_flagged": False,
                "abnormal_count": 0
            }

        c = clusters[cluster_key]
        c["events"].append(evt)

        # Update severity
        sev = evt.priority_signals.get("severity_level", "info")
        if sev == "critical":
            c["max_severity"] = "critical"
        elif sev == "warning" and c["max_severity"] != "critical":
            c["max_severity"] = "warning"

        dev = evt.priority_signals.get("deviation", 0.0)
        if dev > c["max_deviation"]:
            c["max_deviation"] = dev

        if evt.priority_signals.get("operator_concern"):
            c["operator_flagged"] = True

        if evt.priority_signals.get("is_abnormal"):
            c["abnormal_count"] += 1

        evt_dt = parse_timestamp(evt.occurred_at)
        if evt_dt:
            if c["latest_event_dt"] is None or evt_dt > c["latest_event_dt"]:
                c["latest_event_dt"] = evt_dt

    # Now score each cluster
    ranked_clusters = []

    for key, c in clusters.items():
        score = 0.0
        factors = []

        # 1. Severity weight (0.35)
        if c["max_severity"] == "critical":
            score += 0.35
            factors.append("Critical trip threshold breached")
        elif c["max_severity"] == "warning":
            score += 0.20
            factors.append("Elevated beyond nominal operating envelope")
        else:
            score += 0.05

        # 2. Repetition weight (0.25)
        count = len(c["events"])
        if count >= 3:
            score += 0.25
            factors.append(f"Repeated {count} times across shift")
        elif count == 2:
            score += 0.15
            factors.append("Repeated 2 times in shift")
        else:
            score += 0.05
            factors.append("Single event occurrence")

        # 3. Deviation weight (0.20)
        dev = c["max_deviation"]
        if dev >= 5.0:
            score += 0.20
            factors.append(f"Significant deviation (+{dev:.1f} beyond limit)")
        elif dev > 0.0:
            score += 0.12
            factors.append(f"Moderate deviation (+{dev:.1f} beyond limit)")
        else:
            score += 0.05

        # 4. Recency weight (0.10)
        if c["latest_event_dt"] and w_end_dt:
            time_to_end = (w_end_dt - c["latest_event_dt"]).total_seconds()
            recency_ratio = max(0.0, min(1.0, 1.0 - (time_to_end / window_total_seconds)))
            recency_contrib = recency_ratio * 0.10
            score += recency_contrib
            if recency_ratio > 0.75:
                factors.append("Recent event (within final quarter of shift)")
            elif recency_ratio > 0.40:
                factors.append("Mid-shift event")
            else:
                factors.append("Early-shift event")
        else:
            score += 0.05

        # 5. Operator concern weight (0.10)
        if c["operator_flagged"]:
            score += 0.10
            factors.append("Corroborated by outgoing operator memo")

        # Categorize
        score = round(min(score, 1.0), 2)
        if score >= 0.70:
            priority = "high"
        elif score >= 0.40:
            priority = "medium"
        else:
            priority = "low"

        ranked_clusters.append({
            "cluster_key": key,
            "priority": priority,
            "priority_score": score,
            "priority_factors": factors,
            "events": c["events"]
        })

    # Sort descending by priority_score
    ranked_clusters.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked_clusters
