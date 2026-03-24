# Phase 41: Bible AI Injection - Research

**Researched:** 2026-03-24
**Domain:** AI prompt injection / context augmentation for episode generation
**Confidence:** HIGH

## Summary

This phase modifies existing AI generation services to automatically prepend series bible content and target episode duration into prompts when the project is an episode (has `show_id`). Standalone film projects (show_id=NULL) are completely unaffected. There are no UI changes.

The implementation is straightforward: a helper function builds a bible context string from the Show model's bible columns, and this string is passed as an optional parameter through the endpoint-to-service call chain. Three services are affected: `template_ai_service.py` (wizard generation, chat, fill blanks, give notes, analyze structure), `openai_service.py` (section review), and `breakdown_service.py` (extraction). The endpoint handlers already have DB access and will look up the show + bible data when `project.show_id` is not None.

**Primary recommendation:** Create a shared `build_bible_context(db, project)` helper function in a new utility location (or in the endpoints module), then thread `bible_context: Optional[str] = None` through all affected service methods and prepend it to prompts where it appears.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Inject bible context in `template_ai_service.py` -> `_build_project_context()` method
- Also inject into `openai_service.py` -> `review_section()` method (agent reviews)
- Also inject into `breakdown_service.py` for breakdown extraction
- Bible context injected as a prefix block before the existing project context
- When `project.show_id` is not None: fetch show record, build bible block with show title, episode duration, and four bible sections (only non-empty fields)
- If no bible fields filled and no duration set -> skip injection (no empty context)
- Pass `bible_context: Optional[str] = None` to service methods -- keeps services DB-agnostic
- Build bible context in the API endpoint handlers (they already have DB access)
- Affected services + methods:
  1. `template_ai_service.py` -> `_build_project_context()` -- prepend bible_context if provided
  2. `template_ai_service.py` -> `wizard_generate()` -- accept and pass bible_context
  3. `openai_service.py` -> `_get_system_prompt()` -- prepend bible context to system prompt
  4. `openai_service.py` -> `review_section()` -- accept and pass bible_context
  5. `breakdown_service.py` -> extraction call -- accept and pass bible_context
- API endpoint changes: review, template AI (wizards, fill_blanks, etc.), breakdown extraction all fetch show bible if project.show_id is set
- Tests: verify bible context appears in prompts when project has show_id; verify standalone projects have no bible context; mock AI calls and test prompt construction

### Claude's Discretion
- Exact formatting of bible block headers
- Whether to use separator lines (---) between bible and project context

### Deferred Ideas (OUT OF SCOPE)
- Per-section bible toggle -- not in requirements
- Bible context in shotlist generation -- not in requirements (BIBL-04 specifies screenplay + agent review + breakdown)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BIBL-04 | Bible content (all four sections) and episode duration are automatically injected into AI context for episode script generation, agent reviews, and breakdown extraction | All three services identified with exact methods and injection points. Helper function pattern documented. Testing approach using mock AI calls verified against existing test patterns. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API endpoints where bible context is built | Already in project |
| SQLAlchemy | existing | DB queries to fetch Show model | Already in project |
| Python typing | 3.11 | `Optional[str]` parameter threading | Standard library |

### Supporting
No new libraries needed. This phase modifies existing code only.

## Architecture Patterns

### Recommended Project Structure
No new files required. All changes are to existing files:
```
backend/app/
├── api/endpoints/
│   ├── wizards.py          # Add bible lookup before wizard calls
│   ├── ai_chat.py          # Add bible lookup before chat/fill/notes calls
│   ├── review.py           # Add bible lookup before review_section call
│   └── breakdown.py        # Add bible lookup before extract call
├── services/
│   ├── template_ai_service.py  # Accept bible_context, prepend to project context
│   ├── openai_service.py       # Accept bible_context, prepend to system prompt
│   └── breakdown_service.py    # Accept bible_context, prepend to user prompt
└── tests/
    └── test_bible_injection.py  # NEW: tests for bible context injection
```

### Pattern 1: Shared Bible Context Builder
**What:** A reusable function that takes a DB session and a project, checks for show_id, fetches the Show record, and returns a formatted bible context string (or None if no bible data exists).
**When to use:** Every endpoint that calls an AI service method.
**Example:**
```python
from typing import Optional
from sqlalchemy.orm import Session
from ..models.database import Project, Show

def build_bible_context(db: Session, project: Project) -> Optional[str]:
    """Build bible context string for episode projects. Returns None for standalone films."""
    if not project.show_id:
        return None

    show = db.query(Show).filter(Show.id == str(project.show_id)).first()
    if not show:
        return None

    parts = []
    parts.append(f"## Series Bible Context")
    parts.append(f"**Show:** {show.title}")

    if show.episode_duration_minutes:
        parts.append(f"**Target Episode Duration:** {show.episode_duration_minutes} minutes")

    if show.bible_characters:
        parts.append(f"\n### Characters\n{show.bible_characters}")

    if show.bible_world_setting:
        parts.append(f"\n### World & Setting\n{show.bible_world_setting}")

    if show.bible_season_arc:
        parts.append(f"\n### Season Arc\n{show.bible_season_arc}")

    if show.bible_tone_style:
        parts.append(f"\n### Tone & Style\n{show.bible_tone_style}")

    # If only the show title was added (no bible content, no duration), skip
    if len(parts) <= 2 and not show.episode_duration_minutes:
        return None

    return "\n".join(parts)
```

### Pattern 2: Service Method Threading
**What:** Add `bible_context: Optional[str] = None` parameter to service methods and prepend it to the prompt/context when provided.
**When to use:** Every service method that builds an AI prompt.
**Example (template_ai_service._build_project_context):**
```python
def _build_project_context(
    self,
    project_data: Dict,
    template_id: str,
    list_items: Optional[Dict[str, list]] = None,
    project_title: Optional[str] = None,
    bible_context: Optional[str] = None,  # NEW
) -> str:
    template = get_template(template_id)
    context_parts = []

    # Prepend bible context if provided
    if bible_context:
        context_parts.append(bible_context)
        context_parts.append("---")

    if project_title:
        context_parts.append(f"Project: {project_title}")
    # ... rest unchanged
```

### Pattern 3: Endpoint Bible Lookup
**What:** In each endpoint handler, after fetching the project, call `build_bible_context()` and pass the result to the service.
**When to use:** Every endpoint that calls an AI service.
**Example (wizards.py _get_project_context):**
```python
def _get_project_context(db: Session, project: database.Project, bible_context: Optional[str] = None) -> str:
    # ... existing code ...
    return template_ai_service._build_project_context(
        project_data, template_id, list_items=list_items_map,
        project_title=project.title, bible_context=bible_context
    )
```

### Anti-Patterns to Avoid
- **DB lookups in services:** Services should remain DB-agnostic. The bible context should be a string passed in, not fetched by the service itself. This is the established pattern in this codebase.
- **Duplicating the bible builder:** Don't copy-paste the bible context building logic. Use a single shared function called from all endpoints.
- **Injecting bible into non-episode projects:** Always guard with `if project.show_id` check. Standalone projects must be completely unaffected.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bible context formatting | Custom per-service formatting | Single `build_bible_context()` helper | Consistency across all 3 services |
| Show data fetching in services | DB queries inside services | Pass `bible_context: str` from endpoints | Services stay DB-agnostic (established pattern) |

## Common Pitfalls

### Pitfall 1: Missing Injection Points
**What goes wrong:** Bible context injected into some services but not all, leading to inconsistent AI behavior between wizards, review, and breakdown.
**Why it happens:** Many service calls are spread across `wizards.py`, `ai_chat.py`, `review.py`, and `breakdown.py` -- easy to miss one.
**How to avoid:** Exhaustive list of all call sites (see "All Injection Points" in Code Examples below). Grep for service imports and method calls after implementation.
**Warning signs:** A wizard knows about the show bible but the review does not.

### Pitfall 2: Empty Bible Block Injection
**What goes wrong:** An empty or near-empty bible context block ("## Series Bible Context\n**Show:** Title\n---") gets injected, wasting tokens and confusing the AI.
**Why it happens:** Checking only for `show_id is not None` without verifying that actual bible content exists.
**How to avoid:** The builder function must check that at least one bible field is non-empty OR duration is set before returning a context string. Otherwise return None.
**Warning signs:** AI responses for episodes of a show with no bible data mention "Series Bible Context" but have no useful information.

### Pitfall 3: Breaking the Wizard Background Task
**What goes wrong:** The `_run_wizard_background` function in `wizards.py` creates a new DB session -- the `build_bible_context` must be called before the background task, or within it using its own session.
**Why it happens:** Background tasks use `SessionLocal()` directly, not the request-scoped session.
**How to avoid:** Two options: (1) call `build_bible_context` in the request handler and pass the string to the background task, or (2) call it in the background task using its own session. Option (1) is cleaner since the bible context is just a string.
**Warning signs:** Bible context is None in wizard output despite the show having bible data.

### Pitfall 4: Breakdown Service Has Its Own DB Session
**What goes wrong:** `breakdown_service.extract()` takes `(db, project_id)` not a project object. The endpoint handler has the project, but the service builds its own extraction context from DB.
**Why it happens:** `BreakdownService._build_extraction_context` does its own DB queries.
**How to avoid:** For breakdown, the endpoint handler should build the bible context string and pass it to `extract()` as an additional parameter. The service then prepends it to the user prompt in `_build_user_prompt()` or passes it to `_call_ai_extraction()`.
**Warning signs:** Breakdown extracts elements without considering show bible characters.

### Pitfall 5: _get_project_context Duplication
**What goes wrong:** `_get_project_context` is defined identically in both `wizards.py` and `ai_chat.py`. Changes to one must be mirrored in the other.
**Why it happens:** Historical copy-paste of the context builder.
**How to avoid:** Add `bible_context` parameter to BOTH copies. Consider extracting to a shared module (but that's a refactor beyond this phase's scope).
**Warning signs:** Wizard calls include bible context but chat calls do not (or vice versa).

## Code Examples

### All Injection Points (Complete List)

**Review endpoint (`review.py`):**
- `review_section()` -- calls `openai_service.review_section()`. Must lookup show, build bible, pass to service.

**Wizard endpoints (`wizards.py`):**
- `_get_project_context()` -- helper that calls `template_ai_service._build_project_context()`. Add `bible_context` param.
- `_run_wizard_background()` -- background task. Bible context string must be passed as parameter from the request handler (since it uses its own DB session).
- `run_wizard()` -- entry point. Fetch bible context here, pass to background task.

**AI Chat endpoints (`ai_chat.py`):**
- `_get_project_context()` -- DUPLICATE of the one in wizards.py. Same change needed.
- Multiple endpoints calling: `chat_with_action()`, `chat_respond()`, `chat_respond_stream()`, `chat_action_stream_message()`, `fill_blanks()`, `give_notes()`, `analyze_structure()`, `wizard_generate()` (YOLO mode).
- All these endpoints first call `_get_project_context()` then pass to service. The bible context can be threaded through `_get_project_context()`.

**Breakdown endpoints (`breakdown.py`):**
- `trigger_extraction()` -- calls `breakdown_service.extract()`. Must lookup show, build bible, pass to service.

### Bible Context in template_ai_service._build_project_context
```python
def _build_project_context(
    self,
    project_data: Dict,
    template_id: str,
    list_items: Optional[Dict[str, list]] = None,
    project_title: Optional[str] = None,
    bible_context: Optional[str] = None,
) -> str:
    template = get_template(template_id)
    context_parts = []

    if bible_context:
        context_parts.append(bible_context)
        context_parts.append("---")

    if project_title:
        context_parts.append(f"Project: {project_title}")
    context_parts.append(f"Template: {template['name']}")
    # ... rest unchanged
```

### Bible Context in openai_service._get_system_prompt
```python
def _get_system_prompt(self, framework: Framework, section_type: SectionType, bible_context: Optional[str] = None) -> str:
    # ... existing framework_context and section_context ...

    base_prompt = f"""{framework_context[framework]}
        {section_context[section_type]}
        # ... existing instructions ...
    """

    if bible_context:
        return f"{bible_context}\n---\n{base_prompt}"
    return base_prompt
```

### Bible Context in breakdown_service
```python
async def extract(self, db: Session, project_id: UUID, bible_context: Optional[str] = None) -> database.BreakdownRun:
    # ... existing code ...
    ctx = self._build_extraction_context(db, project_id)
    # ... validation ...
    response = await self._call_ai_extraction(ctx, bible_context=bible_context)
    # ...

async def _call_ai_extraction(self, ctx: ExtractionContext, bible_context: Optional[str] = None) -> ExtractionResponse:
    user_prompt = self._build_user_prompt(ctx)
    if bible_context:
        user_prompt = f"{bible_context}\n---\n{user_prompt}"
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    # ...
```

### Wizard Background Task Pattern
```python
async def _run_wizard_background(
    run_id, project_id, template_id: str,
    wizard_type: str, config: dict, phase: str, owner_id: str,
    bible_context: str = None,  # NEW: passed as string, no DB needed
):
    db = SessionLocal()
    try:
        # ...
        project_context = _get_project_context(db, project, bible_context=bible_context)
        result = await template_ai_service.wizard_generate(
            wizard_type=wizard_type,
            config=config,
            project_context=project_context,
            template_id=template_id,
        )
        # ...
```

### Test Pattern: Verify Bible in Prompt
```python
@patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
async def test_extraction_includes_bible_context(self, mock_ai, db_session):
    """When project has show_id, extraction prompt includes bible content."""
    # Setup show with bible
    show = ShowModel(owner_id=MOCK_USER_ID, title="Test Show",
                     bible_characters="Walter White", episode_duration_minutes=44)
    db_session.add(show)
    db_session.flush()

    # Setup project linked to show
    project_id, scene_ids = _setup_project_with_screenplay(db_session)
    project = db_session.query(Project).get(project_id)
    project.show_id = str(show.id)
    db_session.commit()

    mock_ai.return_value = _mock_extraction_response([])

    bible_ctx = build_bible_context(db_session, project)
    await breakdown_service.extract(db_session, project_id, bible_context=bible_ctx)

    # Verify bible content appears in the prompt
    call_args = mock_ai.call_args
    messages = call_args.kwargs["messages"]
    user_prompt = messages[1]["content"]
    assert "Series Bible Context" in user_prompt
    assert "Walter White" in user_prompt
    assert "44 minutes" in user_prompt
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No bible context | Bible auto-injected for episodes | Phase 41 (this phase) | AI generates episode-aware content |
| Standalone-only prompts | Show-aware prompts for episodes | Phase 41 (this phase) | AI respects show bible and duration |

## Open Questions

1. **Where to place `build_bible_context()` helper?**
   - What we know: It needs to be importable from multiple endpoint files (wizards.py, ai_chat.py, review.py, breakdown.py).
   - Options: (a) New file like `backend/app/utils/bible_context.py`, (b) Add to existing `backend/app/api/endpoints/shows.py`, (c) Add to a shared endpoint utilities module.
   - Recommendation: Option (a) -- a small utility module keeps it cleanly separated and importable from any endpoint. This follows the pattern of `backend/app/utils/validators.py`.

2. **Should we refactor the duplicated `_get_project_context()` in wizards.py and ai_chat.py?**
   - What we know: Both are identical. Adding bible_context to both is needed.
   - Recommendation: Add the parameter to both for now. Refactoring to a shared location is a good idea but out of scope for BIBL-04.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | implicit (pytest discovers under app/tests/) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_bible_injection.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BIBL-04a | Bible context built correctly from Show model | unit | `pytest app/tests/test_bible_injection.py::TestBuildBibleContext -x` | No -- Wave 0 |
| BIBL-04b | Bible context is None for standalone projects (no show_id) | unit | `pytest app/tests/test_bible_injection.py::TestBuildBibleContext::test_standalone_returns_none -x` | No -- Wave 0 |
| BIBL-04c | Bible context is None when all bible fields empty and no duration | unit | `pytest app/tests/test_bible_injection.py::TestBuildBibleContext::test_empty_bible_returns_none -x` | No -- Wave 0 |
| BIBL-04d | template_ai_service._build_project_context prepends bible when provided | unit | `pytest app/tests/test_bible_injection.py::TestTemplateAIBibleInjection -x` | No -- Wave 0 |
| BIBL-04e | openai_service.review_section accepts and uses bible_context | unit | `pytest app/tests/test_bible_injection.py::TestOpenAIBibleInjection -x` | No -- Wave 0 |
| BIBL-04f | breakdown_service.extract includes bible in extraction prompt | unit | `pytest app/tests/test_bible_injection.py::TestBreakdownBibleInjection -x` | No -- Wave 0 |
| BIBL-04g | Wizard background task threads bible context through | unit | `pytest app/tests/test_bible_injection.py::TestWizardBibleInjection -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_bible_injection.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_bible_injection.py` -- covers BIBL-04 (all sub-requirements)
- [ ] `backend/app/utils/bible_context.py` -- shared helper (new file, covered by tests)

## Sources

### Primary (HIGH confidence)
- Direct code reading of `backend/app/services/template_ai_service.py` -- all service methods and signatures
- Direct code reading of `backend/app/services/openai_service.py` -- review_section and _get_system_prompt signatures
- Direct code reading of `backend/app/services/breakdown_service.py` -- extract pipeline and _build_user_prompt
- Direct code reading of `backend/app/api/endpoints/wizards.py` -- _get_project_context and _run_wizard_background patterns
- Direct code reading of `backend/app/api/endpoints/ai_chat.py` -- _get_project_context duplicate and all service calls
- Direct code reading of `backend/app/api/endpoints/review.py` -- review_section call pattern
- Direct code reading of `backend/app/api/endpoints/breakdown.py` -- trigger_extraction call pattern
- Direct code reading of `backend/app/models/database.py` -- Show model with bible columns, Project model with show_id FK
- Direct code reading of `backend/app/api/endpoints/shows.py` -- bible endpoint patterns
- Direct code reading of `backend/app/tests/conftest.py` -- test infrastructure (SQLite, fixtures)
- Direct code reading of `backend/app/tests/test_breakdown_service.py` -- mock AI test patterns
- Direct code reading of `backend/app/tests/test_shows_api.py` -- show/bible test patterns

### Secondary (MEDIUM confidence)
- None needed -- all findings derived from direct code reading

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, modifying existing code only
- Architecture: HIGH - patterns directly observed in codebase (Optional[str] threading, endpoint-builds-context-service-uses-it)
- Pitfalls: HIGH - identified from direct code analysis (duplicated _get_project_context, background task session, breakdown's own DB queries)

**Research date:** 2026-03-24
**Valid until:** indefinite (internal codebase patterns, not external library versions)
