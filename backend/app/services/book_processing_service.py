import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import Book, BookChunk, BookStatus, Concept, ConceptRelationship, RelationshipType
from .document_service import document_service
from .embedding_service import embedding_service
from .knowledge_extraction_service import knowledge_extraction_service

logger = logging.getLogger(__name__)


class BookProcessingService:
    """Orchestrates the full book processing pipeline:
    1. Extract text from document
    2. Create raw chunks + embeddings (for RAG citations)
    3. Extract knowledge graph via GPT-4 (concepts + relationships)
    4. Generate concept embeddings
    5. Link chunks to concepts
    """

    async def process_book(self, book_id: UUID, file_path: str, db: Session) -> None:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            logger.error(f"Book {book_id} not found")
            return

        try:
            # ── Step 1: Extract text ──
            self._update_status(book, BookStatus.EXTRACTING, "Extracting text from document", db)
            pages = document_service.extract_text(file_path, book.file_type)

            if not pages:
                raise ValueError("No text could be extracted from the document")

            logger.info(f"Extracted {len(pages)} pages/sections from {book.filename}")

            # ── Step 2: Create raw chunks + embeddings ──
            self._update_status(book, BookStatus.EMBEDDING, "Creating text chunks and embeddings", db)

            chunks = document_service.chunk_text(pages)
            logger.info(f"Created {len(chunks)} chunks")

            chunk_texts = [c.content for c in chunks]
            chunk_embeddings = await embedding_service.embed_batch(chunk_texts)

            db_chunks = []
            for chunk, emb in zip(chunks, chunk_embeddings):
                db_chunk = BookChunk(
                    book_id=book_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding=emb,
                    chapter_title=chunk.chapter_title,
                    page_number=chunk.page_number,
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)

            book.total_chunks = len(chunks)
            db.commit()

            # ── Step 3: Extract knowledge graph ──
            self._update_status(book, BookStatus.ANALYZING, "Extracting knowledge graph with GPT-4", db)

            chapters = document_service.split_into_chapters(pages)
            logger.info(f"Processing {len(chapters)} chapters for knowledge extraction")

            all_concepts = []
            all_relationships = []

            for chapter in chapters:
                chapter_result = await knowledge_extraction_service.process_chapter(
                    chapter_text=chapter["text"],
                    chapter_title=chapter.get("title", "Untitled"),
                    book_title=book.title,
                )
                all_concepts.extend(chapter_result.get("concepts", []))
                all_relationships.extend(chapter_result.get("relationships", []))

                # Update progress
                book.processing_step = f"Analyzed {len(all_concepts)} concepts so far"
                db.commit()

            logger.info(f"Extracted {len(all_concepts)} concepts, {len(all_relationships)} relationships")

            # ── Step 4: Store concepts + generate concept embeddings ──
            self._update_status(book, BookStatus.EMBEDDING, "Generating concept embeddings", db)

            concept_definitions = [c["definition"] for c in all_concepts]
            concept_embeddings = await embedding_service.embed_batch(concept_definitions) if concept_definitions else []

            # Map concept names to DB objects for relationship linking
            concept_name_to_db = {}

            for concept_data, emb in zip(all_concepts, concept_embeddings):
                db_concept = Concept(
                    book_id=book_id,
                    name=concept_data["name"],
                    definition=concept_data["definition"],
                    chapter_source=concept_data.get("chapter_source"),
                    page_range=concept_data.get("page_range"),
                    examples=concept_data.get("examples", []),
                    actionable_questions=concept_data.get("actionable_questions", []),
                    section_relevance=concept_data.get("section_relevance", {}),
                    tags=concept_data.get("tags", []),
                    embedding=emb,
                )
                db.add(db_concept)
                db.flush()  # Get the ID
                concept_name_to_db[concept_data["name"]] = db_concept

            # ── Step 5: Store relationships ──
            for rel_data in all_relationships:
                source = concept_name_to_db.get(rel_data["source"])
                target = concept_name_to_db.get(rel_data["target"])
                if source and target:
                    rel_type_str = rel_data.get("type", "related_to")
                    try:
                        rel_type = RelationshipType(rel_type_str)
                    except ValueError:
                        rel_type = RelationshipType.RELATED_TO

                    db_rel = ConceptRelationship(
                        source_concept_id=source.id,
                        target_concept_id=target.id,
                        relationship=rel_type,
                        description=rel_data.get("description"),
                    )
                    db.add(db_rel)

            # ── Step 6: Link chunks to concepts ──
            # Simple heuristic: if a concept name appears in a chunk, link them
            for db_chunk in db_chunks:
                linked_ids = []
                chunk_lower = db_chunk.content.lower()
                for name, db_concept in concept_name_to_db.items():
                    if name.lower() in chunk_lower:
                        linked_ids.append(str(db_concept.id))
                if linked_ids:
                    db_chunk.concept_ids = linked_ids

            # ── Finalize ──
            book.status = BookStatus.COMPLETED
            book.total_concepts = len(all_concepts)
            book.processed_at = datetime.now(timezone.utc)
            book.processing_step = "Complete"
            db.commit()

            logger.info(
                f"Book '{book.title}' processed: "
                f"{book.total_chunks} chunks, "
                f"{book.total_concepts} concepts, "
                f"{len(all_relationships)} relationships"
            )

        except Exception as e:
            logger.error(f"Error processing book {book_id}: {e}", exc_info=True)
            book.status = BookStatus.FAILED
            book.processing_error = str(e)
            book.processing_step = "Failed"
            db.commit()

    def _update_status(self, book: Book, status: BookStatus, step: str, db: Session) -> None:
        book.status = status
        book.processing_step = step
        db.commit()
        logger.info(f"Book '{book.title}': {step}")


book_processing_service = BookProcessingService()
