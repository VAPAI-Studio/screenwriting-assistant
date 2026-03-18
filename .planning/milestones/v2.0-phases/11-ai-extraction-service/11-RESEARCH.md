# Phase 11: AI Extraction Service - Research

**Researched:** 2026-03-13
**Domain:** AI-driven structured data extraction from screenplay content
**Confidence:** HIGH

## Summary

Phase 11 implements the core AI extraction service that analyzes screenplay content and character data to produce structured production elements (characters, locations, props, wardrobe, vehicles). The service builds an extraction context from the project's screenplay content (stored in `ScreenplayContent` table) and character names (from `ListItem` records in the `story.characters` PhaseData subsection), sends this to an AI provider with a strictly-typed JSON schema using structured outputs, and persists the results as `BreakdownElement` rows with `ElementSceneLink` junction records.

The existing codebase provides strong patterns to follow: the `ai_provider.py` abstraction already handles both OpenAI and Anthropic, `template_ai_service.py` demonstrates context building and JSON-mode calls, and Phase 10 established all database models and CRUD endpoints. The primary new work is: (1) building the `BreakdownService` class, (2) upgrading SDK versions for structured outputs, (3) implementing deduplication and user-modification protection logic, and (4) wiring the extraction endpoint stub into the real service.

**Primary recommendation:** Create a `backend/app/services/breakdown_service.py` with a `BreakdownService` class that follows the singleton pattern of `template_ai_service.py`. Use the existing `ai_provider.py` but add a new `chat_completion_structured()` function that supports Pydantic-based structured outputs for both OpenAI and Anthropic providers.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXTR-01 | AI extraction service analyzes screenplay + character names to produce structured JSON across 5 categories | Context builder gathers ScreenplayContent + character ListItems; structured output schema defines 5 categories |
| EXTR-02 | Uses structured outputs (schema-enforced JSON) via upgraded SDKs | OpenAI needs >=1.40.0 (currently 1.12.0); Anthropic needs >=0.77.0 (currently >=0.39.0); both SDKs support Pydantic-based structured outputs |
| EXTR-03 | Deduplication -- same element maps to one master list entry with canonical name | AI prompt instructs deduplication at extraction time; post-processing merges remaining duplicates via case-insensitive name matching |
| EXTR-04 | Low temperature (0.1-0.2); only physically-present elements | Temperature parameter already supported in ai_provider.py; prompt engineering restricts to on-screen elements |
| EXTR-05 | Scene linking -- each element tracks which scenes it appears in | AI response includes scene references per element; service matches to ListItem IDs via scene summary/content matching |
| SYNC-01 | Re-extraction preserves user_modified=true elements | Upsert logic skips elements where user_modified=true; existing name/description/metadata preserved |
| SYNC-02 | Soft-deleted elements not resurrected | Upsert logic filters out is_deleted=true elements from being restored |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=1.40.0 | OpenAI API with structured outputs | Minimum version for `client.chat.completions.parse()` with Pydantic response_format |
| anthropic | >=0.77.0 | Anthropic API with structured outputs | Minimum version for `client.messages.parse()` with output_format Pydantic support |
| pydantic | >=2.10 | Structured output schema definitions | Already in requirements; Pydantic models define extraction response shape |
| sqlalchemy | ==2.0.27 | ORM for element upsert and scene linking | Already in stack; all DB operations follow existing patterns |
| fastapi | ==0.110.0 | API endpoint (extraction trigger) | Already in stack; endpoint stub already exists |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ==8.0.2 | Integration testing | Test extraction service with mocked AI responses |
| pytest-asyncio | ==0.23.5 | Async test support | BreakdownService methods are async |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Structured outputs | json_mode + manual validation | Structured outputs guarantee schema compliance; json_mode can produce malformed JSON |
| Single extraction call | Per-scene extraction calls | Single call is simpler and cheaper; per-scene risks inconsistent deduplication across calls |
| AI-level deduplication | Post-processing only | Asking AI to deduplicate in the prompt reduces post-processing burden; belt-and-suspenders approach is best |

**Installation (upgrade only -- no new packages):**
```bash
# In backend/requirements.txt, update:
# openai==1.12.0  -->  openai>=1.40.0
# anthropic>=0.39.0  -->  anthropic>=0.77.0
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
    breakdown_service.py    # NEW: BreakdownService class (extraction logic)
    ai_provider.py          # MODIFIED: add chat_completion_structured() function
    template_ai_service.py  # REFERENCE: existing AI service patterns
backend/app/api/endpoints/
    breakdown.py            # MODIFIED: wire trigger_extraction to real service
backend/app/tests/
    test_breakdown_api.py   # MODIFIED: update extraction tests
    test_breakdown_service.py  # NEW: unit tests for extraction logic
```

### Pattern 1: BreakdownService Class (follows template_ai_service.py)
**What:** Singleton service class with methods for extraction context building, AI calls, and DB persistence.
**When to use:** Primary service for all extraction operations.
**Example:**
```python
# Source: follows template_ai_service.py singleton pattern
class BreakdownService:
    async def extract(self, db: Session, project_id: UUID) -> BreakdownRun:
        """Full extraction pipeline: gather context -> AI call -> upsert elements -> link scenes."""
        ...

    def _build_extraction_context(self, db: Session, project_id: UUID) -> ExtractionContext:
        """Gather screenplay content + character names + scene ListItem IDs."""
        ...

    async def _call_ai_extraction(self, context: ExtractionContext) -> ExtractionResponse:
        """Structured output AI call with low temperature."""
        ...

    def _upsert_elements(self, db: Session, project_id: UUID,
                         elements: List[ExtractedElement],
                         existing: List[BreakdownElement]) -> UpsertResult:
        """Insert/update elements with user_modified and is_deleted protection."""
        ...

    def _reconcile_scene_links(self, db: Session, element: BreakdownElement,
                                scene_ids: List[UUID]) -> None:
        """Sync scene links: add missing, remove stale (AI-sourced only)."""
        ...

breakdown_service = BreakdownService()
```

### Pattern 2: Structured Output Pydantic Models
**What:** Pydantic models that define the exact AI response schema for extraction.
**When to use:** Passed to `response_format` (OpenAI) or `output_format` (Anthropic) for guaranteed JSON shape.
**Example:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedSceneElement(BaseModel):
    """A single element occurrence in a specific scene."""
    scene_summary: str = Field(description="Brief identifier matching the scene's summary field")
    context: str = Field(description="How the element appears in this scene")

class ExtractedElement(BaseModel):
    """A production element extracted from the screenplay."""
    category: str = Field(description="One of: character, location, prop, wardrobe, vehicle")
    canonical_name: str = Field(description="The standard/canonical name for this element")
    description: str = Field(description="Brief description of the element")
    scene_appearances: List[ExtractedSceneElement] = Field(
        description="Which scenes this element physically appears in"
    )

class ExtractionResponse(BaseModel):
    """Complete extraction result from AI."""
    elements: List[ExtractedElement]
```

### Pattern 3: Extraction Context Builder
**What:** Gathers all data needed for the AI prompt from DB models.
**When to use:** Before the AI call, to build the complete context string.
**Example:**
```python
from dataclasses import dataclass

@dataclass
class ExtractionContext:
    """All data needed for an extraction AI call."""
    screenplay_texts: List[str]          # From ScreenplayContent.content
    character_names: List[str]           # From story.characters ListItem names
    scene_summaries: List[dict]          # {id: UUID, summary: str} from scene_list ListItems
    project_title: str

def _build_extraction_context(self, db: Session, project_id: UUID) -> ExtractionContext:
    # 1. Fetch ScreenplayContent records
    screenplays = db.query(database.ScreenplayContent).filter(
        database.ScreenplayContent.project_id == str(project_id)
    ).all()

    # 2. Fetch character names from story.characters
    chars_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == str(project_id),
        database.PhaseData.phase == "story",
        database.PhaseData.subsection_key == "characters",
    ).first()
    character_names = []
    if chars_pd:
        items = db.query(database.ListItem).filter(
            database.ListItem.phase_data_id == str(chars_pd.id)
        ).all()
        character_names = [
            li.content.get("name", "") for li in items if li.content.get("name")
        ]

    # 3. Fetch scene ListItems from scenes.scene_list
    scenes_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == str(project_id),
        database.PhaseData.phase == "scenes",
        database.PhaseData.subsection_key == "scene_list",
    ).first()
    scene_summaries = []
    if scenes_pd:
        scene_items = db.query(database.ListItem).filter(
            database.ListItem.phase_data_id == str(scenes_pd.id)
        ).order_by(database.ListItem.sort_order).all()
        scene_summaries = [
            {"id": li.id, "summary": li.content.get("summary", f"Scene {li.sort_order + 1}")}
            for li in scene_items
        ]

    # 4. Project title
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id)
    ).first()

    return ExtractionContext(
        screenplay_texts=[sc.content for sc in screenplays if sc.content],
        character_names=character_names,
        scene_summaries=scene_summaries,
        project_title=project.title if project else "",
    )
```

### Pattern 4: Dual-Provider Structured Output via ai_provider.py
**What:** Add a new function to `ai_provider.py` that supports Pydantic-based structured outputs for both OpenAI and Anthropic.
**When to use:** For extraction calls that require guaranteed JSON schema compliance.
**Example:**
```python
# In ai_provider.py -- new function
from pydantic import BaseModel
from typing import Type, TypeVar

T = TypeVar("T", bound=BaseModel)

async def chat_completion_structured(
    messages: List[Dict[str, str]],
    response_model: Type[T],
    temperature: float = 0.1,
    max_tokens: int = 4000,
    provider: Optional[str] = None,
) -> T:
    """Structured output completion. Returns validated Pydantic model instance."""
    provider = provider or settings.AI_PROVIDER

    if provider == "anthropic":
        return await _anthropic_structured(messages, response_model, temperature, max_tokens)
    else:
        return await _openai_structured(messages, response_model, temperature, max_tokens)

async def _openai_structured(messages, response_model, temperature, max_tokens):
    client = _get_openai_client()
    completion = await client.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=messages,
        response_format=response_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.parsed

async def _anthropic_structured(messages, response_model, temperature, max_tokens):
    client = _get_anthropic_client()
    # Separate system prompt
    system_prompt = None
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = (system_prompt or "") + msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})
    if not chat_messages or chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "Begin."})

    kwargs = {
        "model": settings.ANTHROPIC_MODEL,
        "messages": chat_messages,
        "output_format": response_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    response = await client.messages.parse(**kwargs)
    return response.parsed_output
```

### Pattern 5: Upsert with User-Modified Protection
**What:** Element upsert that preserves user modifications and respects soft-deletes.
**When to use:** During element persistence after AI extraction.
**Example:**
```python
def _upsert_elements(self, db: Session, project_id: UUID,
                     extracted: List[ExtractedElement]) -> dict:
    # Pre-load all existing elements for this project (single query)
    existing = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.project_id == str(project_id)
    ).all()
    existing_map = {(e.category, e.name.lower()): e for e in existing}

    created, updated, skipped = 0, 0, 0
    element_map = {}  # canonical_name -> BreakdownElement (for scene linking)

    for item in extracted:
        key = (item.category, item.canonical_name.lower())
        existing_elem = existing_map.get(key)

        if existing_elem:
            if existing_elem.is_deleted:
                # SYNC-02: Do NOT resurrect soft-deleted elements
                skipped += 1
                continue
            if existing_elem.user_modified:
                # SYNC-01: Preserve user modifications
                element_map[item.canonical_name] = existing_elem
                skipped += 1
                continue
            # Update AI-sourced element
            existing_elem.description = item.description
            existing_elem.source = "ai"
            element_map[item.canonical_name] = existing_elem
            updated += 1
        else:
            # Create new element
            new_elem = database.BreakdownElement(
                project_id=project_id,
                category=item.category,
                name=item.canonical_name,
                description=item.description,
                source="ai",
            )
            db.add(new_elem)
            db.flush()  # get ID for scene linking
            element_map[item.canonical_name] = new_elem
            created += 1

    return {"created": created, "updated": updated, "skipped": skipped,
            "element_map": element_map}
```

### Anti-Patterns to Avoid
- **Per-element AI calls:** Do NOT make a separate AI call per element or per scene. One call with the full screenplay produces better deduplication and consistency.
- **Hard-coding provider logic in the service:** Always go through `ai_provider.py` so both OpenAI and Anthropic work.
- **Deleting old scene links before checking source:** AI-sourced links can be replaced; user-sourced links should be preserved.
- **Using `json_mode=True` instead of structured outputs:** For extraction, structured outputs are required per EXTR-02 to guarantee the response shape.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation of AI response | Manual JSON parsing + validation | Pydantic structured outputs via `response_format`/`output_format` | SDK guarantees schema compliance at token generation level |
| Provider abstraction | Separate code paths in the service | Extend existing `ai_provider.py` with `chat_completion_structured()` | Keeps single provider toggle pattern consistent |
| Context string building | New helper from scratch | Follow `_get_project_context()` from `wizards.py` and `_build_project_context()` from `template_ai_service.py` | Proven patterns that handle PhaseData + ListItem traversal |
| Test fixtures | New fixture helpers | Extend existing `conftest.py` patterns and `test_breakdown_api.py` helpers | Consistent test patterns across test suite |

**Key insight:** The existing codebase already has 90% of the infrastructure needed. The new work is primarily the BreakdownService business logic and extending ai_provider.py for structured outputs.

## Common Pitfalls

### Pitfall 1: SDK Version Mismatch
**What goes wrong:** Structured output methods (`chat.completions.parse` for OpenAI, `messages.parse` for Anthropic) don't exist on old SDK versions.
**Why it happens:** Current requirements.txt has `openai==1.12.0` and `anthropic>=0.39.0`, both far below minimums.
**How to avoid:** Upgrade in the very first task: `openai>=1.40.0` and `anthropic>=0.77.0`. Verify imports work before writing service code.
**Warning signs:** `AttributeError: 'AsyncOpenAI' object has no attribute 'beta'` or `'AsyncAnthropic' has no attribute 'messages.parse'`.

### Pitfall 2: Scene Matching Fragility
**What goes wrong:** AI returns scene references by summary text, but summaries don't exactly match stored ListItem content.
**Why it happens:** AI paraphrases or abbreviates scene summaries.
**How to avoid:** Pass scene summaries with explicit index numbers in the prompt (e.g., "Scene 1: [summary]", "Scene 2: [summary]"). Have the AI reference scenes by index, not by freeform text. Then map indices to ListItem IDs by sort_order.
**Warning signs:** Many elements with zero scene links after extraction.

### Pitfall 3: UUID String Casting in SQLAlchemy Queries
**What goes wrong:** UUID comparisons fail silently when PostgreSQL UUIDs are compared against Python `uuid.UUID` objects.
**Why it happens:** PostgreSQL stores native UUIDs; Python passes objects. SQLite tests use strings.
**How to avoid:** Always cast to `str()` in `.filter()` calls, consistent with Phase 10's decision: `filter(Model.id == str(some_uuid))`.
**Warning signs:** Queries return empty results despite data existing; works in SQLite tests but fails in PostgreSQL.

### Pitfall 4: Transaction Scope During Extraction
**What goes wrong:** Partial extraction results committed to DB if AI call succeeds but scene linking fails.
**Why it happens:** Multiple `db.commit()` calls within the extraction pipeline.
**How to avoid:** Use a single transaction: `db.flush()` during processing (to get auto-generated IDs), only `db.commit()` once at the end after all elements and links are persisted. Wrap in try/except to rollback on failure.
**Warning signs:** Orphaned elements without scene links; inconsistent element counts between runs.

### Pitfall 5: Anthropic Async Client Method Name
**What goes wrong:** Using `await client.messages.parse()` on `AsyncAnthropic` -- the async method may differ.
**Why it happens:** Documentation often shows sync examples.
**How to avoid:** Verify the async client has the same method signature. The Anthropic SDK's `AsyncAnthropic` typically mirrors sync methods but check at implementation time.
**Warning signs:** `TypeError: object NoneType can't be used in 'await' expression`.

### Pitfall 6: Structured Output Schema Limitations
**What goes wrong:** Pydantic features like `Union`, complex validators, or recursive types may not be supported by structured outputs.
**Why it happens:** Structured output JSON schema support has constraints (e.g., no `oneOf` in some providers).
**How to avoid:** Keep extraction Pydantic models simple: use `str`, `List`, `Optional`, `bool`, `int` fields only. Avoid complex validators or union types. Use `Field(description=...)` for field-level instructions to the AI.
**Warning signs:** Schema validation errors at the API level before any tokens are generated.

## Code Examples

### Extraction System Prompt
```python
# Source: Derived from project requirements EXTR-01, EXTR-04
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
```

### Scene-Indexed Prompt Construction
```python
def _build_user_prompt(self, ctx: ExtractionContext) -> str:
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
```

### Extraction AI Call (Structured Output)
```python
async def _call_ai_extraction(self, ctx: ExtractionContext) -> ExtractionResponse:
    from .ai_provider import chat_completion_structured

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": self._build_user_prompt(ctx)},
    ]

    return await chat_completion_structured(
        messages=messages,
        response_model=ExtractionResponse,
        temperature=0.15,  # EXTR-04: Low temperature for deterministic extraction
        max_tokens=8000,   # Extraction can be verbose for full screenplays
    )
```

### Scene Link Reconciliation
```python
def _reconcile_scene_links(self, db: Session, element: database.BreakdownElement,
                            new_scene_ids: List[str]) -> None:
    """Replace AI-sourced scene links; preserve user-sourced links."""
    # Remove old AI-sourced links
    db.query(database.ElementSceneLink).filter(
        database.ElementSceneLink.element_id == str(element.id),
        database.ElementSceneLink.source == "ai",
    ).delete(synchronize_session="fetch")

    # Add new links
    for scene_id in new_scene_ids:
        # Check if user-sourced link already exists (don't duplicate)
        existing_user_link = db.query(database.ElementSceneLink).filter(
            database.ElementSceneLink.element_id == str(element.id),
            database.ElementSceneLink.scene_item_id == str(scene_id),
            database.ElementSceneLink.source == "user",
        ).first()
        if existing_user_link:
            continue

        link = database.ElementSceneLink(
            element_id=element.id,
            scene_item_id=scene_id,
            context="",
            source="ai",
        )
        db.add(link)
```

### BreakdownRun Audit Recording
```python
def _record_run(self, db: Session, project_id: UUID,
                status: str, result: dict, error: str = None,
                created: int = 0, updated: int = 0) -> database.BreakdownRun:
    from datetime import datetime, timezone
    run = database.BreakdownRun(
        project_id=project_id,
        status=status,
        config={"temperature": 0.15, "provider": settings.AI_PROVIDER},
        result_summary=result,
        elements_created=created,
        elements_updated=updated,
        error_message=error,
        completed_at=datetime.now(timezone.utc) if status in ("completed", "failed") else None,
    )
    db.add(run)
    return run
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `json_mode=True` with manual parsing | Structured outputs with Pydantic | OpenAI: Aug 2024; Anthropic: Nov 2025 | Guaranteed schema compliance; no JSON parse errors |
| `client.beta.chat.completions.parse()` | `client.chat.completions.parse()` | OpenAI SDK ~1.50+ | Method moved out of beta |
| Anthropic `output_format` param | Anthropic `output_config.format` or `messages.parse()` | SDK 0.77.0 (Jan 2026) | `messages.parse()` is the recommended high-level API |
| openai==1.12.0 | openai>=1.40.0 | Current project needs upgrade | Required for structured outputs |
| anthropic>=0.39.0 | anthropic>=0.77.0 | Current project needs upgrade | Required for structured outputs |

**Deprecated/outdated:**
- `client.beta.chat.completions.parse()` (OpenAI) -- moved to `client.chat.completions.parse()` in newer SDK versions
- `output_format` parameter (Anthropic) -- still works but `output_config.format` is the production API; SDK's `messages.parse()` abstracts this

## Data Flow Summary

```
1. User triggers: POST /api/breakdown/extract/{project_id}
2. breakdown.py endpoint calls: breakdown_service.extract(db, project_id)
3. Service gathers context:
   a. ScreenplayContent records (project_id) -> screenplay text
   b. PhaseData(phase="story", subsection_key="characters") -> ListItem names
   c. PhaseData(phase="scenes", subsection_key="scene_list") -> ListItem IDs + summaries
4. Service builds prompt with scene indices and character names
5. Service calls ai_provider.chat_completion_structured() with ExtractionResponse model
6. Service upserts BreakdownElement records:
   - Skip if is_deleted=true (SYNC-02)
   - Skip if user_modified=true (SYNC-01)
   - Update if AI-sourced element exists
   - Create if new
7. Service reconciles ElementSceneLink records:
   - Delete old AI-sourced links
   - Create new links matching scene indices to ListItem IDs
   - Preserve user-sourced links
8. Service records BreakdownRun audit entry
9. Returns BreakdownRunResponse to API
```

## Open Questions

1. **Anthropic async structured output method**
   - What we know: Sync API uses `client.messages.parse()`. Anthropic SDK provides `AsyncAnthropic` client.
   - What's unclear: Whether `AsyncAnthropic` exposes the same `.messages.parse()` method or requires different invocation.
   - Recommendation: Verify at implementation time by checking `dir(AsyncAnthropic().messages)`. If not available, fall back to `messages.create()` with `output_config` parameter.

2. **Token budget for full screenplay extraction**
   - What we know: A 10-minute short film might produce 10-15 pages of screenplay (~3000-5000 tokens input).
   - What's unclear: Whether a single AI call with full screenplay + all scenes will hit token limits.
   - Recommendation: Start with single-call approach. If token limit issues arise, chunk by scene groups. The `max_tokens=8000` output budget should be sufficient for element lists.

3. **OpenAI `parse()` async support**
   - What we know: The existing codebase uses `AsyncOpenAI` for all calls.
   - What's unclear: Whether `AsyncOpenAI.chat.completions.parse()` is available in the async client.
   - Recommendation: Test at implementation time. If async `parse()` is unavailable, fall back to `create()` with `response_format={"type": "json_schema", "schema": ...}` and manual Pydantic validation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 + pytest-asyncio 0.23.5 |
| Config file | None (uses defaults; conftest.py at backend/app/tests/) |
| Quick run command | `cd backend && python -m pytest app/tests/test_breakdown_service.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTR-01 | Service gathers screenplay + characters, produces elements | unit | `pytest app/tests/test_breakdown_service.py::test_extraction_produces_elements -x` | No -- Wave 0 |
| EXTR-02 | Structured output schema produces valid Pydantic model | unit | `pytest app/tests/test_breakdown_service.py::test_structured_output_schema -x` | No -- Wave 0 |
| EXTR-03 | Deduplication maps variants to canonical name | unit | `pytest app/tests/test_breakdown_service.py::test_deduplication -x` | No -- Wave 0 |
| EXTR-04 | Low temperature used; only on-screen elements | unit | `pytest app/tests/test_breakdown_service.py::test_extraction_temperature -x` | No -- Wave 0 |
| EXTR-05 | Elements linked to scene ListItems | integration | `pytest app/tests/test_breakdown_service.py::test_scene_linking -x` | No -- Wave 0 |
| SYNC-01 | Re-extraction preserves user_modified elements | integration | `pytest app/tests/test_breakdown_service.py::test_user_modified_preserved -x` | No -- Wave 0 |
| SYNC-02 | Soft-deleted elements not resurrected | integration | `pytest app/tests/test_breakdown_service.py::test_deleted_not_resurrected -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_breakdown_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_breakdown_service.py` -- covers EXTR-01 through SYNC-02
- [ ] Mock fixture for `chat_completion_structured` in conftest.py or test file
- [ ] No framework install needed -- pytest already in requirements.txt

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/models/database.py` -- BreakdownElement, ElementSceneLink, BreakdownRun, ListItem, PhaseData, ScreenplayContent models
- Codebase: `backend/app/api/endpoints/breakdown.py` -- existing stub extraction endpoint and CRUD
- Codebase: `backend/app/services/ai_provider.py` -- dual-provider chat completion pattern
- Codebase: `backend/app/services/template_ai_service.py` -- context building and JSON-mode AI call patterns
- Codebase: `backend/app/api/endpoints/wizards.py` -- `_get_project_context()` and `_get_character_data()` helpers
- Codebase: `backend/requirements.txt` -- current SDK versions (openai==1.12.0, anthropic>=0.39.0)
- Codebase: `backend/app/tests/conftest.py` -- test fixture patterns

### Secondary (MEDIUM confidence)
- [Anthropic Structured Outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- `messages.parse()` API, `output_format` parameter, Pydantic support
- [OpenAI Structured Outputs docs](https://platform.openai.com/docs/guides/structured-outputs) -- `chat.completions.parse()` API, `response_format` parameter
- [Anthropic SDK changelog](https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md) -- v0.77.0 introduced structured outputs
- [OpenAI SDK structured outputs deep wiki](https://deepwiki.com/openai/openai-python/4.1.3-parsed-responses-and-structured-outputs) -- `client.chat.completions.parse()` confirmed out of beta

### Tertiary (LOW confidence)
- SDK version floor for OpenAI: >=1.40.0 is the commonly cited minimum for structured outputs, but exact version varies by source. 1.42.0 confirmed to work. Using >=1.40.0 as safe floor.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- existing codebase is well-understood; SDK upgrade versions verified via multiple sources
- Architecture: HIGH -- patterns directly follow existing service/provider patterns in the codebase
- Pitfalls: HIGH -- based on concrete codebase analysis (UUID casting, transaction scope) and SDK documentation
- Structured outputs API: MEDIUM -- API surface verified via official docs but async variants need implementation-time verification

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days -- stable domain, SDK APIs unlikely to change)
