# Technology Stack

**Project:** v2.0 Script Breakdown -- AI-Powered Production Element Extraction
**Researched:** 2026-03-12
**Confidence:** HIGH (verified with current PyPI, npm, and official documentation)

---

## Core Verdict: AI Extraction with Structured Outputs, Custom Diff, No NLP Libraries

**Use the existing AI provider abstraction with Pydantic-defined schemas for structured extraction.** Do not add spaCy, NLTK, or any NLP library. The extraction task is not NER (Named Entity Recognition) in the traditional NLP sense -- it is domain-specific production element identification from screenplay text, which modern LLMs handle far better than rule-based NLP. The AI already understands screenplay conventions (slug lines, character cues, action lines) without preprocessing.

**Use DeepDiff for bidirectional sync diffing.** The bidirectional sync between script and breakdown requires detecting what changed between two versions of structured data. DeepDiff provides exactly this: deep comparison of nested Python dicts/lists with categorized change types (added, removed, changed). Rolling a custom diff is error-prone for nested structures.

**Use TanStack Table for breakdown master lists.** The existing frontend has card-based and list-based patterns, but the breakdown page needs filtering, sorting, and column-based views across categories -- a table is the natural UI. TanStack Table is headless, integrates cleanly with Tailwind and Radix UI (both already in the stack), and is the standard React table library.

---

## Recommended Stack

### Backend: AI Structured Extraction

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `openai` | `>=1.40.0` (upgrade from 1.12.0) | Structured outputs via `response_format: json_schema` | Current version (1.12.0) supports `json_mode=True` but not the newer `json_schema` structured outputs that guarantee schema compliance. Version 1.40+ adds `client.beta.chat.completions.parse()` which accepts Pydantic models directly and returns typed responses. The existing `ai_provider.py` wrapper already passes `response_format` -- the upgrade is backward-compatible. |
| `anthropic` | `>=0.42.0` (upgrade from >=0.39.0) | Structured outputs via `output_format` + `json_schema` | Anthropic added structured outputs in the `structured-outputs-2025-11-13` beta. The SDK provides `client.beta.messages.parse()` accepting Pydantic models with guaranteed schema compliance. Current pinned version (>=0.39.0) likely needs a bump to get structured output support. |
| Pydantic v2 | `>=2.10` (existing) | Define extraction schemas as Pydantic models | Both OpenAI and Anthropic SDKs natively accept Pydantic `BaseModel` subclasses for structured outputs. The same models serve as API request/response schemas, database serialization targets, and AI output definitions -- single source of truth. Already in the stack. |

**Confidence:** HIGH -- verified OpenAI structured outputs docs, Anthropic structured outputs docs, and PyPI versions.

**Key upgrade in `ai_provider.py`:**

The existing `chat_completion()` function uses `json_mode=True` which requests JSON but does not enforce a schema. For breakdown extraction, upgrade to schema-enforced structured outputs:

```python
# New method in ai_provider.py
async def structured_completion(
    messages: List[Dict[str, str]],
    response_model: type[BaseModel],
    temperature: float = 0.3,
    max_tokens: int = 4000,
    provider: Optional[str] = None,
) -> BaseModel:
    """Structured completion with guaranteed schema compliance.

    Uses OpenAI's response_format json_schema or Anthropic's
    output_format json_schema to ensure the response matches
    the provided Pydantic model exactly.
    """
    provider = provider or settings.AI_PROVIDER
    if provider == "anthropic":
        return await _anthropic_structured(messages, response_model, temperature, max_tokens)
    else:
        return await _openai_structured(messages, response_model, temperature, max_tokens)
```

This avoids fragile `json.loads()` + manual validation on AI output. The SDK handles schema enforcement and parsing.

### Backend: Bidirectional Sync

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `deepdiff` | `8.6.1` | Detect changes between script versions and breakdown states | DeepDiff compares nested Python dicts/lists and categorizes changes as `dictionary_item_added`, `dictionary_item_removed`, `values_changed`, `iterable_item_added`, etc. This maps directly to the sync use case: when a script is re-generated, diff the new extraction against the stored breakdown to find what was added, removed, or changed. The `Delta` class can also serialize diffs for audit trails. |

**Confidence:** HIGH -- verified PyPI version (8.6.1), MIT license, Python 3.9+ support, active maintenance.

**Why not custom diffing:** The breakdown data structure is a nested dict of categories, each containing lists of elements with properties. A naive `==` comparison would miss partial changes. DeepDiff handles: list item reordering (`ignore_order=True`), type coercion, and nested path tracking. Writing this correctly from scratch is a week of edge-case debugging.

**Why not `jsondiff` or `dictdiffer`:** DeepDiff is the most actively maintained (last release: Sep 2025), has the richest feature set (Delta serialization, deep search, hash-based comparison), and handles the widest range of Python types. `dictdiffer` has not been updated since 2021.

### Backend: Token Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `tiktoken` | `0.7.0` (existing) | Count tokens in script content before sending to AI | Breakdown extraction of a full screenplay can be 15K-30K tokens. Token counting with tiktoken (already installed) is needed to decide whether to chunk the script or send it whole. Already used in the codebase for book processing. |

**Confidence:** HIGH -- already in requirements.txt and used in book processing.

### Database: Breakdown Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL 15 (existing) | 15 | Store breakdown elements, categories, scene links | New tables needed but no new database technology. PostgreSQL JSONB handles element metadata flexibly. Foreign keys handle project and scene linkage. |
| SQLAlchemy 2.0.27 (existing) | 2.0.27 | ORM models for `BreakdownElement`, `BreakdownCategory`, `ElementSceneLink` | Follows existing model patterns from `database.py`. Cascade deletes when project is deleted. |

**Confidence:** HIGH -- exact patterns already established in the codebase.

### Frontend: Breakdown Table UI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@tanstack/react-table` | `^8.21.3` | Headless table logic for master list views | The breakdown page shows master lists per category (Characters, Locations, Props, Wardrobe, Vehicles) with columns for element name, description, scene count, and actions. TanStack Table provides sorting, filtering, column visibility, and row selection -- all needed for breakdown management. It is headless (no DOM opinions), so it integrates with existing Tailwind + Radix UI styling. 5.3M weekly npm downloads; the standard React table solution. |
| `@radix-ui/react-tabs` | `^1.0.4` (existing) | Tab switching between breakdown categories | Already installed. The breakdown page uses tabs for Characters, Locations, Props, Wardrobe, Vehicles -- each tab renders a TanStack Table. |
| `@radix-ui/react-dialog` | `^1.0.5` (existing) | Element edit/add modals | Already installed. User refinement of breakdown elements (edit name, description, add notes) uses the existing Dialog pattern. |
| `lucide-react` | `^0.314.0` (existing) | Icons for element types, scene links, edit/delete actions | Already installed. Icons like `MapPin` (locations), `User` (characters), `Package` (props), `Shirt` (wardrobe), `Car` (vehicles) are available. |

**Confidence:** HIGH -- TanStack Table version verified via npm; existing Radix/Lucide deps verified in package.json.

---

## What NOT to Add

### spaCy / NLTK / Hugging Face Transformers

**Do not add.** These NLP libraries are designed for token-level linguistic analysis (POS tagging, dependency parsing, NER). The breakdown extraction task is:

1. Read screenplay text (which has standardized formatting)
2. Identify production elements by category (characters, locations, props, etc.)
3. Return structured JSON

Modern LLMs (GPT-4, Claude) outperform rule-based NLP for this task because they understand screenplay conventions contextually. A character mentioned in action lines vs. a character in dialogue headers vs. a character reference in description -- the LLM disambiguates naturally. spaCy's NER would require custom training data and would still miss domain-specific elements like "picture vehicles" vs. transportation.

Additionally, spaCy adds ~300MB to the Docker image (model downloads), plus numpy/scipy dependencies. Not worth it when the AI provider already handles this.

**Confidence:** HIGH -- the project already uses LLMs for content understanding; NLP libraries would be a parallel, inferior system.

### Instructor Library

**Do not add.** Instructor is a popular wrapper for structured LLM outputs that patches OpenAI/Anthropic clients. However, the project already has `ai_provider.py` as its abstraction layer. Adding Instructor would create two abstraction layers for the same thing. The OpenAI and Anthropic SDKs now have native structured output support (via `parse()` methods) that Instructor originally filled the gap for. Use the native SDK capabilities directly in `ai_provider.py`.

**Confidence:** HIGH -- the native SDK structured outputs make Instructor redundant for this use case.

### PydanticAI

**Do not add.** PydanticAI is a full agent framework built by the Pydantic team. It is a framework-level abstraction over LLM providers. The project already has its own provider abstraction (`ai_provider.py`) and agent system. PydanticAI would conflict with both.

**Confidence:** HIGH.

### AG Grid / Material React Table / Other Pre-styled Table Libraries

**Do not add.** AG Grid is enterprise-grade with a commercial license. Material React Table imposes Material UI styling that conflicts with the Tailwind + Radix UI design system. The project needs a headless table (logic only, no styling opinions) that integrates with the existing design system. TanStack Table is the correct choice.

**Confidence:** HIGH.

### Real-time Sync Libraries (Y.js, Automerge, ShareDB)

**Do not add.** The PROJECT.md explicitly states: "Real-time sync (changes propagate on save/generate, not as user types)" is out of scope. These CRDT/OT libraries solve real-time collaborative editing conflicts. The breakdown syncs on discrete save/generate events, which is a simple request-response pattern.

**Confidence:** HIGH -- explicitly out of scope per PROJECT.md.

### Fountain Parser Libraries (Jouvence, screenplay-tools)

**Do not add.** The script content in this app is generated by the AI service and stored as text/JSON in the database -- it is not in Fountain format (.fountain files). The screenplay content lives in `ScreenplayContent.content` (Text) and `ScreenplayContent.formatted_content` (JSON). Parsing from Fountain format is unnecessary since the app controls the data format end-to-end.

If Fountain import is added in a future milestone, `screenplay-tools` (Python, actively maintained, supports Fountain + FDX) would be the choice. But do not add it now.

**Confidence:** HIGH -- verified data model; content is stored in app-controlled format.

---

## Supporting Libraries (New Additions Only)

### Backend

```bash
# Upgrade existing packages
pip install "openai>=1.40.0"      # Structured outputs support
pip install "anthropic>=0.42.0"   # Structured outputs beta

# New package
pip install deepdiff==8.6.1       # Bidirectional sync diffing
```

### Frontend

```bash
npm install @tanstack/react-table@^8.21.3
```

**Total new dependencies: 1 backend (deepdiff), 1 frontend (@tanstack/react-table), plus 2 version upgrades.**

This is intentionally minimal. The existing stack handles 90% of the work.

---

## Integration Points with Existing Code

### What Already Exists (Do Not Rewrite)

| Existing Component | How It Is Reused for Breakdown |
|-------------------|-------------------------------|
| `ai_provider.chat_completion(json_mode=True)` | Fallback for providers/models that do not support structured outputs. The new `structured_completion()` method wraps this with schema enforcement when available. |
| `ai_provider.py` provider abstraction | Extended with `structured_completion()` method. No changes to existing methods. |
| `TemplateAIService._build_project_context()` | Called to gather all project phase data as context for the breakdown extraction prompt. The AI needs the full project context (characters defined in Idea phase, locations from Scene phase, etc.) to extract elements accurately. |
| `ScreenplayContent` model | Source data for extraction. Query all `ScreenplayContent` rows for a project, concatenate content, and feed to the extraction AI call. |
| `ListItem` model (scenes) | Scene identifiers for element-to-scene linking. Each breakdown element references which scenes it appears in by `ListItem.id`. |
| `PhaseData` model | Additional context source. Character descriptions, location details, wardrobe notes from earlier phases inform element extraction. |
| React Query patterns | `useQuery` for fetching breakdown data, `useMutation` for CRUD operations, `invalidateQueries` for cache updates. Exact patterns from SnippetManager and CardGridView. |
| Radix UI Dialog + Tabs | Element edit modals (Dialog) and category tabs (Tabs) on the breakdown page. Already installed. |
| Tailwind styling patterns | Table styling follows existing card/list patterns. No new CSS approach. |

### What Needs to Be Added

| New Component | Location | Purpose |
|--------------|----------|---------|
| `structured_completion()` in `ai_provider.py` | `backend/app/services/ai_provider.py` | Schema-enforced AI completion returning typed Pydantic models |
| Breakdown Pydantic schemas | `backend/app/models/breakdown_schemas.py` | `BreakdownResult`, `BreakdownElement`, `ElementCategory` -- serve as both AI output schema and API response schema |
| `BreakdownElement` SQLAlchemy model | `backend/app/models/database.py` | Persist extracted elements with category, name, description, metadata |
| `ElementSceneLink` SQLAlchemy model | `backend/app/models/database.py` | Many-to-many: element <-> scene (ListItem) with optional notes |
| `breakdown_service.py` | `backend/app/services/` | `extract_breakdown()`, `sync_breakdown()`, `get_breakdown()`, `update_element()` |
| `breakdown_sync_service.py` | `backend/app/services/` | DeepDiff-based sync logic: compare old extraction vs. new, merge with user edits |
| `GET/POST/PATCH/DELETE /api/breakdown/` | `backend/app/api/endpoints/breakdown.py` | CRUD endpoints for breakdown elements + extraction trigger |
| Migration SQL | `backend/migrations/` | `breakdown_elements`, `element_scene_links` tables |
| `BreakdownPage.tsx` | `frontend/src/components/Breakdown/` | Main breakdown page with category tabs and master list tables |
| `BreakdownTable.tsx` | `frontend/src/components/Breakdown/` | TanStack Table wrapper for one category's element list |
| `ElementEditDialog.tsx` | `frontend/src/components/Breakdown/` | Radix Dialog for editing/adding elements |
| `SceneLinkBadges.tsx` | `frontend/src/components/Breakdown/` | Scene reference badges shown on each element row |

---

## Structured Output Schema Design

The extraction schema is the single most important design decision. It serves triple duty:

1. **AI output format** -- the LLM returns data matching this schema
2. **API response format** -- the frontend receives this shape
3. **Database serialization target** -- elements are unpacked from this into DB rows

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ElementCategory(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"
    WARDROBE = "wardrobe"
    VEHICLE = "vehicle"

class SceneReference(BaseModel):
    scene_identifier: str = Field(description="Scene heading or number from the script")
    context: str = Field(description="Brief note on how the element appears in this scene")

class BreakdownElement(BaseModel):
    category: ElementCategory
    name: str = Field(description="Element name, e.g., 'DETECTIVE SARAH' or 'Vintage Revolver'")
    description: str = Field(description="Brief production-relevant description")
    scenes: List[SceneReference] = Field(description="Scenes where this element appears")
    notes: Optional[str] = Field(default=None, description="Additional production notes")

class BreakdownResult(BaseModel):
    elements: List[BreakdownElement] = Field(description="All extracted production elements")
    extraction_notes: str = Field(description="Any ambiguities or assumptions made during extraction")
```

**Why this shape:** Flat list of elements with embedded scene references. This is simpler to diff than a nested category-first structure, and the frontend groups by category client-side (or via a DB query). The AI returns one pass over all categories rather than N separate calls per category -- more efficient and catches cross-category relationships (a character's wardrobe in a specific scene).

---

## Bidirectional Sync Pattern

The sync problem has three states to reconcile:

1. **Previous AI extraction** (stored in DB)
2. **New AI extraction** (from updated script)
3. **User edits** (modifications to the previous extraction)

The sync algorithm using DeepDiff:

```python
from deepdiff import DeepDiff

def sync_breakdown(
    previous_extraction: dict,
    new_extraction: dict,
    user_edits: dict,
) -> dict:
    """
    Three-way merge: keep user edits, apply AI changes from script updates.

    - User-added elements: KEEP (not in any AI extraction)
    - User-edited elements: KEEP user version unless element was removed from script
    - AI-added elements (new in script): ADD
    - AI-removed elements (no longer in script): MARK for review, do not auto-delete
    """
    # What changed in the AI extraction?
    ai_diff = DeepDiff(previous_extraction, new_extraction, ignore_order=True)

    # What did the user change?
    user_diff = DeepDiff(previous_extraction, user_edits, ignore_order=True)

    # Apply AI additions that don't conflict with user edits
    # Flag AI removals for user review
    # Preserve all user additions and modifications
    ...
```

**Key principle:** Never auto-delete user-edited elements. If the AI extraction no longer finds an element but the user has edited it, flag it for review rather than removing it. This respects user intent.

**Confidence:** HIGH on DeepDiff suitability. MEDIUM on the exact sync algorithm -- will need refinement during implementation as edge cases emerge.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| AI extraction approach | Structured outputs (schema-enforced) | `json_mode=True` (current) | `json_mode` requests JSON but does not enforce schema -- the AI can return valid JSON that does not match the expected shape. Structured outputs guarantee the shape. |
| AI extraction approach | Structured outputs (schema-enforced) | Instructor library | Instructor wraps the SDK clients. Since OpenAI and Anthropic now have native structured output support, Instructor adds an unnecessary abstraction layer on top of `ai_provider.py`. |
| NLP preprocessing | None (direct LLM extraction) | spaCy NER | LLMs outperform spaCy for domain-specific extraction from semi-structured text. spaCy adds 300MB+ to Docker image. Would need custom training data for screenplay elements. |
| Diff library | DeepDiff | Custom dict comparison | Nested structure diffing is surprisingly complex (list reordering, type coercion, path tracking). DeepDiff handles all edge cases. |
| Diff library | DeepDiff | `dictdiffer` | Last updated 2021. DeepDiff is actively maintained (Sep 2025) with more features (Delta, DeepSearch). |
| Frontend table | TanStack Table (headless) | AG Grid | AG Grid is enterprise-licensed. Imposes its own styling. Overkill for the breakdown use case. |
| Frontend table | TanStack Table (headless) | Material React Table | Imposes Material UI styling that conflicts with Tailwind + Radix UI design system. |
| Frontend table | TanStack Table (headless) | Custom HTML tables | Would need to re-implement sorting, filtering, column resizing. TanStack Table provides this out of the box with zero styling opinions. |
| Sync approach | DeepDiff three-way merge on save | Real-time CRDT (Y.js) | Explicitly out of scope per PROJECT.md constraints. |

---

## Version Upgrade Details

### OpenAI SDK Upgrade: 1.12.0 -> >=1.40.0

**Why upgrade:** Version 1.12.0 (current) supports `json_mode=True` but not the `response_format: {type: "json_schema", json_schema: {...}}` parameter that guarantees schema compliance. The `parse()` method for Pydantic model outputs was added in later versions. The latest stable is 2.26.0 but pinning to `>=1.40.0` ensures structured output support while allowing flexibility.

**Breaking changes:** None for the existing usage. The `chat.completions.create()` API is backward-compatible. The `json_mode=True` codepath in `ai_provider.py` continues to work unchanged. The new `structured_completion()` method uses the newer API surface alongside the existing one.

**Recommendation:** Pin to `>=1.40.0,<3.0.0` for safety.

### Anthropic SDK Upgrade: >=0.39.0 -> >=0.42.0

**Why upgrade:** Structured outputs were added in the `structured-outputs-2025-11-13` beta. The `client.beta.messages.parse()` method and `output_format` parameter require a recent SDK version. The latest stable is 0.84.0.

**Breaking changes:** None for existing usage. The `messages.create()` API is backward-compatible. The structured output feature is accessed through the `beta` namespace.

**Recommendation:** Pin to `>=0.42.0,<1.0.0`. The structured outputs feature is still in beta -- the beta namespace isolates it from the stable API.

**Confidence:** MEDIUM on exact minimum versions for structured output support. The important thing is that both SDKs now support it natively; the exact version floor needs verification during implementation.

---

## Installation

### Backend

```bash
# Updated requirements.txt additions/changes:
# Upgrade existing:
openai>=1.40.0,<3.0.0           # Was: openai==1.12.0
anthropic>=0.42.0,<1.0.0        # Was: anthropic>=0.39.0

# New:
deepdiff==8.6.1                 # Bidirectional sync diffing
```

### Frontend

```bash
npm install @tanstack/react-table@^8.21.3
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| No NLP libraries needed | HIGH | LLMs outperform traditional NLP for domain-specific extraction; verified by industry practice |
| OpenAI structured outputs | HIGH | Verified via official docs and PyPI; feature is GA |
| Anthropic structured outputs | HIGH | Verified via official docs; feature is in public beta since Nov 2025 |
| SDK version requirements | MEDIUM | Exact minimum versions for structured output support need verification during implementation; latest versions definitely support it |
| DeepDiff for sync | HIGH | Verified PyPI version, feature set, and active maintenance |
| TanStack Table for breakdown UI | HIGH | Verified npm version, weekly downloads, Tailwind/Radix compatibility |
| Pydantic as schema bridge | HIGH | Natively supported by both OpenAI and Anthropic SDKs |
| Three-way sync algorithm | MEDIUM | Concept is sound; implementation details will need refinement during development |
| No Fountain parser needed | HIGH | Verified data model; content is in app-controlled format |

---

## Sources

- [OpenAI Structured Outputs Guide](https://developers.openai.com/api/docs/guides/structured-outputs/) -- HIGH confidence
- [Anthropic Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- HIGH confidence
- [OpenAI Python SDK on PyPI](https://pypi.org/project/openai/) -- version 2.26.0 verified -- HIGH confidence
- [Anthropic Python SDK on PyPI](https://pypi.org/project/anthropic/) -- version 0.84.0 verified -- HIGH confidence
- [DeepDiff on PyPI](https://pypi.org/project/deepdiff/) -- version 8.6.1 verified -- HIGH confidence
- [DeepDiff Documentation](https://zepworks.com/deepdiff/current/) -- HIGH confidence
- [TanStack Table on npm](https://www.npmjs.com/package/@tanstack/react-table) -- version 8.21.3 verified -- HIGH confidence
- [TanStack Table Docs](https://tanstack.com/table/latest/docs/introduction) -- HIGH confidence
- [Pydantic LLM Integration Guide](https://pydantic.dev/articles/llm-intro) -- MEDIUM confidence
- [StudioBinder Script Breakdown Elements Guide](https://www.studiobinder.com/blog/the-complete-guide-to-mastering-script-breakdown-elements/) -- domain knowledge -- HIGH confidence
- [Script Breakdown Wikipedia](https://en.wikipedia.org/wiki/Script_breakdown) -- domain knowledge -- HIGH confidence
- Codebase analysis: `backend/app/services/ai_provider.py` -- HIGH confidence
- Codebase analysis: `backend/app/models/database.py` (ScreenplayContent, ListItem, PhaseData) -- HIGH confidence
- Codebase analysis: `backend/requirements.txt` -- HIGH confidence
- Codebase analysis: `frontend/package.json` -- HIGH confidence

*Stack research: 2026-03-12*
