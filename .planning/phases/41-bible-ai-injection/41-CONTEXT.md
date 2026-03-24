# Phase 41: Bible AI Injection - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase modifies AI generation for episodes to automatically prepend show bible content and target episode duration into prompts. Standalone film projects (show_id=NULL) are completely unaffected. No UI changes.

</domain>

<decisions>
## Implementation Decisions

### Injection Point
- Inject bible context in `template_ai_service.py` → `_build_project_context()` method
- Also inject into `openai_service.py` → `review_section()` method (agent reviews)
- Also inject into `breakdown_service.py` for breakdown extraction
- Bible context injected as a prefix block before the existing project context

### What Gets Injected
When `project.show_id` is not None:
1. Fetch show record from DB (title, episode_duration_minutes)
2. Fetch bible via `GET /api/shows/{show_id}/bible` or direct DB query
3. Build bible block:
```
## Series Bible Context
**Show:** {show_title}
**Target Episode Duration:** {episode_duration_minutes} minutes

### Characters
{bible_characters}

### World & Setting
{bible_world_setting}

### Season Arc
{bible_season_arc}

### Tone & Style
{bible_tone_style}
---
```
4. Only include non-empty bible fields
5. If no bible fields filled and no duration set → skip injection (no empty context)

### How to Pass Bible Context to Services
- Services receive `project_id` or `project` object — add optional `show_id` parameter
- Services look up show and bible from DB when show_id is present
- Alternative: pass bible_context as optional string parameter to service methods (cleaner, no DB coupling in service)
- Decision: Pass `bible_context: Optional[str] = None` to service methods — keeps services DB-agnostic

### Who Builds Bible Context
- Build bible context in the API endpoint handlers (they already have DB access)
- Pass it down to service methods as an optional string
- This keeps the separation: endpoints do DB reads, services do AI logic

### Affected Services + Methods
1. `template_ai_service.py` → `_build_project_context()` — prepend bible_context if provided
2. `template_ai_service.py` → `wizard_generate()` — accept and pass bible_context
3. `openai_service.py` → `_get_system_prompt()` — prepend bible context to system prompt
4. `openai_service.py` → `review_section()` — accept and pass bible_context
5. `breakdown_service.py` → extraction call — accept and pass bible_context

### API Endpoint Changes
- Review endpoint: fetch show bible if project.show_id is set, pass to openai_service
- Template AI endpoints (wizard_generate, fill_blanks, etc.): fetch show bible if project.show_id is set
- Breakdown extraction endpoint: same pattern

### Tests
- Test that bible context appears in the prompt when project has show_id
- Test that standalone projects (no show_id) generate prompts without bible context
- Mock the AI call — test prompt construction, not AI output

### Claude's Discretion
- Exact formatting of bible block headers
- Whether to use separator lines (---) between bible and project context

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `template_ai_service._build_project_context()` — inject here as prefix
- `openai_service._get_system_prompt()` — prepend bible to system prompt
- `database.Show` model — has bible columns and episode_duration_minutes
- Existing DB session patterns in endpoints

### Established Patterns
- Services receive context as strings, not DB objects
- Endpoint handlers do DB lookups, pass data to services
- Optional[str] = None pattern for optional parameters throughout codebase

### Integration Points
- `backend/app/api/endpoints/sections.py` or review.py — review calls
- `backend/app/services/template_ai_service.py` — generation
- `backend/app/services/openai_service.py` — review
- `backend/app/services/breakdown_service.py` — extraction

</code_context>

<specifics>
## Specific Ideas

- Bible injection is silent/automatic — no UI toggle needed
- If all bible fields are empty AND no duration set, skip the bible block entirely to avoid noise

</specifics>

<deferred>
## Deferred Ideas

- Per-section bible toggle — not in requirements
- Bible context in shotlist generation — not in requirements (BIBL-04 specifies screenplay + agent review + breakdown)

</deferred>
