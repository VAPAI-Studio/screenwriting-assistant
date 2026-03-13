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
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models import database

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
        description="One of: character, location, prop, wardrobe, vehicle"
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
- vehicle: Cars, trucks, bikes, boats, aircraft"""


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
        # 1. Fetch screenplay content
        screenplays = db.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == str(project_id)
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

        return ExtractionContext(
            screenplay_texts=[sc.content for sc in screenplays if sc.content],
            character_names=character_names,
            scene_summaries=scene_summaries,
            project_title=project.title if project else "",
        )

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

        # Scene list with indices for reliable matching
        parts.append("## Scenes")
        for i, scene in enumerate(ctx.scene_summaries):
            parts.append(f"Scene {i + 1}: {scene['summary']}")
        parts.append("")

        # Full screenplay text
        parts.append("## Screenplay Content")
        for text in ctx.screenplay_texts:
            parts.append(text)
            parts.append("---")

        parts.append("\nExtract all production elements from this screenplay.")
        return "\n".join(parts)

    async def extract(self, db: Session, project_id: UUID) -> dict:
        """Full extraction pipeline. Implemented in Plan 11-02."""
        return {"status": "not_implemented"}


# Module-level singleton
breakdown_service = BreakdownService()
