"""Socratic "hard questions" service.

Generates one book + script-grounded hard question per project at a time. Lazy
regeneration: a new question is only generated when the section is opened AND
either there is no question yet, or the last one was answered >= COOLDOWN_HOURS ago.
A still-unanswered question is never replaced. Answers are persisted and fed back
into the project context (see socratic_answers_context).

Reuses, no new infra:
- rag_service.semantic_search (global library) -> book concepts + chunks
- the project-context builder from the wizards endpoint -> the script summary
- chat_completion -> the question itself
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models import database
from .ai_provider import chat_completion
from .rag_service import rag_service

logger = logging.getLogger(__name__)

COOLDOWN_HOURS = 3
# How many recent book concepts/chunks to ground the question in.
TOP_K_CONCEPTS = 6
TOP_K_CHUNKS = 4
# How many prior answers to fold back into the project context (token-bounded).
ANSWERS_IN_CONTEXT = 8

_SYSTEM_PROMPT = """You are a sharp, generous screenwriting mentor in the Socratic tradition.
Given the writer's SCRIPT CONTEXT and grounding EXCERPTS/CONCEPTS from craft books they
have loaded, ask exactly ONE hard, specific question that will unblock or deepen THIS
script. The question must:
- be answerable only by thinking about THIS project (not generic advice),
- probe something the script has not yet resolved (fear, want vs. need, the antagonist's
  real motivation, theme, the cost of failure, what the protagonist is avoiding, etc.),
- be short (one or two sentences), provocative, and open-ended,
- NOT repeat any of the ALREADY-ASKED questions.

Respond with strict JSON only:
{"question": "...", "rationale": "one sentence on why this question matters for this script",
 "source_concepts": ["concept or book idea you drew on", "..."]}"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_pending(db: Session, project_id) -> Optional[database.SocraticQuestion]:
    """The single unanswered question for the project, if any."""
    return (
        db.query(database.SocraticQuestion)
        .filter(
            database.SocraticQuestion.project_id == str(project_id),
            database.SocraticQuestion.answer.is_(None),
        )
        .order_by(database.SocraticQuestion.created_at.desc())
        .first()
    )


def _last_answered(db: Session, project_id) -> Optional[database.SocraticQuestion]:
    return (
        db.query(database.SocraticQuestion)
        .filter(
            database.SocraticQuestion.project_id == str(project_id),
            database.SocraticQuestion.answered_at.isnot(None),
        )
        .order_by(database.SocraticQuestion.answered_at.desc())
        .first()
    )


def cooldown_remaining_seconds(db: Session, project_id) -> int:
    """Seconds left before a new question may be generated (0 if ready)."""
    last = _last_answered(db, project_id)
    if not last or not last.answered_at:
        return 0
    answered = last.answered_at
    if answered.tzinfo is None:
        answered = answered.replace(tzinfo=timezone.utc)
    ready_at = answered + timedelta(hours=COOLDOWN_HOURS)
    remaining = (ready_at - _now()).total_seconds()
    return max(0, int(remaining))


def _prior_questions(db: Session, project_id) -> list[str]:
    rows = (
        db.query(database.SocraticQuestion.question)
        .filter(database.SocraticQuestion.project_id == str(project_id))
        .order_by(database.SocraticQuestion.created_at.desc())
        .limit(40)
        .all()
    )
    return [r[0] for r in rows]


def socratic_answers_context(db: Session, project_id) -> Optional[str]:
    """A context block of the author's answered hard questions, for generation/review.

    Returned as a plain string (or None) so it can be folded into the project context
    the same way bible_context is. Bounded to the most recent ANSWERS_IN_CONTEXT.
    """
    rows = (
        db.query(database.SocraticQuestion)
        .filter(
            database.SocraticQuestion.project_id == str(project_id),
            database.SocraticQuestion.answer.isnot(None),
        )
        .order_by(database.SocraticQuestion.answered_at.desc())
        .limit(ANSWERS_IN_CONTEXT)
        .all()
    )
    if not rows:
        return None
    lines = ["## Author insights (Socratic Q&A)"]
    for r in reversed(rows):  # oldest-first reads more naturally
        ans = (r.answer or "").strip()
        if not ans:
            continue
        lines.append(f"- Q: {r.question.strip()}")
        lines.append(f"  A: {ans}")
    return "\n".join(lines) if len(lines) > 1 else None


async def generate_question(
    db: Session, project: database.Project, script_context: str
) -> database.SocraticQuestion:
    """Generate, persist and return a new hard question grounded in books + script."""
    # 1. RAG over the global book library, keyed on the current script.
    book_block = ""
    try:
        rag = await rag_service.semantic_search(
            query_text=script_context[:4000] or project.title,
            tags_filter=[],  # no tag filter -> the whole library
            db=db,
            top_k_concepts=TOP_K_CONCEPTS,
            top_k_chunks=TOP_K_CHUNKS,
        )
        parts = []
        for c in rag.get("concepts", []):
            aq = c.get("actionable_questions") or []
            parts.append(
                f"- CONCEPT: {c.get('name')} — {c.get('definition')}"
                + (f"\n  prompts: {'; '.join(aq[:3])}" if aq else "")
            )
        for ch in rag.get("chunks", []):
            parts.append(f"- EXCERPT ({ch.get('book_title')}): {ch.get('content')}")
        book_block = "\n".join(parts)
    except Exception as e:
        # Books are grounding, not a hard dependency — degrade gracefully.
        logger.warning("Socratic RAG failed for project %s: %s", project.id, e)

    prior = _prior_questions(db, project.id)
    prior_block = "\n".join(f"- {q}" for q in prior) if prior else "(none yet)"

    user_content = (
        f"SCRIPT CONTEXT:\n{script_context or '(empty script so far)'}\n\n"
        f"GROUNDING EXCERPTS/CONCEPTS FROM CRAFT BOOKS:\n{book_block or '(no books loaded)'}\n\n"
        f"ALREADY-ASKED QUESTIONS (do not repeat):\n{prior_block}"
    )

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.9,
        max_tokens=400,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        question = (data.get("question") or "").strip()
        rationale = (data.get("rationale") or "").strip() or None
        sources = data.get("source_concepts") or []
        if not isinstance(sources, list):
            sources = [str(sources)]
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat the whole response as the question.
        question = (raw or "").strip()
        rationale = None
        sources = []

    if not question:
        raise ValueError("Socratic generation produced an empty question")

    q = database.SocraticQuestion(
        project_id=str(project.id),
        question=question,
        rationale=rationale,
        source_concepts=sources,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q
