# backend/app/services/breakdown_service.py

"""
Breakdown extraction service. Gathers screenplay content, character names,
and scene data from the database, then uses structured AI output to extract
production elements (characters, locations, props, wardrobe, vehicles).

Plan 11-01 establishes the skeleton: Pydantic models, context builder, and
user prompt formatter. Plan 11-02 implements the full extraction pipeline.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..models import database
from .ai_provider import chat_completion_structured

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic structured output models (passed to chat_completion_structured)
# ---------------------------------------------------------------------------

class ExtractedSceneAppearance(BaseModel):
    """A single scene where an element physically appears."""
    scene_index: int = Field(
        description="1-based index matching the scene list provided in the prompt"
    )
    context: str = Field(
        description="Brief description of how this element appears in the scene"
    )


class ExtractedElement(BaseModel):
    """A production element extracted from the screenplay."""
    category: str = Field(
        description="One of: character, location, prop, wardrobe, vehicle, set_dressing, animal, sfx, makeup_hair, extras"
    )
    canonical_name: str = Field(
        description="The standard canonical name for this element, deduplicated across scenes"
    )
    description: str = Field(
        description="Brief description of the element as it appears in the screenplay"
    )
    scene_appearances: List[ExtractedSceneAppearance] = Field(
        description="Scenes where this element physically appears on screen"
    )


class ExtractionResponse(BaseModel):
    """Complete extraction result from AI."""
    elements: List[ExtractedElement]


# ---------------------------------------------------------------------------
# Internal data-passing dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExtractionContext:
    """All data needed for an extraction AI call."""
    screenplay_texts: List[str]        # From ScreenplayContent.content
    character_names: List[str]          # From story.characters ListItem names
    scene_summaries: List[dict]        # [{id: str, summary: str, sort_order: int}]
    project_title: str
    # Phase 50 (D-50-01/BFID-02): per-scene full text keyed by 0-based scene index,
    # aligned to scene_summaries order. None/empty => _build_user_prompt falls back to
    # the concatenated form. Kept alongside screenplay_texts for the graceful fallback.
    scene_texts_by_index: Optional[Dict[int, str]] = None


# ---------------------------------------------------------------------------
# Extraction system prompt
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """You are a professional script supervisor performing a production breakdown.

Analyze the provided screenplay content and extract ALL production elements that are PHYSICALLY PRESENT ON SCREEN.

CRITICAL RULES:
1. Only extract elements that PHYSICALLY APPEAR in the scene -- visible to the camera
2. Do NOT extract elements merely mentioned in dialogue or backstory
3. Do NOT extract abstract concepts, emotions, or themes
4. Characters must actually appear in the scene (not just be talked about)
5. Props must be handled, seen, or interact with the scene (not just referenced)
6. Locations are the actual shooting locations where scenes take place

DEDUPLICATION:
- If the same element is described differently across scenes (e.g., "GUN", "revolver", ".38 Special"), use ONE canonical name
- Prefer the most specific common name (e.g., "Revolver" over "Gun")
- Characters should use their proper name, not descriptions like "the old man"

CATEGORIES:
- character: Named or significant unnamed characters who appear on screen
- location: Distinct shooting locations (INT./EXT. settings)
- prop: Physical objects handled or prominently featured
- wardrobe: Notable costume pieces or accessories
- vehicle: Cars, trucks, bikes, boats, aircraft
- set_dressing: Furniture and décor that dress a location but are not handled as a prop (couch, paintings, rugs, lamps) -- must be visible on screen
- animal: Animals appearing on screen (dogs, horses, birds) -- must be physically present, not merely mentioned
- sfx: Practical/special effects that physically occur on screen (fire, smoke, rain, explosions, breaking glass) -- only what is actually shown, never implied or off-screen
- makeup_hair: Notable makeup, hair, or prosthetics as a production element (wounds, aging, distinctive hairstyles, prosthetic appliances) -- visible on screen
- extras: Background performers or crowds visible on screen (restaurant patrons, soldiers in the background, a crowd)

PRECEDENCE FOR AMBIGUOUS CASES:
- A ridden or driven horse (or any living creature) is an animal, not a vehicle -- the living creature wins.
- set_dressing vs prop: if a character handles or the scene features the object, it is a prop; otherwise it is set_dressing."""


# ---------------------------------------------------------------------------
# BreakdownService
# ---------------------------------------------------------------------------

class BreakdownService:
    """Service for AI-driven screenplay breakdown extraction."""

    def _build_extraction_context(
        self, db: Session, project_id: UUID
    ) -> ExtractionContext:
        """
        Gather all data needed for extraction from the database.

        Queries:
        - ScreenplayContent records for screenplay text
        - PhaseData(phase=story, subsection_key=characters) -> ListItem names
        - PhaseData(phase=scenes, subsection_key=scene_list) -> ListItem summaries
        - Project for title
        """
        # 1. Fetch screenplay content. Phase 50 (D-50-01): order deterministically
        # (newest-first) so per-scene alignment and the concatenated fallback are
        # both stable across runs. Mirrors wizards.py:keep_scene_version (484-488).
        screenplays = db.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == str(project_id)
        ).order_by(
            database.ScreenplayContent.created_at.desc(),
            database.ScreenplayContent.id.desc(),
        ).all()

        # 2. Fetch character names from story.characters
        character_names = []
        chars_pd = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == str(project_id),
            database.PhaseData.phase == "story",
            database.PhaseData.subsection_key == "characters",
        ).first()
        if chars_pd:
            char_items = db.query(database.ListItem).filter(
                database.ListItem.phase_data_id == str(chars_pd.id)
            ).all()
            character_names = [
                li.content.get("name", "")
                for li in char_items
                if li.content and li.content.get("name")
            ]

        # 3. Fetch scene summaries from scenes.scene_list
        scene_summaries = []
        scenes_pd = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == str(project_id),
            database.PhaseData.phase == "scenes",
            database.PhaseData.subsection_key == "scene_list",
        ).first()
        if scenes_pd:
            scene_items = db.query(database.ListItem).filter(
                database.ListItem.phase_data_id == str(scenes_pd.id)
            ).order_by(database.ListItem.sort_order).all()
            scene_summaries = [
                {
                    "id": str(li.id),
                    "summary": li.content.get("summary", f"Scene {li.sort_order + 1}"),
                    "sort_order": li.sort_order,
                }
                for li in scene_items
            ]

        # 4. Fetch project title
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()

        # Phase 50 (D-50-01/BFID-02): attempt to align per-scene text to the scene
        # list by episode_index (positional fallback). NEVER raises; returns {} on
        # any mismatch so _build_user_prompt degrades to the concatenated form.
        scene_texts_by_index = self._align_screenplay_to_scenes(
            screenplays, scene_summaries
        )

        return ExtractionContext(
            screenplay_texts=[sc.content for sc in screenplays if sc.content],
            character_names=character_names,
            scene_summaries=scene_summaries,
            project_title=project.title if project else "",
            scene_texts_by_index=scene_texts_by_index,
        )

    def _align_screenplay_to_scenes(
        self, screenplays: List, scene_summaries: List[dict]
    ) -> Dict[int, str]:
        """
        Align ScreenplayContent rows to the scene list STRICTLY by
        formatted_content.episode_index, returning {0-based scene index -> full
        scene text}.

        Phase 50 (D-50-01): episode_index is the ONLY reliable join key (set by the
        v6.0 generation path on every row it writes). We deliberately do NOT attempt
        a positional fallback for rows that lack episode_index: the batch-generate
        path appends rows and never deletes them, and `created_at` is only
        second-resolution on some backends (SQLite), so insertion order is NOT
        reliably recoverable — a positional guess can silently REVERSE scene order
        and mis-attribute every element (caught by test
        test_legacy_positional_fallback_*). When a scene has no episode_index match
        (legacy/duplicate/ambiguous data), it is simply omitted from the mapping;
        the builder's strict full-coverage gate then drops the aligned path entirely
        and falls back to the safe concatenated form.

        On duplicate rows per episode_index, the FIRST match wins — `screenplays`
        arrives newest-first (created_at.desc, id.desc), so the most recent row for
        that scene is used (consistent with v6.0 keep-scene-version's newest-first
        preference).

        Rows with empty content are skipped. This helper NEVER raises (T-50-01
        mitigation: extraction must never crash).
        """
        mapping: Dict[int, str] = {}
        try:
            rows = list(screenplays)

            def _ep_index(r):
                return (getattr(r, "formatted_content", None) or {}).get("episode_index")

            for i in range(len(scene_summaries)):
                # First match wins; rows is newest-first so this is the most recent
                # row carrying episode_index == i. No positional fallback (unreliable).
                target = next((r for r in rows if _ep_index(r) == i), None)
                if target is None:
                    continue
                text = getattr(target, "content", None)
                if not text:
                    continue
                mapping[i] = text
        except Exception as e:  # noqa: BLE001 - alignment must never crash extraction
            logger.warning("Scene alignment failed; falling back to concatenated prompt: %s", e)
            return {}
        return mapping

    def _build_user_prompt(self, ctx: ExtractionContext) -> str:
        """
        Format extraction context into a user prompt for the AI.

        Scene indexing is 1-based (Scene 1, Scene 2, ...) so AI scene_index
        references in ExtractedSceneAppearance map directly to position.
        """
        parts = [f"# Screenplay: {ctx.project_title}\n"]

        # Known characters (helps AI match names consistently)
        if ctx.character_names:
            parts.append("## Known Characters")
            for name in ctx.character_names:
                parts.append(f"- {name}")
            parts.append("")

        # Phase 50 (D-50-01/BFID-02): take the ALIGNED per-scene path ONLY when the
        # mapping covers EVERY scene with exactly one non-empty text (strict
        # full-coverage gate). On any gap/ambiguity, fall back to the concatenated
        # form below so extraction never crashes or mis-labels (T-50-01).
        by_index = ctx.scene_texts_by_index or {}
        full_coverage = bool(ctx.scene_summaries) and all(
            by_index.get(i) for i in range(len(ctx.scene_summaries))
        )

        if full_coverage:
            # Aligned path: each scene's summary + its FULL text under its own
            # explicit 1-based header, in the SAME index space scene_appearances /
            # _map_scene_indices_to_ids use.
            parts.append(
                "## Scenes (extract elements against the scene under which their text appears)"
            )
            for i, scene in enumerate(ctx.scene_summaries):
                parts.append(f"### Scene {i + 1}: {scene['summary']}")
                parts.append(by_index[i])
                parts.append("")
            parts.append(
                "\nAttribute each element to the scene index/indices under which its "
                "text appears."
            )
            return "\n".join(parts)

        # Fallback path (UNCHANGED concatenated form): 1-based summary list + a
        # separate concatenated screenplay blob.
        parts.append("## Scenes")
        for i, scene in enumerate(ctx.scene_summaries):
            parts.append(f"Scene {i + 1}: {scene['summary']}")
        parts.append("")

        parts.append("## Screenplay Content")
        for text in ctx.screenplay_texts:
            parts.append(text)
            parts.append("---")

        parts.append("\nExtract all production elements from this screenplay.")
        return "\n".join(parts)

    async def _call_ai_extraction(self, ctx: ExtractionContext,
                                   bible_context: Optional[str] = None) -> ExtractionResponse:
        """Call AI with structured output to extract production elements."""
        user_prompt = self._build_user_prompt(ctx)
        if bible_context:
            user_prompt = f"{bible_context}\n---\n{user_prompt}"
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return await chat_completion_structured(
            messages=messages,
            response_model=ExtractionResponse,
            temperature=0.15,
            max_tokens=8000,
        )

    def _deduplicate_elements(self, elements: List[ExtractedElement]) -> List[ExtractedElement]:
        """Post-processing deduplication: merge elements with same category + case-insensitive name.

        The AI prompt instructs deduplication, but this catches any remaining duplicates.
        When duplicates found, merge scene_appearances and keep the first description.
        """
        seen: dict[tuple[str, str], ExtractedElement] = {}  # (category, name_lower) -> element
        for elem in elements:
            key = (elem.category, elem.canonical_name.lower())
            if key in seen:
                # Merge: combine scene appearances, keep first description
                existing = seen[key]
                merged_appearances = list(existing.scene_appearances)
                seen_indices = {a.scene_index for a in merged_appearances}
                for app in elem.scene_appearances:
                    if app.scene_index not in seen_indices:
                        merged_appearances.append(app)
                        seen_indices.add(app.scene_index)
                # Create new merged element
                seen[key] = ExtractedElement(
                    category=existing.category,
                    canonical_name=existing.canonical_name,
                    description=existing.description,
                    scene_appearances=merged_appearances,
                )
            else:
                seen[key] = elem
        return list(seen.values())

    def _upsert_elements(
        self, db: Session, project_id: UUID, extracted: List[ExtractedElement]
    ) -> Dict:
        """
        Upsert extracted elements into the database.

        Respects user-modified (SYNC-01) and soft-deleted (SYNC-02) elements:
        - is_deleted=True: SKIP entirely (do not resurrect)
        - user_modified=True: SKIP update but include in element_map for scene linking
        - Otherwise: UPDATE description and source
        - New elements: CREATE with source="ai"

        Returns dict with created/updated/skipped counts and element_map.
        """
        # Pre-load ALL existing elements for this project in a single query
        existing_elements = db.query(database.BreakdownElement).filter(
            database.BreakdownElement.project_id == str(project_id)
        ).all()

        # Build lookup map: (category, name_lower) -> element
        lookup: Dict[tuple, database.BreakdownElement] = {
            (el.category, el.name.lower()): el for el in existing_elements
        }

        created = 0
        updated = 0
        skipped = 0
        element_map: Dict[str, database.BreakdownElement] = {}

        for item in extracted:
            key = (item.category, item.canonical_name.lower())
            existing = lookup.get(key)

            if existing and existing.is_deleted:
                # SYNC-02: Do not resurrect soft-deleted elements
                skipped += 1
                continue

            if existing and existing.user_modified:
                # SYNC-01: Do not overwrite user-modified elements
                # But include in element_map for scene linking
                element_map[item.canonical_name] = existing
                skipped += 1
                continue

            if existing:
                # Update existing element
                existing.description = item.description
                existing.source = "ai"
                element_map[item.canonical_name] = existing
                updated += 1
            else:
                # Create new element
                new_el = database.BreakdownElement(
                    project_id=str(project_id),
                    category=item.category,
                    name=item.canonical_name,
                    description=item.description,
                    source="ai",
                )
                db.add(new_el)
                db.flush()  # Get the ID assigned
                element_map[item.canonical_name] = new_el
                created += 1

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "element_map": element_map,
        }

    def _reconcile_scene_links(
        self,
        db: Session,
        element: database.BreakdownElement,
        new_links: List[Tuple[str, str]],
    ) -> None:
        """
        Reconcile scene links for an element after extraction.

        - Delete ALL existing AI-sourced links for this element
        - Create new AI-sourced links for each (scene_id, context) pair,
          persisting the AI's per-appearance context (APPR-02 / D-51-01)
        - Preserve user-sourced links (never delete them)
        """
        # Delete all existing AI-sourced scene links for this element
        db.query(database.ElementSceneLink).filter(
            database.ElementSceneLink.element_id == str(element.id),
            database.ElementSceneLink.source == "ai",
        ).delete(synchronize_session="fetch")

        for scene_id, context in new_links:
            # Check if a user-sourced link already exists for this pair
            user_link = db.query(database.ElementSceneLink).filter(
                database.ElementSceneLink.element_id == str(element.id),
                database.ElementSceneLink.scene_item_id == str(scene_id),
                database.ElementSceneLink.source == "user",
            ).first()
            if user_link:
                continue

            link = database.ElementSceneLink(
                element_id=str(element.id),
                scene_item_id=str(scene_id),
                context=context,
                source="ai",
            )
            db.add(link)

    def _map_scene_indices_to_ids(
        self,
        ctx: ExtractionContext,
        scene_appearances: List[ExtractedSceneAppearance],
    ) -> List[Tuple[str, str]]:
        """
        Convert 1-based scene_index values from AI response to
        (ListItem ID, per-appearance context) pairs (APPR-02 / D-51-01).

        AI returns 1-based indices; scene_summaries is 0-indexed.
        Invalid indices (out of range) are skipped with a warning.

        De-duplicates by scene_id, keeping the FIRST appearance's context (IN-01):
        the AI can legitimately emit the same scene_index twice for one element,
        which would otherwise create two links for the same (element, scene) pair
        and violate the uq_element_scene unique constraint — failing the whole
        extraction transaction.
        """
        scene_links: List[Tuple[str, str]] = []
        seen_ids: set = set()
        for appearance in scene_appearances:
            zero_based = appearance.scene_index - 1
            if 0 <= zero_based < len(ctx.scene_summaries):
                scene_id = ctx.scene_summaries[zero_based]["id"]
                if scene_id in seen_ids:
                    continue  # keep first context for this scene; skip duplicate
                seen_ids.add(scene_id)
                scene_links.append((scene_id, appearance.context))
            else:
                logger.warning(
                    "Invalid scene_index %d (total scenes: %d) -- skipping",
                    appearance.scene_index,
                    len(ctx.scene_summaries),
                )
        return scene_links

    def _record_run(
        self,
        db: Session,
        project_id: UUID,
        status: str,
        result: dict,
        error: str = None,
        created: int = 0,
        updated: int = 0,
    ) -> database.BreakdownRun:
        """Create a BreakdownRun audit record."""
        run = database.BreakdownRun(
            project_id=str(project_id),
            status=status,
            config={
                "temperature": 0.15,
                "provider": settings.AI_PROVIDER,
            },
            result_summary=result,
            error_message=error,
            elements_created=created,
            elements_updated=updated,
        )
        if status in ("completed", "failed"):
            run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        return run

    async def extract(self, db: Session, project_id: UUID,
                       bible_context: Optional[str] = None) -> database.BreakdownRun:
        """
        Full extraction pipeline in a single transaction:

        1. Build context from database (screenplay text, characters, scenes)
        2. Validate context has screenplay content
        3. Call AI with structured output
        4. Upsert elements (respecting user_modified and is_deleted)
        5. Reconcile scene links for each element
        6. Record audit run
        7. Single commit for entire transaction
        """
        try:
            # 1. Build context
            ctx = self._build_extraction_context(db, project_id)

            # 2. Validate -- must have screenplay content
            if not ctx.screenplay_texts:
                run = self._record_run(
                    db, project_id, "failed",
                    result={"error": "No screenplay content found"},
                    error="No screenplay content found for project",
                )
                db.commit()
                return run

            # 3. Call AI
            response = await self._call_ai_extraction(ctx, bible_context=bible_context)

            # 3b. Post-processing deduplication
            deduplicated = self._deduplicate_elements(response.elements)

            # 4. Upsert elements
            result = self._upsert_elements(db, project_id, deduplicated)

            # 5. Reconcile scene links for each element in element_map
            for extracted_el in deduplicated:
                db_element = result["element_map"].get(extracted_el.canonical_name)
                if db_element is None:
                    continue  # Was skipped (deleted)
                if db_element.user_modified:
                    # REEX-02 (D-53-01): user-owned element -- leave its scene
                    # links untouched on re-extract. The user has taken ownership
                    # of this element (PUT sets user_modified=True), so we do NOT
                    # wipe/recreate its AI-sourced links. Membership in element_map
                    # is preserved; only the reconcile CALL is skipped. Scoped to
                    # user_modified only -- non-user_modified elements still
                    # reconcile so their links track the current script.
                    continue
                scene_links = self._map_scene_indices_to_ids(ctx, extracted_el.scene_appearances)
                self._reconcile_scene_links(db, db_element, scene_links)

            # 6. Record run
            run = self._record_run(
                db, project_id, "completed",
                result={
                    "elements_extracted": len(response.elements),
                    "created": result["created"],
                    "updated": result["updated"],
                    "skipped": result["skipped"],
                },
                created=result["created"],
                updated=result["updated"],
            )

            # 6b. Clear staleness flag (SYNC-04)
            stale_project = db.query(database.Project).filter(
                database.Project.id == str(project_id)
            ).first()
            if stale_project:
                stale_project.breakdown_stale = False

            # 7. Single commit
            db.commit()
            return run

        except Exception as e:
            db.rollback()
            logger.error("Extraction failed for project %s: %s", project_id, e)
            # Record a failed run in a new transaction
            run = self._record_run(
                db, project_id, "failed",
                result={"error": str(e)},
                error=str(e),
            )
            db.commit()
            raise


# Module-level singleton
breakdown_service = BreakdownService()
