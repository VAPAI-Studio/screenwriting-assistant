"""Craft doctrine for the generation pipeline (Phase 2 of the books roadmap).

Selects book concepts relevant to a project's FORMAT (via concept tags) and
formats them as compact prompt blocks for the critique/rewrite/polish loop in
template_ai_service. Selection is tag-based and deterministic — no embeddings,
no extra LLM calls — so it adds no latency and no external dependency to a
generation run.

Data flow: the wizard background task (which has a DB session) calls
build_doctrine_cards() once per run and stows the result in
config["_doctrine_cards"]; template_ai_service formats blocks from those cards
with the pure helpers below. Any failure here degrades to "no doctrine" — the
generation pipeline must never abort because the book library is missing.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from ..config import settings

logger = logging.getLogger(__name__)

# Template -> concept format tag. Until templates carry an explicit `format`
# field (Phase 3), this mapping is the routing key from a project's template to
# the book concepts extracted with that tag.
TEMPLATE_FORMAT_TAGS = {
    "short_movie": "short_film",
}

# Critique rubric axis -> concept tags that teach that dimension. Used to give
# the rewrite pass only the theory that attacks its flagged weaknesses.
AXIS_TAGS = {
    "subtext": ["subtext", "dialogue"],
    "scene_turn": ["scene_design", "structure"],
    "escalation": ["conflict", "pacing"],
    "voice_distinction": ["character", "dialogue"],
    "tone_identity": ["tone", "genre"],
}


def format_tag_for_template(template_id: str) -> Optional[str]:
    return TEMPLATE_FORMAT_TAGS.get(template_id)


def build_doctrine_cards(
    template_id: str,
    db: Session,
    max_concepts: Optional[int] = None,
) -> List[Dict]:
    """Select the format's top concepts as JSON-serializable doctrine cards.

    Ordered by: has actionable questions first, then quality_score. Only
    concepts from COMPLETED books in the global library carrying the format
    tag. Each card: {name, definition, questions, tags, source, quote?}.
    Returns [] on any failure or when the library has nothing for this format.
    """
    format_tag = format_tag_for_template(template_id)
    if not format_tag:
        return []
    max_concepts = max_concepts or settings.DOCTRINE_MAX_CONCEPTS

    try:
        rows = db.execute(
            sql_text("""
                SELECT c.name, c.definition, c.actionable_questions, c.tags,
                       b.title AS book_title, b.author AS book_author
                FROM concepts c
                JOIN books b ON c.book_id = b.id
                WHERE b.status = 'completed'
                  AND c.tags ? :format_tag
                  AND (c.quality_score IS NULL OR c.quality_score >= 0.5)
                ORDER BY (jsonb_array_length(COALESCE(c.actionable_questions, '[]'::jsonb)) > 0) DESC,
                         c.quality_score DESC NULLS LAST
                LIMIT :top_k
            """),
            {"format_tag": format_tag, "top_k": max_concepts},
        ).fetchall()

        cards = []
        for row in rows:
            author = (row.book_author or "").strip()
            source = f"{row.book_title} ({author})" if author else row.book_title
            cards.append({
                "name": row.name,
                "definition": row.definition,
                "questions": (row.actionable_questions or [])[:3],
                "tags": row.tags or [],
                "source": source,
            })

        _attach_quotes(cards, db)
        return cards
    except Exception as e:
        logger.warning(f"Doctrine lookup failed (tag={format_tag}): {e}")
        return []


def _attach_quotes(cards: List[Dict], db: Session) -> None:
    """Attach a verbatim book snippet to up to 2 of the top cards (in place)."""
    if not cards:
        return
    try:
        names = [c["name"] for c in cards]
        rows = db.execute(
            sql_text("""
                SELECT s.content, s.concept_names
                FROM snippets s
                WHERE s.concept_names ?| :names
                  AND length(s.content) BETWEEN 200 AND 1200
                LIMIT 6
            """),
            {"names": names},
        ).fetchall()

        attached = 0
        for row in rows:
            if attached >= 2:
                break
            for card in cards:
                if card["name"] in (row.concept_names or []) and "quote" not in card:
                    card["quote"] = row.content.strip()
                    attached += 1
                    break
    except Exception as e:
        logger.warning(f"Doctrine snippet lookup failed: {e}")


def select_for_axes(cards: List[Dict], weak_axes: List[str]) -> List[Dict]:
    """Cards whose tags teach the flagged rubric axes; all cards if none match."""
    wanted = {tag for axis in weak_axes for tag in AXIS_TAGS.get(axis, [])}
    if not wanted:
        return cards
    matched = [c for c in cards if wanted.intersection(c.get("tags") or [])]
    return matched or cards


def format_block(cards: List[Dict], max_chars: Optional[int] = None) -> str:
    """Render doctrine cards as a compact prompt block ('' when no cards).

    Kept terse on purpose: name + definition + up to 3 checklist questions per
    concept, plus at most 2 verbatim quotes, hard-capped at max_chars so the
    doctrine can never crowd out the scene itself.
    """
    if not cards:
        return ""
    max_chars = max_chars or settings.DOCTRINE_MAX_CHARS

    parts = []
    for card in cards:
        lines = [f"### {card['name']}  [{card['source']}]", card["definition"].strip()]
        for q in card.get("questions") or []:
            lines.append(f"- Check: {q}")
        if card.get("quote"):
            lines.append(f'> "{card["quote"]}"')
        entry = "\n".join(lines)
        # Always keep at least one card; cap only the trailing ones.
        if parts and sum(len(p) for p in parts) + len(entry) > max_chars:
            break
        parts.append(entry)

    return "\n\n".join(parts)


def critique_block(cards: List[Dict]) -> str:
    """Doctrine block for the critique prompt."""
    body = format_block(cards)
    if not body:
        return ""
    return (
        "## Craft doctrine (from this format's canon — use it to ground your notes)\n"
        "When a weakness maps to one of these principles, NAME the concept in your note "
        "and apply its check questions to the scene.\n\n" + body + "\n\n"
    )


def rewrite_block(cards: List[Dict], weak_axes: List[str]) -> str:
    """Doctrine block for the rewrite prompt, narrowed to the weak axes."""
    body = format_block(select_for_axes(cards, weak_axes))
    if not body:
        return ""
    return (
        "## Craft doctrine for the flagged weaknesses (apply while rewriting)\n\n"
        + body + "\n\n"
    )


def polish_block(cards: List[Dict]) -> str:
    """Doctrine block for the whole-screenplay polish pass (structure/pacing)."""
    body = format_block(select_for_axes(cards, ["scene_turn", "escalation"])[:5])
    if not body:
        return ""
    return "## Craft doctrine (structure and pacing canon for this format)\n\n" + body + "\n\n"
