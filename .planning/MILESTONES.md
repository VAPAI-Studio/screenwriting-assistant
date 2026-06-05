# Milestones

## v5.0 API Key Management & Gateway (Shipped: 2026-04-01)

**Phases completed:** 2 phases (43-44), 4 plans

**Key accomplishments:**

1. API key management — users create named API keys with optional scopes and expiry dates; secure hashing and one-time secret reveal
2. API gateway & docs — unified auth middleware accepting API keys, enhanced API documentation
3. Per-key usage tracking — atomic SQL request-count increment (race-safe), per-key in-memory rate limiter (defaults to 1000 req/hour), last-used timestamps
4. Usage stats UI — request count and last-used display on the API keys settings page with 30-second auto-refresh polling

> Note: This index skips v3.1–v4.2 (file was not maintained between v3.0 and v5.0). See ROADMAP.md for the complete shipped-milestone list.

---

## v3.0 Shotlist & Production Breakdown (Shipped: 2026-03-20)

**Phases completed:** 9 phases, 14 plans, 0 tasks

**Key accomplishments:**

- (none recorded)

---

## v2.0 Script Breakdown (Shipped: 2026-03-18)

**Phases completed:** 8 phases (9-16), 16 plans
**Timeline:** 2026-03-01 → 2026-03-18 (17 days)
**Files changed:** 91 files, 16,745 insertions

**Key accomplishments:**

1. AI extraction service — GPT-4/Claude structured output extraction identifies 5 production element categories (characters, locations, props, wardrobe, vehicles) from screenplay content with deduplication and scene link reconciliation
2. Full CRUD REST API — 7 breakdown endpoints with 22 integration tests; scene link management; extraction trigger; summary with staleness and category counts
3. Breakdown page — React frontend with category tabs, master lists, inline editing, scene chips with deep-link navigation, Add Element dialog, empty state CTA
4. Staleness hooks — all script save/generate paths set `breakdown_stale=True`; re-extraction clears it atomically; user_modified elements preserved across re-extractions
5. Reverse sync — user-initiated "Add to Characters" creates ListItem in story.characters phase; idempotent across calls
6. Migration upgrade path — `delta/001_breakdown_tables.sql` lets existing Docker deployments apply v2.0 schema on restart without volume wipe

**Tech debt carried forward:**

- Latent `selectinload` result discarded in create/update write endpoints (masked on new elements)
- React Query `LIST_ITEMS` cache not invalidated after reverse sync (5-min lag)
- 14/16 phases have partial Nyquist compliance; Phase 11 missing VALIDATION.md

---

## v1.0 Agent Orchestration Pipeline (Shipped: 2026-03-12)

**Phases completed:** 8 phases (1-8), 16 plans

**Key accomplishments:**

1. Multi-agent pipeline system — AI maps user-created agents to generation steps; agents review wizard output in parallel via asyncio.gather
2. Agent review middleware — parallel fan-out, AI merge call, zero-impact bypass when no agents mapped; injected into wizards.py generation path
3. Frontend pipeline tree — collapsible AgentPipelineTree.tsx showing per-step agent assignments with per-agent toggles
4. YOLO auto-generation — agent reviews fire through same middleware in YOLO mode with configurable token budgets

---
