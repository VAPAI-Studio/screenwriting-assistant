# Phase 2: Pipeline Composer Service - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `pipeline_composer.py` — an AI service that analyzes all user agents and produces a stable, deterministic mapping of agents to pipeline steps. The service uses hash-based caching at temperature=0 for determinism, sets `pipeline_dirty=True` on semantic agent changes, and stores results in `agent_pipeline_maps`. Requirements: COMP-01, COMP-03.

</domain>

<decisions>
## Implementation Decisions

### Mapping target scope
- Map agents to **generation-capable subsections only** — those with `ui_pattern` containing "wizard" (wizard, wizard_with_chat)
- Target steps for short_movie template: `idea_wizard`, `scene_wizard`, `script_writer_wizard`
- **Exclude** `import_project` — it's a utility/alignment step, not a creative generation step
- **Dynamic resolution**: composer reads template JSON at runtime, resolves `$ref` references, and extracts wizard-pattern subsections. Adapts automatically if templates change.
- Filter mechanism: use existing `ui_pattern` field (contains "wizard"), no new template schema flags needed

### Batch composition strategy
- **Single batch AI call** per composition: one prompt with ALL agents + ALL target steps. AI sees the full picture for intelligent distribution.
- **Cap at 5 agents per batch call**. If user has >5 agents, split into multiple batch calls.
- **Simple merge** across batches: concatenate results, no cross-batch reconciliation or deduplication needed (agents are different across batches, so results are naturally non-overlapping)
- AI response format: **flat list** of `{agent_id, phase, subsection_key, confidence, rationale}` tuples. Maps directly to `AgentPipelineMap` rows.

### Confidence storage policy
- **Store all mappings** the AI returns, regardless of confidence score. Downstream consumers (Phase 7 tree view, Phase 8 YOLO) filter at read time.
- Confidence scale: **0.0 to 1.0** float. 0.0 = no relevance, 1.0 = perfect match.
- **Rationale always required** for every mapping — useful for Phase 7 tree view tooltips and debugging mapping quality.
- **Full replace** on each re-composition: delete all existing mappings for the owner, insert fresh results. Simple, deterministic, avoids stale data.

### Agent context in composition prompt
- Include per-agent: **system_prompt_template + description + agent_type**. Type serves as a hint, not a binding constraint.
- Include per-step: **subsection name + description** from the template JSON. Descriptions already explain what each step does.
- **Do NOT include** book titles, tags, or personality in the mapping prompt — keeps prompt lean.

### Dirty flag and cache key
- Cache key: `hash(system_prompt_template + description + agent_type)` for all agents combined. Any semantic field change invalidates cache.
- Dirty flag triggers on: `system_prompt_template`, `description`, **and** `agent_type` changes (expanded from original SC3 which only specified prompt + description). Consistent with cache key.
- Cosmetic fields (name, color, icon) still do NOT trigger re-composition.

### Claude's Discretion
- Exact composition prompt engineering and structure
- Hash algorithm choice for cache key
- Error handling and retry logic for failed AI calls
- Logging strategy and observability

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ai_provider.chat_completion()`: Unified provider wrapper supporting both OpenAI and Anthropic, with `json_mode=True` and `temperature` parameter. Directly usable for the composition call.
- `get_template(template_id)`: Loads template JSON with `$ref` resolution. Use to dynamically discover wizard-pattern subsections.
- `AgentPipelineMap` model (Phase 1): Already built with `owner_id`, `agent_id`, `phase`, `subsection_key`, `confidence`, `rationale`, `pipeline_dirty` columns and cascade delete to Agent.
- `PipelineMapEntry` / `PipelineMapResponse` Pydantic schemas (Phase 1): Ready for validation.

### Established Patterns
- Singleton service pattern: `agent_service = AgentService()` — follow same pattern for `pipeline_composer`.
- AI calls use `chat_completion()` with system/user message pairs and `json_mode=True` for structured output.
- Config values in `config.py` via `pydantic_settings.BaseSettings`.
- Agent model has `system_prompt_template`, `description`, `agent_type`, `personality`, `color`, `icon`, `name`, `tags_filter` fields.

### Integration Points
- `Agent` model query: fetch all active agents for an `owner_id` (pattern exists in `agent_service._orchestrate`)
- `AgentPipelineMap` table: write composition results via SQLAlchemy ORM
- Template system: `backend/app/templates/` JSON files with `get_template()` loader
- `config.py`: add any new settings (e.g., batch size cap)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-pipeline-composer-service*
*Context gathered: 2026-03-11*
