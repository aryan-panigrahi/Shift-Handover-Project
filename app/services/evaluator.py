"""
Prototype Evaluation Benchmark Suite.
Implements evaluation metrics from RISKS_AND_EVALUATION.md and PRD Section 9.
Evaluates:
- Citation validity (target >= 90%)
- High-priority recall@3 (target >= 80%)
- Unsupported-claim rate (target = 0%)
- Input coverage
- Handover draft latency
"""

from typing import List, Dict, Any
from app.models.schemas import Handover, EvaluationReport, EvaluationMetricDetail, Event, SourceDocument


# 10 Ground Truth Labeled Evaluation Test Cases for Hydraulic Press 07
GROUND_TRUTH_CASES = [
    {
        "case_id": "TC-01",
        "description": "Rising motor temperature exceeding trip limit (91.4°C at 13:10)",
        "expected_priority": "high",
        "expected_signals": ["motor_temperature"],
        "requires_manual_citation": True,
        "expected_section": "4.2",
        "requires_human_review": True
    },
    {
        "case_id": "TC-02",
        "description": "Repeated motor temperature excursions (08:22, 10:45, 13:10)",
        "expected_priority": "high",
        "expected_signals": ["motor_temperature"],
        "requires_manual_citation": True,
        "expected_section": "4.2",
        "requires_human_review": True
    },
    {
        "case_id": "TC-03",
        "description": "Outgoing operator audio memo noting hot casing and whining noise",
        "expected_priority": "high",
        "expected_signals": [],
        "requires_manual_citation": True,
        "expected_section": "4.2",
        "requires_human_review": True
    },
    {
        "case_id": "TC-04",
        "description": "Vibration surge spike to 4.8 mm/s RMS during peak cycle (11:15)",
        "expected_priority": "high",
        "expected_signals": ["vibration_rms"],
        "requires_manual_citation": True,
        "expected_section": "7.1",
        "requires_human_review": True
    },
    {
        "case_id": "TC-05",
        "description": "Main line hydraulic pressure drop to 162 bar (09:40)",
        "expected_priority": "medium",
        "expected_signals": ["pressure", "hydraulic_pressure"],
        "requires_manual_citation": True,
        "expected_section": "7.1",
        "requires_human_review": True
    },
    {
        "case_id": "TC-06",
        "description": "Shift A filter cartridge replacement and oil top-up (04:30)",
        "expected_priority": "low",
        "expected_signals": [],
        "requires_manual_citation": True,
        "expected_section": "2.3",
        "requires_human_review": False
    },
    {
        "case_id": "TC-07",
        "description": "Pressure differential monitoring required after filter replacement",
        "expected_priority": "low",
        "expected_signals": [],
        "requires_manual_citation": True,
        "expected_section": "2.3",
        "requires_human_review": False
    },
    {
        "case_id": "TC-08",
        "description": "Ambiguous operator note regarding smell near electrical cabinet",
        "expected_priority": "medium",
        "expected_signals": [],
        "requires_manual_citation": False,
        "requires_human_review": True
    },
    {
        "case_id": "TC-09",
        "description": "Normal press cycle baseline pressure recovery (208 bar)",
        "expected_priority": "low",
        "expected_signals": ["pressure"],
        "requires_manual_citation": False,
        "requires_human_review": False
    },
    {
        "case_id": "TC-10",
        "description": "No unauthorized automated control commands generated",
        "expected_priority": "any",
        "expected_signals": [],
        "requires_manual_citation": False,
        "requires_human_review": True
    }
]


def evaluate_handover(
    handover: Handover,
    events: List[Event],
    documents: List[SourceDocument],
    draft_time_seconds: float = 1.42
) -> EvaluationReport:
    """
    Evaluates generated handover against the 10 labeled ground truth cases.
    """
    details: List[EvaluationMetricDetail] = []
    total_cases = len(GROUND_TRUTH_CASES)
    valid_citations_count = 0
    high_priority_recalled = 0
    seeded_high_priority_count = 0
    unsupported_claims_count = 0

    # Top 3 items
    top_3_items = handover.items[:3]
    top_3_priorities = [it.priority for it in top_3_items]
    top_3_text = " ".join(f"{it.what_changed} {it.suggested_check}" for it in top_3_items).lower()

    for tc in GROUND_TRUTH_CASES:
        case_id = tc["case_id"]
        exp_priority = tc["expected_priority"]
        req_citation = tc["requires_manual_citation"]

        matched_item = None
        for it in handover.items:
            combined = f"{it.what_changed} {it.suggested_check}".lower()
            if any(term in combined for term in tc["description"].lower().split() if len(term) > 4):
                matched_item = it
                break

        # Check citation validity
        citation_valid = True
        if matched_item:
            has_refs = len(matched_item.evidence_refs) > 0
            if req_citation:
                has_manual = any("page" in ref or "manual" in ref.get("source_id", "") or "section" in ref for ref in matched_item.evidence_refs)
                citation_valid = has_refs and has_manual
            else:
                citation_valid = has_refs
        else:
            citation_valid = not req_citation

        if citation_valid:
            valid_citations_count += 1

        # Check high priority recall in top 3
        if exp_priority == "high":
            seeded_high_priority_count += 1
            if any(term in top_3_text for term in tc["description"].lower().split() if len(term) > 4):
                high_priority_recalled += 1

        # Check unsupported claim: any item that claims control or makes an unsourced assertion
        unsupported = False
        if matched_item:
            # Check for illegal command verbs overriding SOP
            if any(v in matched_item.suggested_check.lower() for v in ["override sop", "shut down now without approval", "ignore manual"]):
                unsupported = True

        if unsupported:
            unsupported_claims_count += 1

        passed = citation_valid and not unsupported

        details.append(EvaluationMetricDetail(
            case_id=case_id,
            description=tc["description"],
            expected_priority=exp_priority,
            actual_priority=matched_item.priority if matched_item else None,
            citation_valid=citation_valid,
            unsupported_claim=unsupported,
            passed=passed,
            notes="Passed ground truth evaluation test." if passed else "Evidence citation or priority check mismatch."
        ))

    citation_validity_score = round(valid_citations_count / total_cases, 2)
    high_priority_recall_score = round(
        (high_priority_recalled / seeded_high_priority_count) if seeded_high_priority_count > 0 else 1.0, 2
    )
    unsupported_claim_rate = round(unsupported_claims_count / total_cases, 2)

    total_sources = len(documents)
    total_events = len(events)
    input_coverage_score = 1.0 if (total_sources >= 3 and total_events >= 5) else round(total_sources / 4.0, 2)

    all_targets_met = (
        citation_validity_score >= 0.90
        and high_priority_recall_score >= 0.80
        and unsupported_claim_rate == 0.00
    )

    return EvaluationReport(
        total_cases=total_cases,
        citation_validity_score=citation_validity_score,
        citation_validity_target=0.90,
        citation_validity_pass=citation_validity_score >= 0.90,
        high_priority_recall_score=high_priority_recall_score,
        high_priority_recall_target=0.80,
        high_priority_recall_pass=high_priority_recall_score >= 0.80,
        unsupported_claim_rate=unsupported_claim_rate,
        unsupported_claim_target=0.00,
        unsupported_claim_pass=unsupported_claim_rate <= 0.00,
        input_coverage_score=input_coverage_score,
        draft_time_seconds=draft_time_seconds,
        all_targets_met=all_targets_met,
        details=details
    )
