"""
Pydantic data models and canonical schemas for Shift Handover Briefing.
Complies with DATA_MODEL_AND_API.md and PRD.md.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Asset(BaseModel):
    asset_id: str
    display_name: str
    timezone: str = "Europe/Rome"
    signals: List[str] = Field(default_factory=list)
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)


class SourceRef(BaseModel):
    source_id: str
    locator: str  # e.g., "row:18", "page:14", "section:4.2", "timestamp:08:22"
    snippet: Optional[str] = None


class SourceDocument(BaseModel):
    source_id: str
    asset_id: str
    kind: Literal["machine_log", "maintenance_note", "operator_audio", "manual"]
    filename: str
    content_hash: str
    captured_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_content: Optional[str] = None


class SignalReading(BaseModel):
    name: str
    value: float
    unit: Optional[str] = None


class Event(BaseModel):
    event_id: str
    asset_id: str
    occurred_at: str
    event_type: str  # "threshold_exceeded", "alarm", "maintenance", "operator_observation", "unknown"
    summary: str
    signals: List[SignalReading] = Field(default_factory=list)
    source_refs: List[SourceRef] = Field(default_factory=list)
    confidence: Optional[float] = 1.0
    priority_signals: Dict[str, Any] = Field(default_factory=dict)


class ManualPassage(BaseModel):
    passage_id: str
    source_id: str
    title: str
    section: str
    page: int
    content: str
    keywords: List[str] = Field(default_factory=list)


class HandoverItem(BaseModel):
    item_id: str
    priority: Literal["high", "medium", "low"]
    priority_score: float
    priority_factors: List[str] = Field(default_factory=list)
    what_changed: str
    suggested_check: str
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty: Optional[str] = None
    human_review_required: bool = True
    status: Literal["draft", "acknowledged", "deferred", "assigned"] = "draft"
    assigned_to: Optional[str] = None
    operator_notes: Optional[str] = None
    edited_by_user: bool = False


class HandoverGenerationRequest(BaseModel):
    asset_id: str = "press-07"
    shift_name: Optional[str] = "Shift B"
    window_start: str = "2026-10-13T06:00:00+02:00"
    window_end: str = "2026-10-13T14:00:00+02:00"
    previous_window_start: Optional[str] = "2026-10-12T22:00:00+02:00"
    previous_window_end: Optional[str] = "2026-10-13T06:00:00+02:00"


class Handover(BaseModel):
    handover_id: str
    asset_id: str
    shift_name: str
    window_start: str
    window_end: str
    previous_window_start: Optional[str] = None
    previous_window_end: Optional[str] = None
    created_at: str
    status: str = "draft"  # "draft", "reviewed", "approved"
    coverage_summary: Dict[str, Any] = Field(default_factory=dict)
    items: List[HandoverItem] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)


class HandoverItemUpdate(BaseModel):
    priority: Optional[Literal["high", "medium", "low"]] = None
    what_changed: Optional[str] = Field(default=None, max_length=2000)
    suggested_check: Optional[str] = Field(default=None, max_length=2000)
    uncertainty: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[Literal["draft", "acknowledged", "deferred", "assigned"]] = None
    assigned_to: Optional[str] = Field(default=None, max_length=200)
    operator_notes: Optional[str] = Field(default=None, max_length=5000)


class IngestionJob(BaseModel):
    job_id: str
    source_id: str
    status: str  # "pending", "processing", "completed", "failed"
    events_extracted: int = 0
    errors: List[str] = Field(default_factory=list)
    created_at: str


class HealthStatus(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    amd_endpoint_connected: bool
    amd_endpoint_url: Optional[str] = None
    amd_model_id: str
    amd_accelerator: str
    latency_ms: Optional[float] = None
    endpoint_reachable: bool = False
    inference_completed_on_amd: bool = False
    mode: str = "deterministic_fallback"
    active_session_assets: int = 1


class EvaluationMetricDetail(BaseModel):
    case_id: str
    description: str
    expected_priority: str
    actual_priority: Optional[str]
    citation_valid: bool
    unsupported_claim: bool
    passed: bool
    notes: str


class EvaluationReport(BaseModel):
    total_cases: int
    citation_validity_score: float
    citation_validity_target: float = 0.90
    citation_validity_pass: bool
    high_priority_recall_score: float
    high_priority_recall_target: float = 0.80
    high_priority_recall_pass: bool
    unsupported_claim_rate: float
    unsupported_claim_target: float = 0.00
    unsupported_claim_pass: bool
    input_coverage_score: float
    draft_time_seconds: float
    all_targets_met: bool
    details: List[EvaluationMetricDetail]
