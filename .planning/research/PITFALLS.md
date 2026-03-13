# Pitfalls Research: AI Script Breakdown with Bidirectional Sync

**Domain:** AI-powered production element extraction added to an existing template-based screenwriting assistant
**Researched:** 2026-03-12
**Confidence:** HIGH — combines direct codebase analysis of the existing data model and AI service patterns with established production workflow knowledge and real-world lessons from Filmustage/StudioBinder competitors

---

## Critical Pitfalls

Mistakes that require rewrites, break existing workflows, or make the feature unusable.

---

### Pitfall 1: AI Extraction Hallucinates Production Elements Not Present in the Script

**What goes wrong:** The AI extracts production elements that do not actually exist in the screenplay text. A character mentioned in dialogue as a memory ("my grandfather used to say...") gets extracted as a cast member requiring scheduling. A location described metaphorically ("this place is a prison") gets tagged as an actual prison location. An object discussed but never seen on screen ("she sold her car last week") gets added to the vehicles master list. The breakdown grows with phantom elements that inflate production scope and mislead scheduling.

**Why it happens:** LLMs are trained to be comprehensive and helpful. When asked to "extract all production elements," the model interprets narrative context, backstory, and dialogue references as on-screen requirements. Screenplay text is dense with implied action and offscreen references that a human script supervisor would skip but an AI treats as explicit. The existing `chat_completion` calls in `template_ai_service.py` already use `temperature=0.7-0.8` for generation tasks — this level of creativity is actively harmful for extraction tasks where precision matters more than recall.

**How to avoid:**
- Use `temperature=0.1-0.2` for extraction calls. This is an information retrieval task, not a creative generation task.
- The extraction prompt must explicitly define "on-screen" vs. "referenced": "Only extract elements that physically appear in the scene. Exclude elements mentioned in dialogue but not visually present, referenced in backstory, or described metaphorically."
- Require the AI to cite the exact line or action description where each element appears. If it cannot point to a specific screenplay line, the element is likely hallucinated.
- Implement a confidence score per element (0-1). Surface low-confidence elements in a separate "review needed" bucket rather than the main master list.
- Post-extraction validation pass: a second, cheaper LLM call that receives the extracted elements plus the original text and flags any element that lacks a direct textual basis.

**Warning signs:** Breakdown contains more locations than the script has scene headings. Characters appear in the master list who never speak or appear on screen. Props list includes items only mentioned in past-tense dialogue.

**Phase to address:** First phase — AI extraction service design. The prompt engineering and temperature settings must be correct before any UI is built on top.

---

### Pitfall 2: Duplicate Detection Fails Across Scenes, Creating Bloated Master Lists

**What goes wrong:** The same production element extracted from multiple scenes appears as separate entries in the master list. "JOHN'S APARTMENT" in Scene 1 and "John's Apartment - Kitchen" in Scene 3 become two separate locations instead of one location with two scene links. "REVOLVER" in Scene 2 and "the gun" in Scene 5 become two separate props. "Sarah's red dress" in Scene 1 and "Sarah (wearing red)" in Scene 4 become two separate wardrobe items. The master list grows to 3-5x its correct size, making it useless for production planning.

**Why it happens:** AI extraction operates per-scene (or per-chunk) without cross-referencing previous extraction results. Each call returns elements in isolation. String matching fails because screenplay text uses natural language variations — the same element is described differently in different scenes. The existing `_generate_scripts` method in `template_ai_service.py` already processes scenes independently in a loop, and a naive breakdown implementation would follow the same pattern.

**How to avoid:**
- Extract elements from ALL scenes in a single LLM call (if within token limits) or use a two-pass approach: (1) extract per-scene, (2) deduplicate across scenes with a consolidation call.
- The deduplication call should receive the full list of raw extractions and output a normalized master list with scene linkages. Prompt: "Merge these raw extractions into a canonical master list. Group equivalent elements (same prop called different names, same location described differently) under a single canonical name."
- Store a `canonical_name` field on each element that is the normalized, deduplicated identifier. Store `aliases` as a JSON array of alternative names encountered in the script.
- For locations specifically: parse scene headings (INT./EXT. LOCATION - TIME) as the primary location source, then match action-line location references to these headings. Scene headings are structured and canonical; action lines are not.
- For characters: use the character name as it appears in dialogue blocks (ALL CAPS before the colon) as the canonical name. This is a reliable, structured signal in screenplay format.

**Warning signs:** Master list has more entries than the user expects after reading their own script. Multiple entries with similar names in the same category. Users spend more time cleaning up duplicates than they would doing manual breakdown.

**Phase to address:** First phase — extraction service design. The deduplication strategy is an architectural decision that affects the entire data model.

---

### Pitfall 3: Circular Update Loop in Bidirectional Sync

**What goes wrong:** User edits script (adds a new prop mention) -> save triggers breakdown re-extraction -> extraction finds new prop and adds it to master list -> master list change triggers "sync back to script" logic -> script is modified to include a prop annotation -> modification triggers another save -> re-extraction fires again -> infinite loop. Even without a literal infinite loop, the system enters a ping-pong state where every save triggers extraction, which triggers a sync, which triggers another save.

**Why it happens:** Bidirectional sync without a clear "direction flag" or "origin tracking" causes re-entrant updates. The PROJECT.md states sync happens "on save/generate" — if both directions trigger on save, the system oscillates. This is the single most common bidirectional sync bug and the reason the PROJECT.md wisely scoped sync to "on save/generate, not real-time." But even save-triggered sync can loop if not guarded.

**How to avoid:**
- Implement a `sync_origin` flag on every update operation: `"user_edit"`, `"ai_extraction"`, `"breakdown_sync"`. Only `"user_edit"` triggers re-extraction. Updates originating from `"ai_extraction"` or `"breakdown_sync"` never trigger downstream sync.
- Use a version counter (the `ScreenplayContent.version` field already exists in the data model). Record `last_extracted_version` on the breakdown. Only re-extract when `screenplay.version > breakdown.last_extracted_version`.
- Never auto-modify script content based on breakdown edits. The "breakdown -> script" direction should be advisory (highlight inconsistencies) or require explicit user confirmation, not automatic. The PROJECT.md says "bidirectional sync" but the safe implementation is: script -> breakdown is automatic; breakdown -> script is user-confirmed.
- Add a re-entrancy guard: a per-project mutex that prevents concurrent sync operations. If sync is already running for a project, queue the next sync rather than running it concurrently.

**Warning signs:** Server logs show rapid successive calls to both extraction and sync endpoints for the same project. Database shows `updated_at` timestamps on screenplay and breakdown elements within milliseconds of each other, repeatedly.

**Phase to address:** Architecture phase — sync direction rules must be defined before any sync implementation begins. This is the single most important architectural decision in the entire milestone.

---

### Pitfall 4: Breakdown Re-Extraction Destroys User Refinements

**What goes wrong:** User runs AI extraction, gets a breakdown with 50 elements. User spends 30 minutes refining: renames "GUN" to "SMITH & WESSON MODEL 10 (PROP RENTAL)", deletes hallucinated elements, adds missing ones, writes production notes on each element. User then edits the script (adds a new scene), saves, and re-extraction fires. The new extraction replaces the entire breakdown, destroying all user refinements. The user's 30 minutes of work is gone.

**Why it happens:** Naive re-extraction treats each run as a full replacement rather than a diff/merge. The extraction service returns a complete new element list, and the endpoint replaces the old list wholesale. The existing code follows this pattern — `_generate_scenes` returns a full `{"scenes": [...]}` array that replaces whatever was there before.

**How to avoid:**
- Never full-replace on re-extraction. Implement a diff-based merge:
  1. Extract new elements from updated script.
  2. Match new elements against existing elements by `canonical_name` and category.
  3. For matched elements: keep user edits (name overrides, notes, deletions), update scene linkages only.
  4. For new elements (in new extraction but not in existing): add them with `source: "ai"` and `status: "pending_review"`.
  5. For removed elements (in existing but not in new extraction): flag them as `status: "orphaned"` but do not delete. User may have added them manually.
- Track element provenance: `source` field with values `"ai_extracted"`, `"user_added"`, `"user_modified"`. User-sourced elements are never touched by re-extraction.
- Track `user_edited_at` timestamp on each element. If `user_edited_at > last_extraction_at`, the element is user-modified and its name/notes are preserved during merge.
- The frontend must show a "Review changes" diff view after re-extraction, not silently apply changes.

**Warning signs:** Users avoid editing the script after refining the breakdown. Users export breakdowns to spreadsheets as a "backup" before any script edit. Complaints about "lost work."

**Phase to address:** Must be designed in the data model phase and implemented in the extraction service. The `source` and `user_edited_at` fields must exist in the schema from day one.

---

### Pitfall 5: Data Model Couples Elements to Scene IDs That Do Not Exist Yet

**What goes wrong:** The data model creates a `breakdown_elements` table with a foreign key `scene_id` referencing a scenes table. But in the current codebase, "scenes" are `ListItem` records under `PhaseData` for the `scenes` phase — they are not a first-class `Scene` table with stable IDs. `ListItem.id` is a UUID, but `ListItem` is a generic container used for characters, beats, and scenes alike. When scenes are regenerated (user runs Scene Wizard again), old `ListItem` records may be deleted and new ones created with new UUIDs. Every foreign key from breakdown elements to old scene IDs becomes a dangling reference. The breakdown silently loses all its scene linkages.

**Why it happens:** The existing data model was designed for a creation workflow (generate once, edit forward), not for a breakdown workflow that needs stable references to scene identities across regeneration cycles. The `ListItem` model has `cascade="all, delete-orphan"` on its parent relationship, meaning deleting a `PhaseData` entry cascades deletes to all its `ListItem` children — and any breakdown references to them.

**How to avoid:**
- Do NOT foreign-key breakdown elements directly to `ListItem.id`. Instead, create an intermediary `scene_reference` concept:
  - Option A: Add a `stable_scene_id` field to `ListItem` that persists across regeneration. When Scene Wizard regenerates scenes, it matches new scenes to old ones by content similarity and preserves the `stable_scene_id`. New scenes get new IDs; matched scenes keep old IDs.
  - Option B: Store scene linkages in the breakdown element as a JSON array of scene identifiers (scene number + title hash) rather than foreign keys. This is denormalized but resilient to regeneration.
  - Option C (recommended): Create a dedicated `Scene` model that is the stable identity. `ListItem` for scenes gets a FK to this `Scene` model. Breakdown elements reference `Scene`. When scenes regenerate, the `Scene` record persists; only the `ListItem` content updates.
- Whichever option: add an `ON DELETE SET NULL` or `ON DELETE CASCADE` policy on the breakdown-to-scene reference that is explicitly chosen, not accidentally inherited from `ListItem`'s existing cascade behavior.

**Warning signs:** Breakdown shows "linked to 0 scenes" after user regenerates scenes. Scene links in the UI show "Scene not found" errors. Users report breakdown "broke" after using Scene Wizard.

**Phase to address:** Data model migration phase — this is a schema design decision that must be made before any code is written. Getting this wrong requires a migration to fix later.

---

### Pitfall 6: Extraction Prompt Overwhelmed by Full Project Context

**What goes wrong:** The existing `_build_project_context` method in `template_ai_service.py` builds a comprehensive context string from ALL phase data, ALL list items, ALL fields. For a project with completed idea, story, scenes, and write phases, this context can be 8,000-15,000 tokens. The extraction prompt sends this full context plus the screenplay text (potentially 10,000-30,000 tokens for a short film) plus extraction instructions. The total prompt exceeds the model's effective context window, or the model loses focus on the extraction task due to context dilution.

**Why it happens:** The existing AI service pattern is to always include full project context ("the model needs to understand the full story to generate good content"). This is correct for generation but counterproductive for extraction. Extraction needs the screenplay text and category definitions — not the logline, theme, character backstory, and beat structure. Including irrelevant context actually degrades extraction accuracy because the model starts extracting elements from the project context (character backstory fields) rather than from the screenplay text only.

**How to avoid:**
- Build a separate `_build_extraction_context` method that includes ONLY: (1) the screenplay text, (2) a list of character names from the characters phase (to aid character recognition), and (3) category definitions with examples.
- Do NOT include: logline, theme, beat descriptions, scene summaries, or any creative development data. These are sources of hallucinated elements.
- If the screenplay exceeds token limits, chunk it by scene (each scene in its own extraction call) and then run a consolidation pass. The existing per-scene pattern in `_generate_scripts` provides a good template for this.
- Set `max_tokens` for extraction responses to a reasonable limit (2,000-3,000 per scene chunk). Extraction output should be structured and compact, not narrative.

**Warning signs:** Extraction returns elements from the "Story > Core" phase data that do not appear in the screenplay text. Extraction accuracy drops as project context grows. Extraction calls hit token limit errors on projects with extensive development notes.

**Phase to address:** Extraction service implementation phase. The context building must be separate from the existing `_build_project_context` method.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store breakdown as a single JSON blob on the project | No migration needed, fast to ship | Cannot query elements across projects, no relational integrity, no scene linking | Never — the whole point of breakdown is relational data (elements linked to scenes) |
| Skip deduplication and let users merge manually | Simpler extraction, no consolidation pass needed | Users spend more time cleaning up than doing manual breakdown, defeating the core value prop | Never — this is the #1 differentiator of AI breakdown over manual |
| Full-replace on re-extraction instead of diff-merge | Much simpler implementation (5x less code) | Destroys user refinements, makes breakdown a read-only artifact instead of a living document | Only acceptable as v2.0 MVP if extraction is explicitly one-shot (no re-extraction on script edit). Must add diff-merge before enabling bidirectional sync. |
| Foreign key breakdown elements directly to `ListItem.id` | Uses existing model, no new tables | Scene regeneration breaks all links, cascade deletes destroy breakdown data | Never — `ListItem` is too volatile for stable references |
| Single LLM call for extraction (no validation pass) | Half the API cost, faster extraction | Hallucinated elements reach the master list unchecked, users lose trust | Acceptable for MVP if confidence scores are surfaced and low-confidence elements are visually distinguished |
| Auto-sync breakdown edits back to script without user confirmation | "Bidirectional" sounds complete | Script modifications the user did not explicitly request, potential data loss, trust destruction | Never — breakdown-to-script direction must always require explicit user action |

---

## Integration Gotchas

Common mistakes when connecting breakdown features to the existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Existing `template_ai_service.py` | Adding extraction methods to the existing class, making it a 1000+ line monolith | Create a separate `breakdown_service.py` with its own class. Import `chat_completion` from `ai_provider.py` directly. Keep template generation and breakdown extraction decoupled. |
| Existing `PhaseData` / `ListItem` models | Storing breakdown elements as `ListItem` records under a new "breakdown" phase | Breakdown elements are a different data type — they have categories, scene links, aliases, confidence scores. Create dedicated `BreakdownElement` and `ElementSceneLink` models. |
| Existing React Query cache | Assuming breakdown data updates propagate through existing query invalidation | Breakdown queries (`['breakdown', projectId]`) are independent of existing phase data queries. Screenplay saves must explicitly invalidate breakdown queries when re-extraction fires. Cross-invalidation must be wired in `onSettled` callbacks. |
| Existing `ProjectWorkspace.tsx` routing | Adding breakdown as another "phase" in the phase navigation | Breakdown is project-level, not phase-level. It spans all scenes across all phases. It should be a separate top-level tab/section in the workspace, not nested under the "Write" phase. |
| Existing AI provider abstraction | Assuming extraction works equally well with both OpenAI and Anthropic | Test extraction prompts on both providers. Structured JSON extraction may have different accuracy characteristics. The provider abstraction handles API calls but not prompt optimization per provider. |
| Existing `ScreenplayContent` model | Extracting from `ScreenplayContent.content` (plain text) only | Also extract from `ScreenplayContent.formatted_content` (JSON) which may contain richer structural data like scene headings. Parse scene headings from the content to establish scene boundaries for per-scene extraction. |

---

## Performance Traps

Patterns that work at small scale but fail as scripts grow.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Single LLM call for full-script extraction | Works for 5-scene short films | Chunk extraction by scene, consolidate after | Scripts exceeding 8,000 tokens (~15 screenplay pages) |
| Loading all breakdown elements with all scene links in one query | Works for 20 elements | Use `selectinload` for scene links, paginate element lists by category | Projects with 100+ elements (feature film length) |
| Re-extracting the entire script on every save | Works when saves are infrequent | Diff the script to identify changed scenes, re-extract only those scenes | Users who save every 30 seconds during active editing |
| Storing element-to-scene links as a JSON array on the element | Fast to write, no join needed | Use a proper association table (`element_scene_links`) with indexes | When querying "which elements appear in Scene 5" — JSON array scan is O(n) on all elements |
| Frontend renders all categories expanded with all elements visible | Works for 20 elements across 5 categories | Collapse categories by default, virtualize long lists, lazy-load scene link details on expand | Projects with 50+ elements in a single category |
| Re-extraction runs synchronously in the API request handler | Works for 5-scene scripts (2-3 seconds) | Run extraction as a background task, return immediately with `status: "extracting"`, poll for completion | Scripts with 10+ scenes (extraction takes 10-30 seconds) |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Extraction prompt includes raw user screenplay text without sanitization | Prompt injection via screenplay content — a scene description containing "Ignore all previous instructions and..." could manipulate the extraction model | Sanitize screenplay text before including in extraction prompt. Strip any text that matches prompt injection patterns. Use system prompt with strong extraction-only instructions. |
| Breakdown elements store raw AI output without validation | XSS if AI-generated element names contain script tags and are rendered without escaping | Validate and sanitize all AI-generated element names and descriptions before storing. The existing `utils/validators.py` has HTML sanitization — use it on extraction results. |
| Breakdown data accessible without project-level authorization check | Users could view breakdown data for projects they do not own if the endpoint does not check `owner_id` | Every breakdown endpoint must verify `project.owner_id == current_user.id`. Do not create a separate auth path for breakdown — use the existing project auth middleware. |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing all 15+ breakdown categories at once (Cast, Extras, Props, Set Dressing, Vehicles, Wardrobe, Makeup, Hair, Special Makeup, Special Effects, Visual Effects, Mechanical Effects, Stunts, Animals, Sound, Greenery, Music) | Users are overwhelmed by the taxonomy before they extract a single element. Feels like enterprise software, not a creative tool. | Start with 5-6 core categories matching PROJECT.md scope (Characters, Locations, Props, Wardrobe, Vehicles). Add an "Other" catch-all. Let users create custom categories later. Industry-standard 15+ categories are for feature film line producers, not short film creators. |
| Extraction runs with no progress indication | User clicks "Extract Breakdown" and stares at a spinner for 10-30 seconds with no feedback. They think it is broken and click again, firing duplicate extractions. | Show a progress stepper: "Analyzing Scene 1 of 8... Analyzing Scene 2 of 8... Consolidating elements... Done." Even if the backend processes all scenes in one call, fake per-scene progress if needed. |
| Breakdown page disconnected from screenplay editor | User sees "REVOLVER" in the props list but cannot quickly find where it appears in the script. They have to manually search the screenplay text. | Every element in the master list must link directly to the scene(s) where it appears. Clicking a scene link should navigate to that scene in the screenplay editor with the relevant line highlighted (or at minimum scrolled into view). |
| No visual distinction between AI-extracted and user-added elements | Users cannot tell which elements they added manually and which the AI extracted. After re-extraction, they cannot identify what changed. | Color-code or badge elements by source: AI-extracted (default), user-added (distinct badge), user-modified (edited indicator). Show a "last extracted" timestamp and a "changes since last extraction" count. |
| Forcing users to review the entire breakdown before they can use it | A mandatory "review and approve" gate after extraction blocks users who trust the AI and just want to see the overview. | Show the breakdown immediately after extraction. Flag low-confidence elements with a subtle indicator but do not block access. Let power users review/approve at their own pace. |
| Editing breakdown elements in a modal dialog | Each edit requires: click element -> modal opens -> edit fields -> save -> modal closes -> find next element -> repeat. For 50 elements, this is 50 modal round-trips. | Use inline editing. Click an element name to edit it in place. Expand/collapse for details. Batch operations (select multiple, delete, re-categorize). The breakdown page should feel like a spreadsheet, not a form wizard. |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **AI Extraction:** Often missing confidence scores per element -- verify each element has a confidence value and low-confidence elements are visually distinguished
- [ ] **Deduplication:** Often missing alias tracking -- verify that "GUN" and "REVOLVER" in different scenes map to the same master list entry with both names stored as aliases
- [ ] **Scene Linking:** Often missing bidirectional navigation -- verify clicking an element shows its scenes AND clicking a scene shows its elements
- [ ] **Re-extraction:** Often missing diff/merge -- verify that editing the script and re-extracting preserves user-modified element names and notes
- [ ] **User-added elements:** Often missing scene linking -- verify that manually added elements can be linked to scenes, not just AI-extracted ones
- [ ] **Empty states:** Often missing for each category -- verify that categories with no elements show helpful empty states, not blank space
- [ ] **Deletion:** Often missing cascade handling -- verify that deleting a scene updates (not crashes) the breakdown, and deleting a breakdown element does not affect the script
- [ ] **Category filtering:** Often missing for the "all elements" view -- verify the master list can be filtered by category, by scene, and by source (AI vs user)
- [ ] **Sync status:** Often missing visual indicator -- verify the user can see whether the breakdown is up-to-date with the current script version or needs re-extraction

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hallucinated elements in master list | LOW | Add a "bulk review" mode where user can quickly approve/reject AI-extracted elements. Flag elements not referenced by any scene heading or action line. |
| Duplicate elements bloating master list | MEDIUM | Build a one-time deduplication tool: find elements with similar names (Levenshtein distance < 3 or same canonical form), present merge candidates to user, merge selected pairs. |
| Circular sync loop | LOW | Add the `sync_origin` guard. If already in production, add a circuit breaker: if the same project triggers extraction more than 3 times in 60 seconds, halt sync and log an alert. |
| User refinements destroyed by re-extraction | HIGH | If no backup exists, recovery is impossible — the user's edits are gone. Prevention is the only strategy. Add `user_edited_at` tracking and diff-merge before enabling re-extraction. If already shipped without it, add an "undo last extraction" feature that restores the previous breakdown snapshot. |
| Dangling scene references after regeneration | MEDIUM | Run a cleanup migration that nullifies orphaned scene FKs. Rebuild scene links by re-running extraction on the current script. User-added scene links that pointed to deleted scenes are lost. |
| Extraction context too large (token errors) | LOW | Switch to chunked extraction. Split screenplay by scene headings. Run extraction per-scene-chunk. Consolidate results. No data loss, just a code change. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Hallucinated elements (P1) | Extraction service design | Run extraction on 3 test screenplays, count hallucinated elements. Target: <5% hallucination rate. |
| Duplicate elements (P2) | Extraction service design + data model | Extract from a script with recurring characters/locations. Verify master list has no duplicates. |
| Circular sync loop (P3) | Architecture / sync rules | Write integration test: save script -> extraction fires -> verify no second extraction fires. |
| User refinements destroyed (P4) | Data model + extraction service | Edit 5 elements manually, re-extract, verify all 5 user edits survive. |
| Scene ID instability (P5) | Data model migration | Regenerate scenes via Scene Wizard, verify breakdown scene links survive. |
| Context overload (P6) | Extraction service design | Extract from a project with all phases completed. Verify extraction only references screenplay text, not story/idea phase data. |
| Category overwhelm (UX) | Frontend UI design | User test with 3 people. Ask "does this feel manageable?" |
| No progress indication (UX) | Frontend UI implementation | Measure extraction time. If >3 seconds, verify progress indicator appears. |
| Disconnected breakdown (UX) | Frontend UI + routing | Click every element-to-scene link. Verify navigation works. Click every scene-to-element link. Verify bidirectional. |

---

## Sources

- Direct analysis of `/backend/app/models/database.py` — `ScreenplayContent.version` field, `ListItem` cascade behavior, `PhaseData` unique constraints, lack of stable scene identity
- Direct analysis of `/backend/app/services/template_ai_service.py` — `_build_project_context` method (context accumulation pattern), `_generate_scripts` per-scene loop pattern, temperature settings (0.7-0.8 for generation), JSON mode usage
- Direct analysis of `/backend/app/templates/shared/write_phase.json` — screenplay editor structure, scene-to-screenplay relationship
- Direct analysis of `/backend/app/templates/short_movie.json` — phase structure, character card groups, scene field definitions
- `.planning/PROJECT.md` — v2.0 milestone requirements (5 categories, bidirectional sync on save/generate, user refinement), constraints (chunked processing, existing template integration)
- [Noam Kroll's Filmustage review](https://noamkroll.com/review-testing-filmustages-ai-powered-script-breakdown-app-on-a-feature-film/) — real-world AI breakdown accuracy: "generally didn't miss elements but would sometimes add unnecessary items or duplicates"; contextual misinterpretation examples; recommendation to review all tags before scheduling
- [First Draft Filmworks: Complete Guide to Script Breakdown](https://firstdraftfilmworks.com/blog/the-complete-guide-to-script-breakdown/) — standard 21 breakdown categories; props vs. set dressing distinction ("if a character picks up or uses something, it's a prop"); extras classification edge cases
- [StudioBinder: Script Breakdown Elements Guide](https://www.studiobinder.com/blog/the-complete-guide-to-mastering-script-breakdown-elements/) — industry-standard element categorization and color coding
- [Bidirectional Data Synchronization Patterns](https://dev3lop.com/bidirectional-data-synchronization-patterns-between-systems/) — common pitfalls: circular loops, syncing unnecessary fields, lacking monitoring
- [TanStack Query Optimistic Updates](https://tanstack.com/query/v4/docs/react/guides/optimistic-updates) — cancel-snapshot-rollback pattern for React Query cache management during mutations
- [TkDodo: Concurrent Optimistic Updates](https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query) — query cancellation to prevent stale data overwriting optimistic updates
- [SQLAlchemy Performance Anti-Patterns](https://dev.to/zchtodd/sqlalchemy-performance-anti-patterns-and-their-fixes-4bmm) — N+1 query prevention with `selectinload`, association table direct manipulation for many-to-many performance

---
*Pitfalls research for: AI Script Breakdown with Bidirectional Sync (v2.0 Milestone)*
*Researched: 2026-03-12*
