# backend/app/tests/test_breakdown_service.py

"""
Integration and unit tests for BreakdownService covering all Phase 11 requirements:
  EXTR-01: Extraction produces elements
  EXTR-02: Structured output schema
  EXTR-03: Post-processing deduplication
  EXTR-04: Extraction temperature
  EXTR-05: Scene linking
  SYNC-01: User-modified elements preserved
  SYNC-02: Soft-deleted elements not resurrected
"""

import uuid

import pytest
from unittest.mock import patch, AsyncMock
from app.models.database import (
    BreakdownElement,
    BreakdownRun,
    ElementSceneLink,
    ListItem,
    PhaseData,
    Project,
    ScreenplayContent,
)
from app.services.breakdown_service import (
    breakdown_service,
    ExtractionResponse,
    ExtractedElement,
    ExtractedSceneAppearance,
    ExtractionContext,
)


MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _setup_project_with_screenplay(db_session):
    """Create a project with screenplay content, characters, and 3 scenes.

    Returns (project_id, scene_item_ids_list) where scene_item_ids_list is
    a list of 3 scene ListItem IDs in order.
    """
    project_id = str(uuid.uuid4())

    # Create project
    project = Project(
        id=project_id,
        owner_id=MOCK_USER_ID,
        title="Test Film",
    )
    db_session.add(project)
    db_session.flush()

    # Create screenplay content
    sc = ScreenplayContent(
        id=str(uuid.uuid4()),
        project_id=project_id,
        content="INT. CASTLE - NIGHT\nThe KNIGHT draws a MAGIC SWORD from the stone.\n\nEXT. FOREST - DAY\nThe KNIGHT rides through on a HORSE.\n\nINT. THRONE ROOM - DAY\nThe KNIGHT presents the MAGIC SWORD to the KING.",
    )
    db_session.add(sc)
    db_session.flush()

    # Create characters PhaseData + ListItems
    chars_pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="story",
        subsection_key="characters",
        content={},
    )
    db_session.add(chars_pd)
    db_session.flush()

    for name in ["Knight", "King"]:
        li = ListItem(
            id=str(uuid.uuid4()),
            phase_data_id=str(chars_pd.id),
            item_type="character",
            content={"name": name},
            sort_order=0,
        )
        db_session.add(li)
    db_session.flush()

    # Create scenes PhaseData + 3 ListItems
    scenes_pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="scenes",
        subsection_key="scene_list",
        content={},
    )
    db_session.add(scenes_pd)
    db_session.flush()

    scene_item_ids = []
    for i in range(3):
        scene_id = str(uuid.uuid4())
        li = ListItem(
            id=scene_id,
            phase_data_id=str(scenes_pd.id),
            item_type="scene",
            content={"summary": f"Scene {i + 1} summary"},
            sort_order=i,
        )
        db_session.add(li)
        scene_item_ids.append(scene_id)
    db_session.flush()

    db_session.commit()
    return project_id, scene_item_ids


def _mock_extraction_response(elements):
    """Wrap a list of ExtractedElement into an ExtractionResponse."""
    return ExtractionResponse(elements=elements)


def _setup_project_with_aligned_screenplay(db_session):
    """Phase 50: project whose 3 ScreenplayContent rows each carry
    formatted_content.episode_index (0,1,2) with distinct per-scene content, so the
    ALIGNED per-scene prompt path is exercised. Mirrors the shape of
    _setup_project_with_screenplay but with one SC row per scene.

    Returns (project_id, scene_item_ids_list).
    """
    project_id = str(uuid.uuid4())

    project = Project(
        id=project_id,
        owner_id=MOCK_USER_ID,
        title="Aligned Film",
    )
    db_session.add(project)
    db_session.flush()

    # One ScreenplayContent row per scene, each carrying episode_index + distinct text.
    scene_texts = [
        "INT. CASTLE - NIGHT\nThe KNIGHT draws a MAGIC SWORD from the stone.",
        "EXT. FOREST - DAY\nThe KNIGHT rides through on a HORSE.",
        "INT. THRONE ROOM - DAY\nThe KNIGHT presents the MAGIC SWORD to the KING.",
    ]
    for i, text in enumerate(scene_texts):
        sc = ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content=text,
            formatted_content={"episode_index": i, "content": text},
        )
        db_session.add(sc)
    db_session.flush()

    # Characters PhaseData + ListItems
    chars_pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="story",
        subsection_key="characters",
        content={},
    )
    db_session.add(chars_pd)
    db_session.flush()

    for name in ["Knight", "King"]:
        li = ListItem(
            id=str(uuid.uuid4()),
            phase_data_id=str(chars_pd.id),
            item_type="character",
            content={"name": name},
            sort_order=0,
        )
        db_session.add(li)
    db_session.flush()

    # Scenes PhaseData + 3 ListItems (sort_order 0,1,2)
    scenes_pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="scenes",
        subsection_key="scene_list",
        content={},
    )
    db_session.add(scenes_pd)
    db_session.flush()

    scene_item_ids = []
    for i in range(3):
        scene_id = str(uuid.uuid4())
        li = ListItem(
            id=scene_id,
            phase_data_id=str(scenes_pd.id),
            item_type="scene",
            content={"summary": f"Scene {i + 1} summary"},
            sort_order=i,
        )
        db_session.add(li)
        scene_item_ids.append(scene_id)
    db_session.flush()

    db_session.commit()
    return project_id, scene_item_ids


def _setup_project_with_legacy_positional_screenplay(db_session):
    """Phase 50 (IN-01): 3 ScreenplayContent rows with NO episode_index (pure-legacy
    case), inserted in scene order. The breakdown query orders newest-first, so the
    positional-from-end fallback in _align_screenplay_to_scenes must recover ascending
    scene order (scene 0 -> oldest row text). Distinct per-scene text proves the
    mapping isn't reversed.

    Returns (project_id, scene_item_ids_list).
    """
    project_id = str(uuid.uuid4())
    project = Project(id=project_id, owner_id=MOCK_USER_ID, title="Legacy Film")
    db_session.add(project)
    db_session.flush()

    # No formatted_content.episode_index on any row -> pure-legacy positional path.
    scene_texts = [
        "INT. CAVE - NIGHT\nThe MINER lights a LANTERN.",
        "EXT. RIVER - DAY\nThe MINER crosses on a RAFT.",
        "INT. BANK - DAY\nThe MINER deposits the GOLD.",
    ]
    for text in scene_texts:
        sc = ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content=text,
            formatted_content={"content": text},  # deliberately NO episode_index
        )
        db_session.add(sc)
        db_session.flush()  # distinct created_at ordering per row insert

    scenes_pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="scenes",
        subsection_key="scene_list",
        content={},
    )
    db_session.add(scenes_pd)
    db_session.flush()

    scene_item_ids = []
    for i in range(3):
        scene_id = str(uuid.uuid4())
        db_session.add(ListItem(
            id=scene_id,
            phase_data_id=str(scenes_pd.id),
            item_type="scene",
            content={"summary": f"Scene {i + 1} summary"},
            sort_order=i,
        ))
        scene_item_ids.append(scene_id)
    db_session.flush()
    db_session.commit()
    return project_id, scene_item_ids


class TestBreakdownService:
    """Integration and unit tests for BreakdownService."""

    # ----------------------------------------------------------------
    # EXTR-01: Extraction produces elements
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_extraction_produces_elements(self, mock_ai, db_session):
        """extract() with mocked AI returning 3 elements creates 3 BreakdownElement rows."""
        project_id, scene_ids = _setup_project_with_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="character",
                canonical_name="Knight",
                description="A brave knight",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Draws sword"),
                ],
            ),
            ExtractedElement(
                category="prop",
                canonical_name="Magic Sword",
                description="An enchanted blade",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Drawn from stone"),
                ],
            ),
            ExtractedElement(
                category="location",
                canonical_name="Castle",
                description="A medieval castle",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Interior scene"),
                ],
            ),
        ])

        run = await breakdown_service.extract(db_session, project_id)

        # Assert run status
        assert run.status == "completed"
        assert run.elements_created == 3

        # Assert 3 elements in DB
        elements = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id
        ).all()
        assert len(elements) == 3
        categories = {e.category for e in elements}
        assert categories == {"character", "prop", "location"}

    # ----------------------------------------------------------------
    # EXTR-02: Structured output schema
    # ----------------------------------------------------------------
    def test_structured_output_schema(self):
        """ExtractionResponse model validates correctly with edge cases."""
        # Empty elements list is valid
        resp = ExtractionResponse(elements=[])
        assert len(resp.elements) == 0

        # Element with empty scene_appearances is valid
        elem = ExtractedElement(
            category="prop",
            canonical_name="Chair",
            description="A wooden chair",
            scene_appearances=[],
        )
        assert len(elem.scene_appearances) == 0

        # Full element is valid
        full_elem = ExtractedElement(
            category="character",
            canonical_name="Hero",
            description="The protagonist",
            scene_appearances=[
                ExtractedSceneAppearance(scene_index=1, context="Appears"),
            ],
        )
        resp2 = ExtractionResponse(elements=[full_elem])
        assert len(resp2.elements) == 1

        # model_json_schema() returns a valid dict (used by structured outputs)
        schema = ExtractionResponse.model_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema

    # ----------------------------------------------------------------
    # EXTR-03: Post-processing deduplication
    # ----------------------------------------------------------------
    def test_deduplication(self):
        """_deduplicate_elements merges same-category case-insensitive duplicates."""
        elements = [
            ExtractedElement(
                category="prop",
                canonical_name="Gun",
                description="A revolver",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Fired"),
                ],
            ),
            ExtractedElement(
                category="prop",
                canonical_name="gun",
                description="A pistol",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=2, context="Dropped"),
                ],
            ),
        ]

        result = breakdown_service._deduplicate_elements(elements)

        # Should merge into single element
        assert len(result) == 1
        merged = result[0]
        assert merged.canonical_name == "Gun"  # Keeps first name
        assert merged.description == "A revolver"  # Keeps first description
        assert len(merged.scene_appearances) == 2
        scene_indices = {a.scene_index for a in merged.scene_appearances}
        assert scene_indices == {1, 2}

    def test_deduplication_different_categories_not_merged(self):
        """Different categories with same name are NOT merged."""
        elements = [
            ExtractedElement(
                category="character",
                canonical_name="Gun",
                description="A character named Gun",
                scene_appearances=[],
            ),
            ExtractedElement(
                category="prop",
                canonical_name="Gun",
                description="A weapon",
                scene_appearances=[],
            ),
        ]

        result = breakdown_service._deduplicate_elements(elements)
        assert len(result) == 2

    # ----------------------------------------------------------------
    # EXTR-04: Extraction temperature
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_extraction_temperature(self, mock_ai, db_session):
        """AI call uses temperature=0.15."""
        project_id, _ = _setup_project_with_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([])

        await breakdown_service.extract(db_session, project_id)

        mock_ai.assert_called_once()
        call_kwargs = mock_ai.call_args.kwargs
        assert call_kwargs["temperature"] == 0.15

    # ----------------------------------------------------------------
    # EXTR-05: Scene linking
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_scene_linking(self, mock_ai, db_session):
        """Scene links connect elements to correct ListItem IDs based on scene_index."""
        project_id, scene_ids = _setup_project_with_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="character",
                canonical_name="Knight",
                description="A brave knight",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Draws sword"),
                    ExtractedSceneAppearance(scene_index=3, context="Presents sword"),
                ],
            ),
        ])

        await breakdown_service.extract(db_session, project_id)

        # Find the created element
        element = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id,
            BreakdownElement.name == "Knight",
        ).first()
        assert element is not None

        # Check scene links
        links = db_session.query(ElementSceneLink).filter(
            ElementSceneLink.element_id == str(element.id),
        ).all()
        assert len(links) == 2

        linked_scene_ids = {link.scene_item_id for link in links}
        # scene_index 1 -> scene_ids[0], scene_index 3 -> scene_ids[2]
        assert scene_ids[0] in linked_scene_ids
        assert scene_ids[2] in linked_scene_ids

    # ----------------------------------------------------------------
    # APPR-02: Per-appearance context persisted (D-51-01)
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_scene_link_context_persisted(self, mock_ai, db_session):
        """ElementSceneLink.context holds the AI's per-appearance context (was "" before Phase 51)."""
        project_id, scene_ids = _setup_project_with_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="character",
                canonical_name="Knight",
                description="A brave knight",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Draws sword"),
                    ExtractedSceneAppearance(scene_index=3, context="Presents sword"),
                ],
            ),
        ])

        await breakdown_service.extract(db_session, project_id)

        element = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id,
            BreakdownElement.name == "Knight",
        ).first()
        assert element is not None

        links = db_session.query(ElementSceneLink).filter(
            ElementSceneLink.element_id == str(element.id),
        ).all()
        # Map each link to its scene -> context, proving the "" -> real-context change.
        context_by_scene = {link.scene_item_id: link.context for link in links}
        assert context_by_scene[scene_ids[0]] == "Draws sword"   # scene_index 1
        assert context_by_scene[scene_ids[2]] == "Presents sword"  # scene_index 3

    # ----------------------------------------------------------------
    # APPR-03: Two-scene element consolidates to one element, two links (D-51-03)
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_appearance_consolidation_one_element_two_links(self, mock_ai, db_session):
        """An element across two scenes consolidates to ONE element with TWO scene links (APPR-03 verify)."""
        project_id, scene_ids = _setup_project_with_screenplay(db_session)

        # Two same-name same-category extracted elements, each in a distinct scene:
        # the existing _deduplicate_elements path must merge them into one.
        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="prop",
                canonical_name="Magic Sword",
                description="A glowing blade",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Drawn from stone"),
                ],
            ),
            ExtractedElement(
                category="prop",
                canonical_name="Magic Sword",
                description="(duplicate) the sword again",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=3, context="Presented to king"),
                ],
            ),
        ])

        await breakdown_service.extract(db_session, project_id)

        # APPR-03: exactly one element with the matching name
        elements = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id,
            BreakdownElement.name == "Magic Sword",
        ).all()
        assert len(elements) == 1
        element = elements[0]

        # APPR-01: element exposes its scene links; APPR-03: exactly two links
        links = db_session.query(ElementSceneLink).filter(
            ElementSceneLink.element_id == str(element.id),
        ).all()
        assert len(links) == 2
        linked_scene_ids = {link.scene_item_id for link in links}
        assert linked_scene_ids == {scene_ids[0], scene_ids[2]}

    # ----------------------------------------------------------------
    # SYNC-01: User-modified elements preserved
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_user_modified_preserved(self, mock_ai, db_session):
        """Pre-existing user_modified element retains its description after re-extraction."""
        project_id, _ = _setup_project_with_screenplay(db_session)

        # Pre-create a user-modified element
        existing = BreakdownElement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            category="prop",
            name="Magic Sword",
            description="User's description",
            source="user",
            user_modified=True,
        )
        db_session.add(existing)
        db_session.commit()

        # Mock AI returns same element with different description
        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="prop",
                canonical_name="Magic Sword",
                description="AI description",
                scene_appearances=[],
            ),
        ])

        await breakdown_service.extract(db_session, project_id)

        # Refresh and verify
        db_session.refresh(existing)
        assert existing.description == "User's description"
        assert existing.user_modified is True

    # ----------------------------------------------------------------
    # SYNC-02: Soft-deleted elements not resurrected
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_deleted_not_resurrected(self, mock_ai, db_session):
        """Pre-existing soft-deleted element remains is_deleted=True after re-extraction."""
        project_id, _ = _setup_project_with_screenplay(db_session)

        # Pre-create a soft-deleted element
        deleted_elem = BreakdownElement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            category="prop",
            name="Broken Lamp",
            description="A broken lamp",
            source="ai",
            is_deleted=True,
        )
        db_session.add(deleted_elem)
        db_session.commit()

        # Mock AI returns same element
        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="prop",
                canonical_name="Broken Lamp",
                description="A lamp that is broken",
                scene_appearances=[],
            ),
        ])

        run = await breakdown_service.extract(db_session, project_id)

        # Refresh and verify still deleted
        db_session.refresh(deleted_elem)
        assert deleted_elem.is_deleted is True

        # Verify no new element with that name was created
        all_lamps = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id,
            BreakdownElement.name == "Broken Lamp",
        ).all()
        assert len(all_lamps) == 1  # Only the deleted one
        assert all_lamps[0].is_deleted is True

    # ----------------------------------------------------------------
    # Phase 50 / BFID-02: aligned per-scene prompt shape
    # ----------------------------------------------------------------
    def test_aligned_prompt_emits_per_scene_indexed_text(self, db_session):
        """BFID-02: when SC rows align to scenes by episode_index, the prompt emits
        each scene's FULL text under its own 1-based '### Scene {i+1}' header."""
        project_id, _ = _setup_project_with_aligned_screenplay(db_session)

        ctx = breakdown_service._build_extraction_context(db_session, project_id)
        prompt = breakdown_service._build_user_prompt(ctx)

        # Per-scene indexed headers present
        assert "### Scene 1:" in prompt
        assert "### Scene 2:" in prompt
        assert "### Scene 3:" in prompt

        # Each scene's distinct full text appears under the aligned structure
        assert "draws a MAGIC SWORD from the stone" in prompt
        assert "rides through on a HORSE" in prompt
        assert "presents the MAGIC SWORD to the KING" in prompt

        # Aligned-form attribution instruction; NOT the concatenated fallback blob
        assert "Attribute each element to the scene index/indices" in prompt
        assert "## Screenplay Content" not in prompt

    # ----------------------------------------------------------------
    # Phase 50 / IN-01: legacy rows (no episode_index) must NOT mis-align
    # ----------------------------------------------------------------
    def test_legacy_rows_without_index_use_safe_concatenated_fallback(self, db_session):
        """IN-01 (data-correctness): rows with NO episode_index have no reliable
        scene-join key (created_at is only second-resolution; insertion order is not
        recoverable). The aligner must therefore NOT positionally guess (a guess can
        silently REVERSE scene order and mis-attribute every element). Instead it
        omits unmatched scenes, the strict full-coverage gate fails, and the prompt
        falls back to the safe concatenated `## Screenplay Content` form — never the
        per-scene `### Scene` aligned form. All scene texts still reach the AI."""
        project_id, _ = _setup_project_with_legacy_positional_screenplay(db_session)

        ctx = breakdown_service._build_extraction_context(db_session, project_id)
        prompt = breakdown_service._build_user_prompt(ctx)

        # Safe fallback path: concatenated form, NOT the aligned per-scene headers.
        assert "## Screenplay Content" in prompt
        assert "### Scene 1:" not in prompt
        # All three scene texts still reach the AI (BFID-01 holds in fallback).
        assert "lights a LANTERN" in prompt
        assert "crosses on a RAFT" in prompt
        assert "deposits the GOLD" in prompt

    # ----------------------------------------------------------------
    # Phase 50 / BFID-02: attribution mapping via the aligned path
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_aligned_attribution_maps_to_scene_ids(self, mock_ai, db_session):
        """BFID-02: with the aligned fixture, an AI response attributing an element to
        scene_index 1 and 3 links it to scene_ids[0] and scene_ids[2] (proves the
        unchanged _map_scene_indices_to_ids still maps the shared 1-based space)."""
        project_id, scene_ids = _setup_project_with_aligned_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="character",
                canonical_name="Knight",
                description="A brave knight",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Draws sword"),
                    ExtractedSceneAppearance(scene_index=3, context="Presents sword"),
                ],
            ),
        ])

        await breakdown_service.extract(db_session, project_id)

        element = db_session.query(BreakdownElement).filter(
            BreakdownElement.project_id == project_id,
            BreakdownElement.name == "Knight",
        ).first()
        assert element is not None

        links = db_session.query(ElementSceneLink).filter(
            ElementSceneLink.element_id == str(element.id),
        ).all()
        linked_scene_ids = {link.scene_item_id for link in links}
        assert scene_ids[0] in linked_scene_ids  # scene_index 1 -> scene_ids[0]
        assert scene_ids[2] in linked_scene_ids  # scene_index 3 -> scene_ids[2]

    # ----------------------------------------------------------------
    # Phase 50 / BFID-03: on-screen-only rules preserved verbatim
    # ----------------------------------------------------------------
    def test_on_screen_only_rules_preserved(self):
        """BFID-03 regression guard: the on-screen-only extraction rules remain in
        EXTRACTION_SYSTEM_PROMPT."""
        from app.services.breakdown_service import EXTRACTION_SYSTEM_PROMPT

        assert "PHYSICALLY PRESENT ON SCREEN" in EXTRACTION_SYSTEM_PROMPT
        # A second rule fragment: dialogue/backstory exclusion
        assert "merely mentioned in dialogue or backstory" in EXTRACTION_SYSTEM_PROMPT

    # ----------------------------------------------------------------
    # Phase 50 / D-50-01: graceful fallback never crashes extraction
    # ----------------------------------------------------------------
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    async def test_graceful_fallback_on_count_mismatch(self, mock_ai, db_session):
        """D-50-01: 1 SC row (no episode_index) + 3 scenes => alignment cannot cover
        all scenes; extract() still completes and the prompt uses the concatenated
        fallback form (no '### Scene' header)."""
        project_id, _ = _setup_project_with_screenplay(db_session)

        mock_ai.return_value = _mock_extraction_response([
            ExtractedElement(
                category="prop",
                canonical_name="Magic Sword",
                description="An enchanted blade",
                scene_appearances=[
                    ExtractedSceneAppearance(scene_index=1, context="Drawn"),
                ],
            ),
        ])

        run = await breakdown_service.extract(db_session, project_id)
        assert run.status == "completed"  # no crash

        # The builder degrades to the concatenated form for this ctx.
        ctx = breakdown_service._build_extraction_context(db_session, project_id)
        prompt = breakdown_service._build_user_prompt(ctx)
        assert "## Screenplay Content" in prompt
        assert "### Scene" not in prompt
