"""
SQLite database storage for demo sessions, sources, events, handovers, and items.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from app.config import settings
from app.models.schemas import (
    Asset, SourceDocument, Event, Handover, HandoverItem, ManualPassage, IngestionJob
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            timezone TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            baseline_json TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_documents (
            source_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            raw_content TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            confidence REAL NOT NULL,
            priority_signals_json TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS manual_passages (
            passage_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            section TEXT NOT NULL,
            page INTEGER NOT NULL,
            content TEXT NOT NULL,
            keywords_json TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handovers (
            handover_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            window_start TEXT NOT NULL,
            window_end TEXT NOT NULL,
            previous_window_start TEXT,
            previous_window_end TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            coverage_json TEXT NOT NULL,
            unresolved_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handover_items (
            item_id TEXT PRIMARY KEY,
            handover_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            priority_score REAL NOT NULL,
            priority_factors_json TEXT NOT NULL,
            what_changed TEXT NOT NULL,
            suggested_check TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL,
            uncertainty TEXT,
            human_review_required INTEGER NOT NULL,
            status TEXT NOT NULL,
            assigned_to TEXT,
            operator_notes TEXT,
            edited_by_user INTEGER NOT NULL,
            FOREIGN KEY (handover_id) REFERENCES handovers(handover_id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_jobs (
            job_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            status TEXT NOT NULL,
            events_extracted INTEGER NOT NULL,
            errors_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()


# Asset Operations
def upsert_asset(asset: Asset):
    with get_connection() as conn:
        conn.execute("""
        INSERT INTO assets (asset_id, display_name, timezone, signals_json, baseline_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            display_name = excluded.display_name,
            timezone = excluded.timezone,
            signals_json = excluded.signals_json,
            baseline_json = excluded.baseline_json
        """, (
            asset.asset_id,
            asset.display_name,
            asset.timezone,
            json.dumps(asset.signals),
            json.dumps(asset.baseline_metrics)
        ))
        conn.commit()


def get_assets() -> List[Asset]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM assets").fetchall()
        return [
            Asset(
                asset_id=r["asset_id"],
                display_name=r["display_name"],
                timezone=r["timezone"],
                signals=json.loads(r["signals_json"]),
                baseline_metrics=json.loads(r["baseline_json"])
            )
            for r in rows
        ]


def get_asset(asset_id: str) -> Optional[Asset]:
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if not r:
            return None
        return Asset(
            asset_id=r["asset_id"],
            display_name=r["display_name"],
            timezone=r["timezone"],
            signals=json.loads(r["signals_json"]),
            baseline_metrics=json.loads(r["baseline_json"])
        )


# Source Document Operations
def save_source_document(doc: SourceDocument):
    with get_connection() as conn:
        conn.execute("""
        INSERT INTO source_documents (
            source_id, asset_id, kind, filename, content_hash, captured_at, metadata_json, raw_content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            filename = excluded.filename,
            captured_at = excluded.captured_at,
            metadata_json = excluded.metadata_json,
            raw_content = excluded.raw_content
        """, (
            doc.source_id,
            doc.asset_id,
            doc.kind,
            doc.filename,
            doc.content_hash,
            doc.captured_at,
            json.dumps(doc.metadata),
            doc.raw_content
        ))
        conn.commit()


def get_source_documents(asset_id: Optional[str] = None) -> List[SourceDocument]:
    with get_connection() as conn:
        if asset_id:
            rows = conn.execute("SELECT * FROM source_documents WHERE asset_id = ? ORDER BY captured_at ASC", (asset_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM source_documents ORDER BY captured_at ASC").fetchall()
        return [
            SourceDocument(
                source_id=r["source_id"],
                asset_id=r["asset_id"],
                kind=r["kind"],
                filename=r["filename"],
                content_hash=r["content_hash"],
                captured_at=r["captured_at"],
                metadata=json.loads(r["metadata_json"]),
                raw_content=r["raw_content"]
            )
            for r in rows
        ]


def get_source_document(source_id: str) -> Optional[SourceDocument]:
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM source_documents WHERE source_id = ?", (source_id,)).fetchone()
        if not r:
            return None
        return SourceDocument(
            source_id=r["source_id"],
            asset_id=r["asset_id"],
            kind=r["kind"],
            filename=r["filename"],
            content_hash=r["content_hash"],
            captured_at=r["captured_at"],
            metadata=json.loads(r["metadata_json"]),
            raw_content=r["raw_content"]
        )


# Event Operations
def save_events(events: List[Event]):
    with get_connection() as conn:
        for evt in events:
            conn.execute("""
            INSERT INTO events (
                event_id, asset_id, occurred_at, event_type, summary, signals_json,
                source_refs_json, confidence, priority_signals_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                occurred_at = excluded.occurred_at,
                summary = excluded.summary,
                signals_json = excluded.signals_json,
                source_refs_json = excluded.source_refs_json,
                confidence = excluded.confidence,
                priority_signals_json = excluded.priority_signals_json
            """, (
                evt.event_id,
                evt.asset_id,
                evt.occurred_at,
                evt.event_type,
                evt.summary,
                json.dumps([s.model_dump() for s in evt.signals]),
                json.dumps([ref.model_dump() for ref in evt.source_refs]),
                evt.confidence,
                json.dumps(evt.priority_signals)
            ))
        conn.commit()


def get_events(asset_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Event]:
    with get_connection() as conn:
        query = "SELECT * FROM events WHERE asset_id = ?"
        params: List[Any] = [asset_id]
        if start_time:
            query += " AND occurred_at >= ?"
            params.append(start_time)
        if end_time:
            query += " AND occurred_at <= ?"
            params.append(end_time)
        query += " ORDER BY occurred_at ASC"

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            result.append(Event(
                event_id=r["event_id"],
                asset_id=r["asset_id"],
                occurred_at=r["occurred_at"],
                event_type=r["event_type"],
                summary=r["summary"],
                signals=json.loads(r["signals_json"]),
                source_refs=json.loads(r["source_refs_json"]),
                confidence=r["confidence"],
                priority_signals=json.loads(r["priority_signals_json"])
            ))
        return result


# Manual Passages
def save_manual_passages(passages: List[ManualPassage]):
    with get_connection() as conn:
        for p in passages:
            conn.execute("""
            INSERT INTO manual_passages (
                passage_id, source_id, title, section, page, content, keywords_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(passage_id) DO UPDATE SET
                content = excluded.content,
                keywords_json = excluded.keywords_json
            """, (
                p.passage_id,
                p.source_id,
                p.title,
                p.section,
                p.page,
                p.content,
                json.dumps(p.keywords)
            ))
        conn.commit()


def get_manual_passages(source_id: Optional[str] = None) -> List[ManualPassage]:
    with get_connection() as conn:
        if source_id:
            rows = conn.execute("SELECT * FROM manual_passages WHERE source_id = ? ORDER BY page ASC, section ASC", (source_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM manual_passages ORDER BY page ASC, section ASC").fetchall()
        return [
            ManualPassage(
                passage_id=r["passage_id"],
                source_id=r["source_id"],
                title=r["title"],
                section=r["section"],
                page=r["page"],
                content=r["content"],
                keywords=json.loads(r["keywords_json"])
            )
            for r in rows
        ]


# Handover Operations
def save_handover(handover: Handover):
    with get_connection() as conn:
        conn.execute("""
        INSERT INTO handovers (
            handover_id, asset_id, shift_name, window_start, window_end,
            previous_window_start, previous_window_end, created_at, status,
            coverage_json, unresolved_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(handover_id) DO UPDATE SET
            status = excluded.status,
            coverage_json = excluded.coverage_json,
            unresolved_json = excluded.unresolved_json,
            metadata_json = excluded.metadata_json
        """, (
            handover.handover_id,
            handover.asset_id,
            handover.shift_name,
            handover.window_start,
            handover.window_end,
            handover.previous_window_start,
            handover.previous_window_end,
            handover.created_at,
            handover.status,
            json.dumps(handover.coverage_summary),
            json.dumps(handover.unresolved_questions),
            json.dumps(handover.generation_metadata)
        ))

        # Save items
        for item in handover.items:
            conn.execute("""
            INSERT INTO handover_items (
                item_id, handover_id, priority, priority_score, priority_factors_json,
                what_changed, suggested_check, evidence_refs_json, uncertainty,
                human_review_required, status, assigned_to, operator_notes, edited_by_user
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                priority = excluded.priority,
                priority_score = excluded.priority_score,
                priority_factors_json = excluded.priority_factors_json,
                what_changed = excluded.what_changed,
                suggested_check = excluded.suggested_check,
                evidence_refs_json = excluded.evidence_refs_json,
                uncertainty = excluded.uncertainty,
                human_review_required = excluded.human_review_required,
                status = excluded.status,
                assigned_to = excluded.assigned_to,
                operator_notes = excluded.operator_notes,
                edited_by_user = excluded.edited_by_user
            """, (
                item.item_id,
                handover.handover_id,
                item.priority,
                item.priority_score,
                json.dumps(item.priority_factors),
                item.what_changed,
                item.suggested_check,
                json.dumps(item.evidence_refs),
                item.uncertainty,
                1 if item.human_review_required else 0,
                item.status,
                item.assigned_to,
                item.operator_notes,
                1 if item.edited_by_user else 0
            ))
        conn.commit()


def get_latest_handover(asset_id: str = "press-07") -> Optional[Handover]:
    with get_connection() as conn:
        r = conn.execute("SELECT handover_id FROM handovers WHERE asset_id = ? ORDER BY created_at DESC LIMIT 1", (asset_id,)).fetchone()
        if not r:
            return None
        return get_handover(r["handover_id"])


def get_handover(handover_id: str) -> Optional[Handover]:
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM handovers WHERE handover_id = ?", (handover_id,)).fetchone()
        if not r:
            return None
        
        item_rows = conn.execute("SELECT * FROM handover_items WHERE handover_id = ? ORDER BY priority_score DESC", (handover_id,)).fetchall()
        items = [
            HandoverItem(
                item_id=ir["item_id"],
                priority=ir["priority"],
                priority_score=ir["priority_score"],
                priority_factors=json.loads(ir["priority_factors_json"]),
                what_changed=ir["what_changed"],
                suggested_check=ir["suggested_check"],
                evidence_refs=json.loads(ir["evidence_refs_json"]),
                uncertainty=ir["uncertainty"],
                human_review_required=bool(ir["human_review_required"]),
                status=ir["status"],
                assigned_to=ir["assigned_to"],
                operator_notes=ir["operator_notes"],
                edited_by_user=bool(ir["edited_by_user"])
            )
            for ir in item_rows
        ]

        return Handover(
            handover_id=r["handover_id"],
            asset_id=r["asset_id"],
            shift_name=r["shift_name"],
            window_start=r["window_start"],
            window_end=r["window_end"],
            previous_window_start=r["previous_window_start"],
            previous_window_end=r["previous_window_end"],
            created_at=r["created_at"],
            status=r["status"],
            coverage_summary=json.loads(r["coverage_json"]),
            items=items,
            unresolved_questions=json.loads(r["unresolved_json"]),
            generation_metadata=json.loads(r["metadata_json"])
        )


def update_handover_item(handover_id: str, item_id: str, update_dict: Dict[str, Any]) -> Optional[HandoverItem]:
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM handover_items WHERE handover_id = ? AND item_id = ?", (handover_id, item_id)).fetchone()
        if not r:
            return None
        
        current = dict(r)
        new_priority = update_dict.get("priority", current["priority"])
        new_what_changed = update_dict.get("what_changed", current["what_changed"])
        new_suggested_check = update_dict.get("suggested_check", current["suggested_check"])
        new_uncertainty = update_dict.get("uncertainty", current["uncertainty"])
        new_status = update_dict.get("status", current["status"])
        new_assigned_to = update_dict.get("assigned_to", current["assigned_to"])
        new_operator_notes = update_dict.get("operator_notes", current["operator_notes"])

        conn.execute("""
        UPDATE handover_items SET
            priority = ?,
            what_changed = ?,
            suggested_check = ?,
            uncertainty = ?,
            status = ?,
            assigned_to = ?,
            operator_notes = ?,
            edited_by_user = 1
        WHERE handover_id = ? AND item_id = ?
        """, (
            new_priority,
            new_what_changed,
            new_suggested_check,
            new_uncertainty,
            new_status,
            new_assigned_to,
            new_operator_notes,
            handover_id,
            item_id
        ))
        conn.commit()

        updated_row = conn.execute("SELECT * FROM handover_items WHERE handover_id = ? AND item_id = ?", (handover_id, item_id)).fetchone()
        return HandoverItem(
            item_id=updated_row["item_id"],
            priority=updated_row["priority"],
            priority_score=updated_row["priority_score"],
            priority_factors=json.loads(updated_row["priority_factors_json"]),
            what_changed=updated_row["what_changed"],
            suggested_check=updated_row["suggested_check"],
            evidence_refs=json.loads(updated_row["evidence_refs_json"]),
            uncertainty=updated_row["uncertainty"],
            human_review_required=bool(updated_row["human_review_required"]),
            status=updated_row["status"],
            assigned_to=updated_row["assigned_to"],
            operator_notes=updated_row["operator_notes"],
            edited_by_user=bool(updated_row["edited_by_user"])
        )


def reset_demo_session():
    """Wipes all session documents, events, handovers, and items, re-initializing default tables."""
    with get_connection() as conn:
        conn.execute("DELETE FROM handover_items")
        conn.execute("DELETE FROM handovers")
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM manual_passages")
        conn.execute("DELETE FROM source_documents")
        conn.execute("DELETE FROM ingestion_jobs")
        conn.commit()
