# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)

## Phases

<details>
<summary>✅ v1.0 Agent Orchestration Pipeline (Phases 1-8) — SHIPPED 2026-03-12</summary>

- [x] **Phase 1: DB Foundation** — Create `agent_pipeline_maps` table, SQLAlchemy model, and Pydantic schemas (completed 2026-03-11)
- [x] **Phase 2: Pipeline Composer Service** — Build `pipeline_composer.py` with AI mapping, hash-based cache, and dirty-flag gating (completed 2026-03-11)
- [x] **Phase 3: Pipeline Map API and CRUD Wiring** — Expose GET endpoint and wire agent CRUD to trigger re-composition via BackgroundTasks (completed 2026-03-11)
- [x] **Phase 4: Async Safety and Session Isolation** — Fix shared DB session bug in `run_multi_agent_review` for safe concurrent use (completed 2026-03-11)
- [x] **Phase 5: Agent Review Middleware** — Build `agent_review_middleware.py` with parallel fan-out, merge AI call, and pass-through bypass (completed 2026-03-12)
- [x] **Phase 6: Wizard Injection** — Inject review middleware into `wizards.py` generation path and surface `agents_consulted` metadata (completed 2026-03-12)
- [x] **Phase 7: Frontend Pipeline Tree** — Build `AgentPipelineTree.tsx` collapsible tree component embedded in `AgentManager.tsx` (completed 2026-03-12)
- [x] **Phase 8: YOLO Integration and Token Budget** — Wire YOLO auto-generation through review middleware with configurable agent budgets (completed 2026-03-12)

</details>

<details>
<summary>✅ v2.0 Script Breakdown (Phases 9-16) — SHIPPED 2026-03-18</summary>

- [x] **Phase 9: Data Foundation** — Migration, SQLAlchemy models, Pydantic schemas for breakdown tables and staleness column (completed 2026-03-13)
- [x] **Phase 10: Breakdown API** — CRUD endpoints for elements, scene links, manual creation, summary, and extraction trigger (completed 2026-03-13)
- [x] **Phase 11: AI Extraction Service** — Structured output extraction with deduplication, user-modified protection, and scene link reconciliation (completed 2026-03-13)
- [x] **Phase 12: Staleness Hooks** — Wire save/generate paths to set breakdown_stale flag and clear it on re-extraction (completed 2026-03-14)
- [x] **Phase 13: Breakdown Page** — Dedicated frontend page with category tabs, master lists, inline editing, and scene chips (completed 2026-03-18)
- [x] **Phase 14: Reverse Sync** — User-initiated actions to push breakdown elements back to project data (completed 2026-03-18)
- [x] **Phase 15: Phase 13 Documentation Closure & UI-05 Fix** — Formal verification, UI-07/UI-08 documentation, scene chip route fix (completed 2026-03-18)
- [x] **Phase 16: Staleness Bug & Migration Upgrade Path** — Fix scene_wizard staleness hook; delta migration for Docker auto-upgrade (completed 2026-03-18)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DB Foundation | v1.0 | 3/3 | Complete | 2026-03-11 |
| 2. Pipeline Composer Service | v1.0 | 2/2 | Complete | 2026-03-11 |
| 3. Pipeline Map API and CRUD Wiring | v1.0 | 2/2 | Complete | 2026-03-11 |
| 4. Async Safety and Session Isolation | v1.0 | 1/1 | Complete | 2026-03-11 |
| 5. Agent Review Middleware | v1.0 | 2/2 | Complete | 2026-03-12 |
| 6. Wizard Injection | v1.0 | 1/1 | Complete | 2026-03-12 |
| 7. Frontend Pipeline Tree | v1.0 | 3/3 | Complete | 2026-03-12 |
| 8. YOLO Integration and Token Budget | v1.0 | 2/2 | Complete | 2026-03-12 |
| 9. Data Foundation | v2.0 | 2/2 | Complete | 2026-03-13 |
| 10. Breakdown API | v2.0 | 2/2 | Complete | 2026-03-13 |
| 11. AI Extraction Service | v2.0 | 3/3 | Complete | 2026-03-13 |
| 12. Staleness Hooks | v2.0 | 2/2 | Complete | 2026-03-14 |
| 13. Breakdown Page | v2.0 | 3/3 | Complete | 2026-03-18 |
| 14. Reverse Sync | v2.0 | 2/2 | Complete | 2026-03-18 |
| 15. Phase 13 Doc Closure & UI-05 Fix | v2.0 | 1/1 | Complete | 2026-03-18 |
| 16. Staleness Bug & Migration Upgrade | v2.0 | 1/1 | Complete | 2026-03-18 |
