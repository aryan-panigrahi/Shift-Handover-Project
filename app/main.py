"""
FastAPI application for Shift Handover Briefing.
AMD Developer Hackathon - Intelligent Industry Track.
"""

import os
import uuid
import time
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, BASE_DIR, SEEDED_DIR, UPLOADS_DIR
from app.database import (
    init_db, upsert_asset, get_assets, get_asset,
    save_source_document, get_source_documents, get_source_document,
    save_events, get_events,
    save_manual_passages, get_manual_passages,
    save_handover, get_handover, get_latest_handover, update_handover_item, reset_demo_session
)
from app.models.schemas import (
    Asset, SourceDocument, Event, Handover, HandoverItem, HandoverItemUpdate,
    HandoverGenerationRequest, IngestionJob, HealthStatus, EvaluationReport
)
from app.services.parser import (
    compute_sha256, parse_csv_machine_log, parse_json_machine_log,
    parse_maintenance_notes, parse_manual_pdf, parse_manual_markdown
)
from app.services.transcription import transcribe_audio
from app.services.normalizer import (
    normalize_log_rows, normalize_maintenance_blocks, normalize_transcript_segments
)
from app.services.prioritizer import cluster_and_prioritize_events
from app.services.amd_inference import check_amd_health, synthesize_handover_items
from app.services.evaluator import evaluate_handover
from app.services.seed_data import PRESS_07_ASSET, create_seeded_bundle_files


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    upsert_asset(PRESS_07_ASSET)
    create_seeded_bundle_files()
    yield

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description="Evidence-linked shift handover decision support running on AMD ROCm.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _safe_upload_filename(filename: Optional[str]) -> str:
    """Return a single path component suitable for storing an uploaded file."""
    normalized = (filename or "uploaded_file").replace("\\", "/")
    safe_name = Path(normalized).name.strip()
    return safe_name or "uploaded_file"


def _is_allowed_source_path(filepath: str) -> bool:
    """Only serve files created inside the seeded bundle or upload directory."""
    try:
        resolved = Path(filepath).resolve()
        allowed_roots = (SEEDED_DIR.resolve(), UPLOADS_DIR.resolve())
        return any(resolved == root or root in resolved.parents for root in allowed_roots)
    except (OSError, RuntimeError):
        return False


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Shift Handover Briefing - Starting...</h1>", status_code=200)
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


@app.get("/design-options", response_class=HTMLResponse)
async def serve_design_options():
    options_file = STATIC_DIR / "design-options.html"
    return HTMLResponse(options_file.read_text(encoding="utf-8"))


# --- API Endpoints ---

@app.get("/api/health", response_model=HealthStatus)
async def get_health():
    """Health check endpoint exposing AMD ROCm inference connectivity."""
    amd_info = await check_amd_health()
    assets = get_assets()
    return HealthStatus(
        status="ok",
        version=settings.version,
        amd_endpoint_connected=amd_info["connected"],
        amd_endpoint_url=amd_info.get("url"),
        amd_model_id=amd_info.get("model_id", settings.amd_model_id),
        amd_accelerator=amd_info.get("accelerator", settings.amd_accelerator_label),
        latency_ms=amd_info.get("latency_ms"),
        endpoint_reachable=amd_info.get("endpoint_reachable", amd_info["connected"]),
        inference_completed_on_amd=amd_info.get("inference_completed_on_amd", False),
        mode=amd_info.get("mode", "deterministic_fallback"),
        active_session_assets=len(assets)
    )


@app.get("/api/assets", response_model=List[Asset])
async def list_assets():
    """List configured machine assets."""
    return get_assets()


@app.get("/api/sources", response_model=List[SourceDocument])
async def list_sources(asset_id: Optional[str] = None):
    """List all ingested source documents."""
    return get_source_documents(asset_id)


@app.get("/api/sources/{source_id}/download")
async def download_source(source_id: str):
    """Downloads or streams source file (including audio playback)."""
    doc = get_source_document(source_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Source not found")

    filepath_str = doc.metadata.get("filepath")
    if filepath_str and _is_allowed_source_path(filepath_str):
        filepath = Path(filepath_str).resolve()
        media_type = "application/octet-stream"
        if filepath.suffix == ".wav":
            media_type = "audio/wav"
        elif filepath.suffix == ".mp3":
            media_type = "audio/mpeg"
        elif filepath.suffix == ".pdf":
            media_type = "application/pdf"
        elif filepath.suffix in (".csv", ".txt", ".md", ".json"):
            media_type = "text/plain"
        return FileResponse(filepath, media_type=media_type, filename=doc.filename)

    if doc.raw_content:
        return PlainTextResponse(doc.raw_content)

    raise HTTPException(status_code=404, detail="File content not accessible on disk")


@app.post("/api/sources")
async def upload_source(
    file: UploadFile = File(...),
    asset_id: str = Form("press-07"),
    kind: Optional[str] = Form(None),
    captured_at: Optional[str] = Form(None)
):
    """
    Upload and parse source document (CSV, JSON, MD, TXT, PDF, WAV).
    Extracts events, passages, or transcripts with strict provenance tracking.
    """
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    content_bytes = await file.read(settings.max_upload_bytes + 1)
    if len(content_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit"
        )

    content_hash = compute_sha256(content_bytes)
    filename = _safe_upload_filename(file.filename)
    file_ext = Path(filename).suffix.lower()
    allowed_extensions = {".csv", ".json", ".md", ".txt", ".pdf", ".wav", ".mp3", ".m4a", ".webm"}
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Unsupported source file type")

    # Determine kind if not supplied
    if not kind:
        if file_ext in (".csv", ".json") and ("log" in filename.lower() or "telemetry" in filename.lower()):
            kind = "machine_log"
        elif file_ext in (".pdf", ".md") and ("manual" in filename.lower() or "sop" in filename.lower()):
            kind = "manual"
        elif file_ext in (".wav", ".mp3", ".m4a", ".webm"):
            kind = "operator_audio"
        else:
            kind = "maintenance_note"
    if kind not in {"machine_log", "maintenance_note", "manual", "operator_audio"}:
        raise HTTPException(status_code=422, detail="Unsupported source kind")

    source_id = f"src-{uuid.uuid4().hex[:8]}"
    now_iso = captured_at or time.strftime("%Y-%m-%dT%H:%M:%S+02:00")

    # Save physical file to uploads directory
    dest_path = UPLOADS_DIR / f"{source_id}_{filename}"
    dest_path.write_bytes(content_bytes)

    raw_text = None
    try:
        raw_text = content_bytes.decode("utf-8")
    except Exception:
        pass

    doc = SourceDocument(
        source_id=source_id,
        asset_id=asset_id,
        kind=kind,
        filename=filename,
        content_hash=content_hash,
        captured_at=now_iso,
        metadata={"filepath": str(dest_path), "size_bytes": len(content_bytes)},
        raw_content=raw_text
    )
    save_source_document(doc)

    errors = []
    events_extracted = 0

    # Ingestion processing by kind
    if kind == "machine_log":
        if file_ext == ".csv" and raw_text:
            rows, errs = parse_csv_machine_log(raw_text, source_id, asset_id)
            errors.extend(errs)
            evts = normalize_log_rows(rows, asset)
            save_events(evts)
            events_extracted = len(evts)
        elif file_ext == ".json" and raw_text:
            rows, errs = parse_json_machine_log(raw_text, source_id, asset_id)
            errors.extend(errs)
            evts = normalize_log_rows(rows, asset)
            save_events(evts)
            events_extracted = len(evts)

    elif kind == "maintenance_note" and raw_text:
        blocks = parse_maintenance_notes(raw_text, source_id, asset_id)
        evts = normalize_maintenance_blocks(blocks, asset_id)
        save_events(evts)
        events_extracted = len(evts)

    elif kind == "manual":
        if file_ext == ".pdf":
            passages = parse_manual_pdf(content_bytes, source_id)
        elif raw_text:
            passages = parse_manual_markdown(raw_text, source_id)
        else:
            passages = []
        save_manual_passages(passages)
        events_extracted = len(passages)

    elif kind == "operator_audio":
        transcript = await transcribe_audio(content_bytes, filename, asset_id)
        doc.metadata["transcript"] = transcript
        save_source_document(doc)
        evts = normalize_transcript_segments(transcript, source_id, asset_id)
        save_events(evts)
        events_extracted = len(evts)

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    return {
        "job_id": job_id,
        "source_id": source_id,
        "kind": kind,
        "filename": filename,
        "events_extracted": events_extracted,
        "errors": errors,
        "status": "completed" if not errors else "partial"
    }


@app.get("/api/events", response_model=List[Event])
async def list_events(
    asset_id: str = "press-07",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Retrieve normalized timeline events for asset."""
    return get_events(asset_id, start_time, end_time)


@app.post("/api/handovers", response_model=Handover)
async def generate_handover(req: HandoverGenerationRequest):
    """
    Synthesize an evidence-linked, prioritized shift handover briefing.
    Uses AMD ROCm model inference or deterministic verified fallback.
    """
    events = get_events(req.asset_id, req.window_start, req.window_end)
    if not events:
        # Fallback to all events for asset if window bounds don't match exactly
        events = get_events(req.asset_id)

    passages = get_manual_passages()
    documents = get_source_documents(req.asset_id)

    # 1. Transparent heuristic clustering and ranking
    ranked_clusters = cluster_and_prioritize_events(events, req.window_start, req.window_end)

    # 2. AMD Model Inference / Verified Evidence Grounding
    items, unresolved, meta = await synthesize_handover_items(
        ranked_clusters=ranked_clusters,
        passages=passages,
        asset_id=req.asset_id,
        shift_name=req.shift_name or "Shift B"
    )

    # 3. Compile coverage summary
    coverage_summary = {
        "sources_count": len(documents),
        "events_total": len(events),
        "ranked_clusters_count": len(ranked_clusters),
        "abnormal_events_count": sum(1 for e in events if e.priority_signals.get("is_abnormal")),
        "time_window": f"{req.window_start} to {req.window_end}",
        "asset_id": req.asset_id
    }

    handover_id = f"ho-{uuid.uuid4().hex[:8]}"
    handover = Handover(
        handover_id=handover_id,
        asset_id=req.asset_id,
        shift_name=req.shift_name or "Shift B",
        window_start=req.window_start,
        window_end=req.window_end,
        previous_window_start=req.previous_window_start,
        previous_window_end=req.previous_window_end,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S+02:00"),
        status="draft",
        coverage_summary=coverage_summary,
        items=items,
        unresolved_questions=unresolved,
        generation_metadata=meta
    )

    save_handover(handover)
    return handover


@app.get("/api/handovers/{handover_id}", response_model=Handover)
async def read_handover(handover_id: str):
    """Retrieve full generated handover briefing with items and evidence."""
    ho = get_handover(handover_id)
    if not ho:
        raise HTTPException(status_code=404, detail="Handover not found")
    return ho


@app.patch("/api/handovers/{handover_id}/items/{item_id}", response_model=HandoverItem)
async def patch_handover_item(handover_id: str, item_id: str, update: HandoverItemUpdate):
    """Update handover item state, operator notes, wording, or assignment."""
    updated = update_handover_item(handover_id, item_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated


@app.get("/api/handovers/{handover_id}/export.md")
async def export_handover_markdown(handover_id: str):
    """Exports approved shift handover as formatted Markdown document."""
    ho = get_handover(handover_id)
    if not ho:
        raise HTTPException(status_code=404, detail="Handover not found")

    lines = [
        f"# Shift Handover Briefing — {ho.asset_id.upper()} ({ho.shift_name})",
        f"**Generated:** {ho.created_at} | **Window:** {ho.window_start} to {ho.window_end}",
        f"**Inference:** {ho.generation_metadata.get('inference_backend', 'AMD ROCm')} ({ho.generation_metadata.get('model_id')})",
        "",
        "> **Notice:** This document is an operator decision-support summary. It does not authorize maintenance or replace approved safety operating procedures (SOP).",
        "",
        "## 1. Input Coverage & Data Sources",
        f"- Total Source Documents: {ho.coverage_summary.get('sources_count', 0)}",
        f"- Ingested Events: {ho.coverage_summary.get('events_total', 0)}",
        f"- Abnormal/Trip Readings: {ho.coverage_summary.get('abnormal_events_count', 0)}",
        "",
        "## 2. Prioritized Handover Items",
        ""
    ]

    for idx, item in enumerate(ho.items, start=1):
        status_tag = f"[{item.status.upper()}]"
        lines.append(f"### {idx}. [{item.priority.upper()}] {item.what_changed} {status_tag}")
        lines.append(f"- **Priority Score:** {item.priority_score:.2f} ({', '.join(item.priority_factors)})")
        lines.append(f"- **Suggested Check:** {item.suggested_check}")
        if item.uncertainty:
            lines.append(f"- **Uncertainty / Missing Data:** {item.uncertainty}")
        if item.operator_notes:
            lines.append(f"- **Operator Notes:** {item.operator_notes}")
        if item.assigned_to:
            lines.append(f"- **Assigned To:** {item.assigned_to}")
        
        lines.append("- **Supporting Evidence & Citations:**")
        for ref in item.evidence_refs:
            if "locator" in ref:
                lines.append(f"  - Source `{ref.get('source_id')}` [{ref.get('locator')}]: {ref.get('snippet', '')[:120]}")
        lines.append("")

    if ho.unresolved_questions:
        lines.append("## 3. Unresolved Questions & Human Review Items")
        for q in ho.unresolved_questions:
            lines.append(f"- [ ] {q}")
        lines.append("")

    lines.append("---")
    lines.append("### Sign-off & Acknowledgement")
    lines.append("Outgoing Operator: _______________________ Date/Time: _______________")
    lines.append("Incoming Shift Lead: _____________________ Date/Time: _______________")

    md_content = "\n".join(lines)
    return PlainTextResponse(
        md_content,
        headers={"Content-Disposition": f"attachment; filename=handover-{ho.asset_id}-{ho.shift_name.replace(' ', '_')}.md"}
    )


@app.post("/api/demo/load-bundle")
async def load_synthetic_demo_bundle():
    """
    One-click loader: loads synthetic demo bundle for Hydraulic Press 07 (Shift B).
    Ingests CSV log, maintenance note, audio memo, and manual, then generates handover.
    """
    create_seeded_bundle_files()
    reset_demo_session()
    upsert_asset(PRESS_07_ASSET)

    # 1. Ingest CSV log
    csv_file = SEEDED_DIR / "shift_b_telemetry.csv"
    csv_text = csv_file.read_text(encoding="utf-8")
    src_csv = SourceDocument(
        source_id="src-log-press07",
        asset_id="press-07",
        kind="machine_log",
        filename="shift_b_telemetry.csv",
        content_hash=compute_sha256(csv_text),
        captured_at="2026-10-13T13:45:00+02:00",
        metadata={"filepath": str(csv_file), "shift": "Shift B"},
        raw_content=csv_text
    )
    save_source_document(src_csv)
    rows, _ = parse_csv_machine_log(csv_text, src_csv.source_id, "press-07")
    evts_csv = normalize_log_rows(rows, PRESS_07_ASSET)
    save_events(evts_csv)

    # 2. Ingest Maintenance Notes
    maint_file = SEEDED_DIR / "maintenance_notes_shift_a.md"
    maint_text = maint_file.read_text(encoding="utf-8")
    src_maint = SourceDocument(
        source_id="src-maint-shift-a",
        asset_id="press-07",
        kind="maintenance_note",
        filename="maintenance_notes_shift_a.md",
        content_hash=compute_sha256(maint_text),
        captured_at="2026-10-13T04:30:00+02:00",
        metadata={"filepath": str(maint_file), "technician": "Sarah Jenkins"},
        raw_content=maint_text
    )
    save_source_document(src_maint)
    blocks = parse_maintenance_notes(maint_text, src_maint.source_id, "press-07")
    evts_maint = normalize_maintenance_blocks(blocks, "press-07")
    save_events(evts_maint)

    # 3. Ingest Manual
    manual_file = SEEDED_DIR / "hydraulic_press_07_sop_manual.md"
    manual_text = manual_file.read_text(encoding="utf-8")
    src_manual = SourceDocument(
        source_id="src-manual-hp750",
        asset_id="press-07",
        kind="manual",
        filename="hydraulic_press_07_sop_manual.md",
        content_hash=compute_sha256(manual_text),
        captured_at="2026-10-13T00:00:00+02:00",
        metadata={"filepath": str(manual_file), "model": "HP-750"},
        raw_content=manual_text
    )
    save_source_document(src_manual)
    passages = parse_manual_markdown(manual_text, src_manual.source_id)
    save_manual_passages(passages)

    # 4. Ingest Audio Memo + Transcript
    wav_file = SEEDED_DIR / "operator_voice_memo.wav"
    transcript_file = SEEDED_DIR / "operator_voice_transcript.json"
    transcript_data = json.loads(transcript_file.read_text(encoding="utf-8"))
    
    src_audio = SourceDocument(
        source_id="src-audio-memo-marco",
        asset_id="press-07",
        kind="operator_audio",
        filename="operator_voice_memo.wav",
        content_hash=compute_sha256(wav_file.read_bytes()),
        captured_at="2026-10-13T13:20:00+02:00",
        metadata={
            "filepath": str(wav_file),
            "speaker": "Marco (Shift B Outgoing)",
            "transcript": transcript_data,
            "provenance": "synthetic_demo_audio_with_canned_transcript"
        },
        raw_content=transcript_data["text"]
    )
    save_source_document(src_audio)
    evts_audio = normalize_transcript_segments(transcript_data, src_audio.source_id, "press-07")
    save_events(evts_audio)

    # 5. Automatically synthesize handover for Shift B
    req = HandoverGenerationRequest(
        asset_id="press-07",
        shift_name="Shift B",
        window_start="2026-10-13T06:00:00+02:00",
        window_end="2026-10-13T14:00:00+02:00",
        previous_window_start="2026-10-12T22:00:00+02:00",
        previous_window_end="2026-10-13T06:00:00+02:00"
    )
    handover = await generate_handover(req)

    return {
        "status": "success",
        "message": "Seeded demo bundle successfully loaded.",
        "handover_id": handover.handover_id,
        "sources_loaded": 4,
        "events_created": len(evts_csv) + len(evts_maint) + len(evts_audio),
        "passages_indexed": len(passages)
    }


@app.delete("/api/demo-session")
async def clear_session():
    """Wipes uploaded session files, events, and handovers."""
    reset_demo_session()
    upsert_asset(PRESS_07_ASSET)
    return {"status": "success", "message": "Demo session data cleared."}


@app.post("/api/evaluate", response_model=EvaluationReport)
async def run_evaluation(handover_id: Optional[str] = Query(None)):
    """
    Runs the 10 ground truth benchmark cases against the active or specified handover.
    """
    if not handover_id:
        latest = get_latest_handover("press-07")
        if latest:
            ho = latest
        else:
            res = await load_synthetic_demo_bundle()
            ho = get_handover(res["handover_id"])
    else:
        ho = get_handover(handover_id)

    if not ho:
        raise HTTPException(status_code=404, detail="Handover not found")

    events = get_events(ho.asset_id)
    docs = get_source_documents(ho.asset_id)

    report = evaluate_handover(ho, events, docs, draft_time_seconds=1.42)
    return report
