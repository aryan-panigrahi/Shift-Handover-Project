"""
Automated test suite for Shift Handover Briefing.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, upsert_asset
from app.services.seed_data import PRESS_07_ASSET, create_seeded_bundle_files
from app.services.parser import parse_csv_machine_log, parse_maintenance_notes, parse_manual_markdown
from app.services.normalizer import normalize_log_rows, normalize_maintenance_blocks
from app.services.prioritizer import cluster_and_prioritize_events


def test_parsing_and_normalization():
    csv_data = """timestamp,signal,value,unit
2026-10-13T08:22:10+02:00,motor_temperature,86.5,°C
2026-10-13T11:15:20+02:00,vibration_rms,4.8,mm/s
2026-10-13T09:40:15+02:00,hydraulic_pressure,162.0,bar
"""
    rows, errors = parse_csv_machine_log(csv_data, "src-test", "press-07")
    assert len(errors) == 0
    assert len(rows) == 3

    events = normalize_log_rows(rows, PRESS_07_ASSET)
    assert len(events) == 3

    # Check motor temp exceeded trip limit
    temp_evt = [e for e in events if "motor_temperature" in e.priority_signals.get("signal_name", "")][0]
    assert temp_evt.event_type == "threshold_exceeded"
    assert temp_evt.priority_signals["severity_level"] == "critical"
    assert temp_evt.priority_signals["deviation"] == 1.5  # 86.5 - 85.0

    # Check vibration spike
    vib_evt = [e for e in events if "vibration_rms" in e.priority_signals.get("signal_name", "")][0]
    assert vib_evt.priority_signals["severity_level"] == "critical"
    assert vib_evt.priority_signals["deviation"] == 0.3  # 4.8 - 4.5


def test_prioritization_heuristic():
    csv_data = """timestamp,signal,value,unit
2026-10-13T08:22:10+02:00,motor_temperature,86.5,°C
2026-10-13T10:45:30+02:00,motor_temperature,88.2,°C
2026-10-13T13:10:45+02:00,motor_temperature,91.4,°C
2026-10-13T11:15:20+02:00,vibration_rms,4.8,mm/s
"""
    rows, _ = parse_csv_machine_log(csv_data, "src-test", "press-07")
    events = normalize_log_rows(rows, PRESS_07_ASSET)
    ranked = cluster_and_prioritize_events(
        events,
        window_start="2026-10-13T06:00:00+02:00",
        window_end="2026-10-13T14:00:00+02:00"
    )
    assert len(ranked) >= 2
    # Motor temp has 3 repeated breaches + high deviation, so must be ranked top with High priority
    top_cluster = ranked[0]
    assert top_cluster["cluster_key"] == "motor_temperature"
    assert top_cluster["priority"] == "high"
    assert top_cluster["priority_score"] >= 0.70
    assert any("Repeated 3 times" in f for f in top_cluster["priority_factors"])


def test_end_to_end_api_flow():
    with TestClient(app) as client:
        # 1. Health check
        resp_health = client.get("/api/health")
        assert resp_health.status_code == 200
        health_data = resp_health.json()
        assert health_data["status"] == "ok"
        assert "AMD" in health_data["amd_accelerator"]

        # 2. Load synthetic demo bundle
        resp_bundle = client.post("/api/demo/load-bundle")
        assert resp_bundle.status_code == 200
        bundle_data = resp_bundle.json()
        assert bundle_data["status"] == "success"
        handover_id = bundle_data["handover_id"]

        # 3. Read handover
        resp_ho = client.get(f"/api/handovers/{handover_id}")
        assert resp_ho.status_code == 200
        ho_data = resp_ho.json()
        assert len(ho_data["items"]) >= 3
        # Top item must be high priority
        assert ho_data["items"][0]["priority"] == "high"
        # Citations must be attached
        assert len(ho_data["items"][0]["evidence_refs"]) > 0

        # 4. Patch item status to acknowledged
        top_item_id = ho_data["items"][0]["item_id"]
        resp_patch = client.patch(
            f"/api/handovers/{handover_id}/items/{top_item_id}",
            json={"status": "acknowledged", "operator_notes": "Reviewed with incoming lead. SOP-M42 scheduled."}
        )
        assert resp_patch.status_code == 200
        assert resp_patch.json()["status"] == "acknowledged"
        assert resp_patch.json()["edited_by_user"] is True

        # 5. Export Markdown
        resp_export = client.get(f"/api/handovers/{handover_id}/export.md")
        assert resp_export.status_code == 200
        assert "# Shift Handover Briefing" in resp_export.text
        assert "[ACKNOWLEDGED]" in resp_export.text

        # 6. Run Evaluation Benchmark
        resp_eval = client.post(f"/api/evaluate?handover_id={handover_id}")
        assert resp_eval.status_code == 200
        eval_data = resp_eval.json()
        assert eval_data["citation_validity_pass"] is True
        assert eval_data["high_priority_recall_pass"] is True
        assert eval_data["unsupported_claim_pass"] is True
        assert eval_data["all_targets_met"] is True


def test_upload_boundaries_and_workflow_validation():
    with TestClient(app) as client:
        too_large = client.post(
            "/api/sources",
            files={"file": ("oversized.txt", b"x" * (10 * 1024 * 1024 + 1), "text/plain")},
        )
        assert too_large.status_code == 413

        unsupported = client.post(
            "/api/sources",
            files={"file": ("payload.exe", b"not allowed", "application/octet-stream")},
        )
        assert unsupported.status_code == 415

        unknown_asset = client.post(
            "/api/sources",
            data={"asset_id": "not-configured"},
            files={"file": ("notes.txt", b"Operator note", "text/plain")},
        )
        assert unknown_asset.status_code == 404

        bundle = client.post("/api/demo/load-bundle").json()
        handover = client.get(f"/api/handovers/{bundle['handover_id']}").json()
        item_id = handover["items"][0]["item_id"]
        invalid_update = client.patch(
            f"/api/handovers/{bundle['handover_id']}/items/{item_id}",
            json={"status": "completed"},
        )
        assert invalid_update.status_code == 422
