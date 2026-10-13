---
title: Shift Handover Briefing
type: project-documentation
status: hackathon-mvp-complete
updated: 2026-10-13
---

# Shift Handover Briefing — AMD Intelligent Industry

A decision-support system that turns multimodal machine logs, maintenance notes, operator voice memos, and equipment manuals into an evidence-linked, prioritized shift handover running on AMD GPU infrastructure and ROCm.

> **One-line pitch:** The next shift knows what changed, what needs attention, why it matters, and where the evidence came from—in minutes, not after piecing together scattered notes.

---

## 🚀 Live Demo & Quickstart

The prototype runs as a self-contained web service (FastAPI backend + responsive dark industrial UI):

```bash
# Clone and enter directory
cd "shift-handover-briefing"

# Start the application locally
./run.sh
```

Or run via Docker:
```bash
docker compose up --build
```

The web application opens at **http://localhost:8000**.

---

## ⚡ AMD ROCm Workload

- **Core Synthesis Inference:** Runs on open models (`meta-llama/Llama-3.1-70B-Instruct` or `mistralai/Mistral-7B-Instruct-v0.3`) hosted on AMD Instinct GPUs (MI300X / MI250) using vLLM or TGI on ROCm.
- **Live Health Diagnostics:** The UI features a real-time AMD ROCm status pill backed by `/api/health` that probes the active inference endpoint and displays accelerator telemetry and latency.
- **Verified Fallback Engine:** If the cloud endpoint is offline during presentation or testing, a verified deterministic synthesis engine guarantees 100% evidence citation grounding without crashing or hallucinating.

To configure an active AMD Developer Cloud endpoint, copy `.env.example` to `.env` or set environment variables:
```bash
AMD_ENDPOINT_URL=https://your-amd-vllm-endpoint.example.com/v1
AMD_API_KEY=your_token
AMD_MODEL_ID=meta-llama/Llama-3.1-70B-Instruct
```

---

## 📊 Prototype Benchmark Results

Evaluated against the 10 labeled ground truth test cases defined in [Risks and Evaluation](RISKS_AND_EVALUATION.md):

| Metric | Target | Prototype Score | Result |
|---|---|---|---|
| **Citation Validity** | ≥ 90% | **100%** | **PASS** |
| **Recall@3 High Priority** | ≥ 80% | **100%** | **PASS** |
| **Unsupported-Claim Rate** | 0.0% | **0.0%** | **PASS** |
| **Input Coverage** | ≥ 80% | **100%** | **PASS** |
| **Handover Draft Time** | < 120s | **1.42s** | **PASS** |

Click the **Benchmark** button in the app header or call `POST /api/evaluate` to run the test suite live.

---

## 🛠️ Architecture & Pipeline

```text
Browser UI (Industrial Dark Theme / Glassmorphism)
   │ HTTP / JSON / File Uploads
   ▼
FastAPI Application ─────────────── SQLite (Database & Sessions)
   │
   ├── 1. Ingestion: CSV/JSON telemetry, Markdown/TXT notes, PDF/MD manuals, WAV audio
   ├── 2. Normalization: Canonical Events with asset baseline checks (press-07)
   ├── 3. Transcription Adapter: Audio player, waveform canvas & transcript editor
   ├── 4. Manual Chunking & Retrieval: BM25-style lexical passage matcher with page/section anchors
   ├── 5. Prioritization Heuristic: Transparent scoring (Severity, Repetition, Deviation, Recency, Operator Flag)
   └── 6. AMD Synthesis: Structured schema verification, evidence linking, and human-review flags
          │
          ▼
     AMD ROCm / vLLM Endpoint (Instinct MI300X / Llama-3.1-70B)
```

---

## 🧪 Seeded Demo Scenario (Hydraulic Press 07)

The bundle seeds realistic industrial telemetry for **Hydraulic Press 07 (HP-750)** across Shift B (06:00 to 14:00):
1. **Telemetry CSV (`shift_b_telemetry.csv`):** Motor temperature repeated excursions peaking at 91.4 °C (trip limit 85.0 °C), vibration surge to 4.8 mm/s RMS (trip limit 4.5 mm/s), and transient pressure drop to 162 bar.
2. **Maintenance Notes (`maintenance_notes_shift_a.md`):** Filter cartridge replacement and oil top-up on Shift A; instructions to monitor differential pressure.
3. **Operator Voice Memo (`operator_voice_memo.wav`):** Outgoing operator audio memo from Marco flagging a hot motor casing and high-pitch whine on the cooling circuit.
4. **Equipment Manual (`hydraulic_press_07_sop_manual.md`):** Section 4.2 (Page 14) describing heat exchanger descaling (SOP-M42) and Section 7.1 (Page 22) suction manifold cavitation checks.

---

## 🔌 API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web application single-page interface |
| `GET` | `/api/health` | Live AMD ROCm endpoint status, accelerator, and latency |
| `GET` | `/api/assets` | Configured machine assets and baseline thresholds |
| `GET` | `/api/sources` | Ingested source documents |
| `POST` | `/api/sources` | Upload and parse CSV, JSON, MD, TXT, PDF, or WAV |
| `GET` | `/api/sources/{id}/download` | Stream or download source file / audio memo |
| `GET` | `/api/events` | Chronological event list with provenance locators |
| `POST` | `/api/handovers` | Synthesize prioritized, evidence-linked handover |
| `GET` | `/api/handovers/{id}` | Retrieve generated handover and citations |
| `PATCH` | `/api/handovers/{id}/items/{item_id}` | Operator update (status, notes, priority) |
| `GET` | `/api/handovers/{id}/export.md` | Export approved Markdown briefing with sign-off |
| `POST` | `/api/demo/load-bundle` | One-click loader for the synthetic demo scenario |
| `DELETE` | `/api/demo-session` | Clear session files and derived records |
| `POST` | `/api/evaluate` | Run 10-test benchmark evaluation report |

---

## 🛡️ Human-in-the-Loop Safety Boundary

This product is an **operator decision-support aid**. It does not issue machine control signals, actuate valves, or authorize maintenance without qualification. Every recommendation is phrased as a suggested check under approved standard operating procedures (SOP), and all claims link to verified source evidence.

---

## 🧪 Running Automated Tests

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_all.py -v
```
All unit and integration tests run in under 1 second.
