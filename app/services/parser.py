"""
Parsers for CSV/JSON machine logs, notes, and PDF/Text equipment manuals.
"""

import csv
import json
import hashlib
from typing import List, Dict, Any, Tuple, Union
from io import StringIO, BytesIO
from pypdf import PdfReader
from app.models.schemas import ManualPassage, SourceRef


def compute_sha256(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return "sha256:" + hashlib.sha256(content).hexdigest()


def parse_csv_machine_log(csv_text: str, source_id: str, default_asset_id: str = "press-07") -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses a CSV string of machine logs.
    Expected columns: timestamp, [asset_id], signal|metric|event, value, [unit]
    Returns (rows, errors)
    """
    rows = []
    errors = []
    reader = csv.DictReader(StringIO(csv_text.strip()))
    
    # Normalize headers
    if not reader.fieldnames:
        return [], ["CSV file is empty or missing headers"]

    fieldnames_map = {fn.strip().lower(): fn for fn in reader.fieldnames}
    
    time_col = None
    for candidate in ["timestamp", "time", "datetime", "occurred_at"]:
        if candidate in fieldnames_map:
            time_col = fieldnames_map[candidate]
            break
            
    signal_col = None
    for candidate in ["signal", "metric", "signal_name", "event", "tag"]:
        if candidate in fieldnames_map:
            signal_col = fieldnames_map[candidate]
            break

    val_col = None
    for candidate in ["value", "reading", "val"]:
        if candidate in fieldnames_map:
            val_col = fieldnames_map[candidate]
            break

    unit_col = fieldnames_map.get("unit")
    asset_col = fieldnames_map.get("asset_id") or fieldnames_map.get("asset")

    if not time_col or not signal_col:
        return [], [f"CSV missing mandatory columns (need timestamp and signal). Found: {list(reader.fieldnames)}"]

    for row_idx, r in enumerate(reader, start=2):  # 1 is header
        t_val = r.get(time_col, "").strip()
        s_val = r.get(signal_col, "").strip()
        v_raw = r.get(val_col, "").strip() if val_col else ""
        u_val = r.get(unit_col, "").strip() if unit_col else None
        a_val = r.get(asset_col, "").strip() if asset_col else default_asset_id

        if not t_val or not s_val:
            errors.append(f"Row {row_idx}: Missing timestamp or signal")
            continue

        try:
            numeric_val = float(v_raw) if v_raw else None
        except ValueError:
            numeric_val = None

        rows.append({
            "row_number": row_idx,
            "locator": f"row:{row_idx}",
            "asset_id": a_val or default_asset_id,
            "timestamp": t_val,
            "signal": s_val,
            "raw_value": v_raw,
            "numeric_value": numeric_val,
            "unit": u_val,
            "source_id": source_id,
            "source_ref": SourceRef(
                source_id=source_id,
                locator=f"row:{row_idx}",
                snippet=f"{t_val} | {s_val} = {v_raw} {u_val or ''}".strip()
            )
        })

    return rows, errors


def parse_json_machine_log(json_text: str, source_id: str, default_asset_id: str = "press-07") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parses JSON array of log records."""
    rows = []
    errors = []
    try:
        data = json.loads(json_text)
    except Exception as e:
        return [], [f"Invalid JSON format: {str(e)}"]

    if isinstance(data, dict):
        if "events" in data and isinstance(data["events"], list):
            data = data["events"]
        elif "logs" in data and isinstance(data["logs"], list):
            data = data["logs"]
        else:
            data = [data]

    if not isinstance(data, list):
        return [], ["JSON must contain an array of log records"]

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        t_val = item.get("timestamp") or item.get("occurred_at") or item.get("time", "")
        s_val = item.get("signal") or item.get("metric") or item.get("event", "")
        v_val = item.get("value") or item.get("reading")
        u_val = item.get("unit")
        a_val = item.get("asset_id") or default_asset_id

        try:
            num_val = float(v_val) if v_val is not None else None
        except (ValueError, TypeError):
            num_val = None

        rows.append({
            "row_number": idx,
            "locator": f"item:{idx}",
            "asset_id": a_val,
            "timestamp": str(t_val),
            "signal": str(s_val),
            "raw_value": str(v_val) if v_val is not None else "",
            "numeric_value": num_val,
            "unit": u_val,
            "source_id": source_id,
            "source_ref": SourceRef(
                source_id=source_id,
                locator=f"item:{idx}",
                snippet=f"{t_val} | {s_val} = {v_val} {u_val or ''}".strip()
            )
        })

    return rows, errors


def parse_maintenance_notes(text: str, source_id: str, default_asset_id: str = "press-07") -> List[Dict[str, Any]]:
    """
    Parses maintenance notes text or markdown into distinct observation blocks.
    Preserves line/block locators.
    """
    blocks = []
    lines = text.strip().split("\n")
    current_block = []
    current_start_line = 1

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            if current_block:
                block_text = "\n".join(current_block)
                blocks.append({
                    "locator": f"lines:{current_start_line}-{line_idx-1}",
                    "text": block_text,
                    "source_id": source_id,
                    "asset_id": default_asset_id,
                    "source_ref": SourceRef(
                        source_id=source_id,
                        locator=f"lines:{current_start_line}-{line_idx-1}",
                        snippet=block_text[:140]
                    )
                })
                current_block = []
            current_start_line = line_idx + 1
        else:
            current_block.append(stripped)

    if current_block:
        block_text = "\n".join(current_block)
        blocks.append({
            "locator": f"lines:{current_start_line}-{len(lines)}",
            "text": block_text,
            "source_id": source_id,
            "asset_id": default_asset_id,
            "source_ref": SourceRef(
                source_id=source_id,
                locator=f"lines:{current_start_line}-{len(lines)}",
                snippet=block_text[:140]
            )
        })

    return blocks


def parse_manual_pdf(pdf_bytes: bytes, source_id: str) -> List[ManualPassage]:
    """
    Extracts text from PDF by page, then breaks into passages by section headers.
    """
    passages = []
    reader = PdfReader(BytesIO(pdf_bytes))
    
    for page_idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        lines = [ln.strip() for ln in page_text.split("\n") if ln.strip()]
        
        current_section = f"Section {page_idx}"
        current_title = f"Manual Page {page_idx}"
        content_lines = []

        for line in lines:
            if line.startswith("Section ") or line.startswith("SECTION ") or (len(line) < 60 and line.isupper()):
                if content_lines:
                    passage_content = "\n".join(content_lines)
                    passages.append(ManualPassage(
                        passage_id=f"pass-{source_id}-p{page_idx}-{len(passages)+1}",
                        source_id=source_id,
                        title=current_title,
                        section=current_section,
                        page=page_idx,
                        content=passage_content,
                        keywords=extract_keywords(passage_content)
                    ))
                    content_lines = []
                current_section = line[:30]
                current_title = line
            else:
                content_lines.append(line)

        if content_lines:
            passage_content = "\n".join(content_lines)
            passages.append(ManualPassage(
                passage_id=f"pass-{source_id}-p{page_idx}-{len(passages)+1}",
                source_id=source_id,
                title=current_title,
                section=current_section,
                page=page_idx,
                content=passage_content,
                keywords=extract_keywords(passage_content)
            ))

    return passages


def parse_manual_markdown(md_text: str, source_id: str) -> List[ManualPassage]:
    """
    Parses Markdown manual with headings (e.g. ## Section 4.2 ...) and Page annotations.
    """
    passages = []
    lines = md_text.strip().split("\n")
    current_title = "General Manual Overview"
    current_section = "Section 1.0"
    current_page = 1
    content_lines = []

    for line in lines:
        stripped = line.strip()
        # Page indicator like <!-- Page: 14 --> or [Page 14]
        if "Page:" in stripped or "[Page " in stripped:
            import re
            m = re.search(r"Page:?\s*(\d+)", stripped)
            if m:
                current_page = int(m.group(1))

        if stripped.startswith("#"):
            if content_lines:
                text_content = "\n".join(content_lines).strip()
                if text_content:
                    passages.append(ManualPassage(
                        passage_id=f"pass-{source_id}-{len(passages)+1}",
                        source_id=source_id,
                        title=current_title,
                        section=current_section,
                        page=current_page,
                        content=text_content,
                        keywords=extract_keywords(text_content)
                    ))
                content_lines = []
            
            heading_text = stripped.lstrip("#").strip()
            current_title = heading_text
            import re
            sec_match = re.search(r"(\d+(\.\d+)*)", heading_text)
            if sec_match:
                current_section = f"Section {sec_match.group(1)}"
            else:
                current_section = heading_text[:30]
        else:
            content_lines.append(stripped)

    if content_lines:
        text_content = "\n".join(content_lines).strip()
        if text_content:
            passages.append(ManualPassage(
                passage_id=f"pass-{source_id}-{len(passages)+1}",
                source_id=source_id,
                title=current_title,
                section=current_section,
                page=current_page,
                content=text_content,
                keywords=extract_keywords(text_content)
            ))

    return passages


def extract_keywords(text: str) -> List[str]:
    """Extracts informative domain keywords from technical manual text."""
    stop_words = {
        "the", "and", "or", "to", "in", "a", "of", "for", "with", "is", "are",
        "on", "at", "by", "an", "be", "this", "that", "which", "as", "from"
    }
    words = []
    for w in text.lower().replace(",", " ").replace(".", " ").replace(":", " ").replace(";", " ").split():
        clean = "".join(ch for ch in w if ch.isalnum() or ch == "-")
        if len(clean) > 3 and clean not in stop_words and not clean.isdigit():
            words.append(clean)
    return list(set(words))
