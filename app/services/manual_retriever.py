"""
Manual Chunking & Evidence Retrieval: Matches normalized events to relevant equipment manual passages.
"""

from typing import List, Dict, Any, Tuple
from app.models.schemas import ManualPassage, Event, SourceRef


def retrieve_relevant_passages(
    query_text: str,
    passages: List[ManualPassage],
    top_k: int = 3
) -> List[Tuple[ManualPassage, float]]:
    """
    Scores and returns top-k manual passages matching query terms using lexical BM25-style keyword weighting.
    """
    if not passages:
        return []

    tokens = [w.lower().strip(",.:;()") for w in query_text.split() if len(w) > 2]
    scored = []

    for passage in passages:
        score = 0.0
        content_lower = passage.content.lower()
        title_lower = passage.title.lower()
        keywords_lower = [k.lower() for k in passage.keywords]

        for token in tokens:
            # Title match (high weight)
            if token in title_lower:
                score += 3.0
            # Explicit keyword match
            if token in keywords_lower:
                score += 2.0
            # Body content frequency
            occurrences = content_lower.count(token)
            if occurrences > 0:
                score += min(occurrences * 0.5, 4.0)

        # Boost specific critical industrial keywords
        if any(t in query_text.lower() for t in ["temperature", "heat", "hot", "thermal", "overheat", "91"]):
            if "cooling" in content_lower or "temperature" in content_lower or "heat exchanger" in content_lower:
                score += 4.0

        if any(t in query_text.lower() for t in ["vibration", "spike", "cavitation", "pressure"]):
            if "vibration" in content_lower or "pressure" in content_lower or "suction" in content_lower:
                score += 4.0

        if any(t in query_text.lower() for t in ["filter", "cartridge", "oil"]):
            if "filter" in content_lower or "pm" in content_lower:
                score += 3.0

        if score > 0:
            scored.append((passage, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def find_manual_citations_for_event(
    event: Event,
    passages: List[ManualPassage]
) -> List[Dict[str, Any]]:
    """
    Finds supporting manual citations for a given event, returning structured citation references.
    """
    query = f"{event.summary} {' '.join(s.name for s in event.signals)}"
    top_matches = retrieve_relevant_passages(query, passages, top_k=2)
    citations = []

    for passage, score in top_matches:
        if score > 1.5:  # threshold
            citations.append({
                "source_id": passage.source_id,
                "locator": f"page:{passage.page}, section:{passage.section}",
                "page": passage.page,
                "section": passage.section,
                "title": passage.title,
                "snippet": passage.content[:220].strip() + "..."
            })

    return citations
