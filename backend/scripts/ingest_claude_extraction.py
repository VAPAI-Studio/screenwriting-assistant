"""Ingest a Claude-authored knowledge extraction into the book library.

The books roadmap's "Claude as extractor" path: instead of paying per-chapter
LLM calls in book_processing_service, Claude (in a Claude Code session) reads
the book — even visually, for PDFs with broken text layers — and produces one
JSON file with the full extraction. This script persists it EXACTLY like
book_processing_service does (same tables, same fields, same quality filter),
computing only the embeddings (OpenAI, cents per book).

Run INSIDE the backend container (docker network + OPENAI_API_KEY):
    docker cp extraction.json screenwriting-assistant-backend-1:/tmp/
    docker exec screenwriting-assistant-backend-1 \
        python scripts/ingest_claude_extraction.py /tmp/extraction.json

Input JSON schema:
{
  "title": str, "author": str, "filename": str, "file_type": "pdf|epub|txt",
  "chapters_total": int,
  "concepts": [{name, definition, chapter_source?, page_range?, examples?,
                actionable_questions?, section_relevance?, tags?, quality_score}],
  "relationships": [{source, target, type, description?}],
  "snippets": [{content, concept_name?, justification?, chapter_title?}],
  "chunks": [{content, chapter_title?, page_number?}]        # optional
}

Re-running with the same title replaces the previous ingestion (delete+insert).
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models.database import (
    Book, BookChunk, BookStatus, Concept, ConceptRelationship,
    RelationshipType, Snippet,
)
from app.services.embedding_service import embedding_service

OWNER_ID = "12345678-1234-5678-1234-567812345678"
QUALITY_THRESHOLD = 0.5


async def ingest(path: str) -> None:
    with open(path) as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Replace any previous ingestion of the same title (cascade wipes
        # chunks/concepts/relationships/snippets).
        prev = db.query(Book).filter(
            Book.owner_id == OWNER_ID, Book.title == data["title"]
        ).first()
        if prev:
            print(f"— reemplazando ingesta previa de '{data['title']}'")
            db.delete(prev)
            db.commit()

        concepts = [
            c for c in data.get("concepts", [])
            if c.get("quality_score", QUALITY_THRESHOLD) >= QUALITY_THRESHOLD
        ]
        dropped = len(data.get("concepts", [])) - len(concepts)
        if dropped:
            print(f"— quality filter: descartados {dropped} conceptos < {QUALITY_THRESHOLD}")

        book = Book(
            owner_id=OWNER_ID,
            title=data["title"],
            author=data.get("author"),
            filename=data.get("filename", f"{data['title']}.{data.get('file_type', 'pdf')}"),
            file_type=data.get("file_type", "pdf"),
            file_size_bytes=data.get("file_size_bytes", 0),
            status=BookStatus.COMPLETED,
            processing_step="Complete (Claude extraction)",
            progress=100,
            chapters_total=data.get("chapters_total", 0),
            chapters_processed=data.get("chapters_total", 0),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(book)
        db.flush()

        # ── Chunks (optional) ──
        db_chunks = []
        chunks = data.get("chunks") or []
        if chunks:
            chunk_embeddings = await embedding_service.embed_batch(
                [c["content"] for c in chunks]
            )
            for i, (c, emb) in enumerate(zip(chunks, chunk_embeddings)):
                db_chunk = BookChunk(
                    book_id=book.id,
                    content=c["content"],
                    token_count=len(c["content"].split()),
                    chunk_index=i,
                    chapter_title=c.get("chapter_title"),
                    page_number=c.get("page_number"),
                    embedding=emb,
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)
        book.total_chunks = len(db_chunks)

        # ── Concepts ──
        concept_embeddings = await embedding_service.embed_batch(
            [c["definition"] for c in concepts]
        ) if concepts else []
        by_name = {}
        for c, emb in zip(concepts, concept_embeddings):
            db_concept = Concept(
                book_id=book.id,
                name=c["name"],
                definition=c["definition"],
                chapter_source=c.get("chapter_source"),
                page_range=c.get("page_range"),
                examples=c.get("examples", []),
                actionable_questions=c.get("actionable_questions", []),
                section_relevance=c.get("section_relevance", {}),
                tags=c.get("tags", []),
                quality_score=c.get("quality_score"),
                embedding=emb,
            )
            db.add(db_concept)
            db.flush()
            by_name[c["name"]] = db_concept

        # ── Relationships ──
        kept_rels = 0
        for r in data.get("relationships", []):
            source, target = by_name.get(r["source"]), by_name.get(r["target"])
            if not (source and target):
                continue
            try:
                rel_type = RelationshipType(r.get("type", "related_to"))
            except ValueError:
                rel_type = RelationshipType.RELATED_TO
            db.add(ConceptRelationship(
                source_concept_id=source.id,
                target_concept_id=target.id,
                relationship=rel_type,
                description=r.get("description"),
            ))
            kept_rels += 1

        # ── Snippets ──
        snippets = data.get("snippets") or []
        if snippets:
            snippet_embeddings = await embedding_service.embed_batch(
                [s["content"] for s in snippets]
            )
            for s, emb in zip(snippets, snippet_embeddings):
                concept_db = by_name.get(s.get("concept_name"))
                db.add(Snippet(
                    book_id=book.id,
                    chapter_title=s.get("chapter_title"),
                    content=s["content"],
                    justification=s.get("justification"),
                    concept_ids=[str(concept_db.id)] if concept_db else [],
                    concept_names=[concept_db.name] if concept_db else [],
                    token_count=len(s["content"].split()),
                    embedding=emb,
                ))

        # ── Link chunks ↔ concepts (name-in-text, same as the pipeline) ──
        for db_chunk in db_chunks:
            lower = db_chunk.content.lower()
            linked = [str(c.id) for n, c in by_name.items() if n.lower() in lower]
            if linked:
                db_chunk.concept_ids = linked

        book.total_concepts = len(concepts)
        db.commit()
        print(
            f"✔ '{book.title}': {len(concepts)} conceptos, {kept_rels} relaciones, "
            f"{len(snippets)} snippets, {len(db_chunks)} chunks"
        )
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(ingest(sys.argv[1]))
