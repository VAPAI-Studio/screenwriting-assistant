# Feature Landscape: Script Breakdown System

**Domain:** AI-powered script breakdown for film/TV pre-production
**Researched:** 2026-03-13
**Confidence:** HIGH (industry categories well-documented, competitor features verified via multiple sources)

---

## Context: What Already Exists

The codebase has a template-based screenwriting assistant with AI generation. The breakdown system builds on top of existing data structures.

**Already implemented (do not rebuild):**
- `PhaseData` model with `content` JSON storing structured scene/story data per phase
- `ListItem` model with `item_type: "scene"` storing individual scenes with `content` JSON (fields: `summary`, `arena`, `inciting_incident`, `goal`, `subtext`, `turning_point`, `crisis`, `climax`, `fallout`, `push_forward`)
- `ScreenplayContent` model with `content` (text) and `formatted_content` (JSON) per scene
- `template_ai_service.py` with phase-based AI generation pipeline (idea -> story -> scenes -> write)
- AI provider abstraction (`ai_provider.py`) supporting OpenAI and Anthropic
- Agent system with RAG-based knowledge retrieval and multi-agent parallel review
- Scene list and individual scene detail views in the frontend workspace

**Key data available for breakdown extraction:**
- Story phase data: logline, theme, protagonist, characters list (with descriptions, arcs, motivations)
- Scene list: summaries, arenas (locations), beats mapped to scenes
- Individual scene detail: full narrative breakdown per scene
- Screenplay content: generated screenplay text per scene/episode

**The gap this milestone fills:**
No production-oriented view exists. Users create screenplays but have no way to see "which props appear across scenes", "where does Character X appear", or "what wardrobe changes are needed." The breakdown bridges creative writing to production planning.

---

## Industry Standard: Breakdown Categories

The film industry uses a well-established set of production element categories. These are codified in Movie Magic Scheduling (the industry standard) and followed by StudioBinder, Celtx, Filmustage, and Gorilla.

### Movie Magic Scheduling Default Categories (23 total)
Additional Labor, Animal Wrangler, Animals, Art Department, Background Actors, Camera, Cast Members, Greenery, Makeup/Hair, Mechanical Effects, Miscellaneous, Music, Notes, Props, Security, Set Dressing, Sound, Special Effects, Special Equipment, Stunts, Vehicles, Visual Effects, Wardrobe

### Industry Standard Color Codes
| Color | Category | Description |
|-------|----------|-------------|
| Red | Cast | Speaking actors and principal cast |
| Orange | Stunts | Stunt sequences and stunt doubles |
| Yellow | Extras (Silent) | Non-speaking performers with action |
| Green | Extras (Atmosphere) | Background crowd and environmental people |
| Blue | Special Effects | Practical SFX on set |
| Purple/Violet | Props | Objects handled by actors or referenced in script |
| Pink | Vehicles / Animals | Picture vehicles and animals in scene |
| Brown | Sound Effects | Practical sound needs on set |
| Circle mark | Wardrobe | Costume and clothing requirements |
| Asterisk mark | Makeup/Hair | Makeup and hair styling needs |

Note: Color schemes are conventional, not rigidly standardized. Different productions may adapt them. The important thing is consistency within a project.

---

## Table Stakes

Features users expect from any breakdown system. Missing any of these makes the feature feel incomplete. Informed by what StudioBinder, Celtx, Filmustage, and Gorilla all provide.

| Feature | Why Expected | Complexity | Dependencies on Existing |
|---------|--------------|------------|--------------------------|
| **AI extraction of elements from script** | The core value proposition. Manual tagging is the old way; AI extraction is why users would use this over a spreadsheet. Filmustage proved AI extraction is viable and expected. | High | Reads from `ScreenplayContent.content` + `ListItem.content` (scene data) + `PhaseData.content` (characters, story). Requires AI provider calls. |
| **Core category support (Cast, Props, Wardrobe, Vehicles, Locations)** | These 5 are the PROJECT.md scope and the minimum set every production needs. Every competitor supports at least these. | Medium | New DB tables for breakdown elements with `category` enum. |
| **Master list per category** | StudioBinder's Elements Manager, Celtx's Catalog -- users expect a single searchable inventory of all elements grouped by category. This is how departments work. | Medium | New API endpoint + new frontend page. No dependency on existing components. |
| **Scene-to-element linking** | Every competitor tracks which scenes each element appears in. "Character X appears in scenes 1, 3, 7" is fundamental for scheduling and budgeting. | Medium | Foreign key from breakdown element to `ListItem` (scene). Junction table: `breakdown_element_scenes`. |
| **User refinement (add, edit, remove elements)** | AI extraction will miss things and hallucinate others. Users must be able to correct the AI. StudioBinder, Celtx, and Filmustage all support manual editing of AI/auto-generated results. | Medium | CRUD endpoints for breakdown elements. Frontend inline editing. |
| **Breakdown re-extraction on script change** | Filmustage updates breakdown automatically when a new script version is uploaded. If the script changes and the breakdown is stale, the feature is useless. PROJECT.md specifies "on save/generate." | High | Hook into `template_ai_service.py` post-generation and `ScreenplayContent` save events. Must diff against previous extraction to avoid losing user edits. |
| **Dedicated breakdown page/view** | A breakdown buried in the existing workspace tabs is hard to find. All competitors have a distinct breakdown area. PROJECT.md specifies "Dedicated breakdown page." | Medium | New route/tab in the frontend. Can reuse workspace layout patterns. |
| **Element count per scene** | Users need to see at a glance how "heavy" a scene is (many props + many cast = expensive scene). This is implicit in every per-scene breakdown sheet. | Low | Computed from junction table. No extra storage needed. |

---

## Differentiators

Features that set this system apart from competitors. Not expected, but high value. Ordered by impact.

| Feature | Value Proposition | Complexity | Dependencies on Existing |
|---------|-------------------|------------|--------------------------|
| **Context-aware extraction using project phase data** | Filmustage/StudioBinder extract from script text only. This system has access to structured story data (character arcs, scene goals, beat mappings) which enables deeper extraction. E.g., knowing a character's "wardrobe" from the story phase data, not just what's mentioned in dialogue. | Medium | Reads from `PhaseData` (story/characters) in addition to screenplay text. Enriches extraction prompt with structured context. |
| **Extraction from project data even before screenplay exists** | Most tools require a formatted screenplay. This system can generate a preliminary breakdown from scene descriptions and character lists alone, giving production estimates earlier in the creative process. | Medium | Fallback extraction from `ListItem` (scenes) + `PhaseData` (characters) when no `ScreenplayContent` exists yet. |
| **Bidirectional sync: breakdown edits back to script context** | PROJECT.md specifies this. No competitor does true bidirectional sync. Filmustage and StudioBinder update breakdown from script, but not the reverse. If a user adds a prop in the breakdown, it could flag the screenplay as needing that prop added. | High | Requires a "suggested changes" or "annotation" layer on screenplay content. Complex conflict resolution. |
| **Intelligent merge on re-extraction** | When script changes trigger re-extraction, the system should merge AI results with user edits rather than overwriting them. Filmustage preserves "custom scene and tag settings from the previous version." | High | Requires diff/merge logic: match elements by name+category, preserve user-added elements, flag removed elements for user confirmation, add new AI-detected elements as suggestions. |
| **Element detail pages with notes and metadata** | StudioBinder gives each element its own profile page with notes, images, docs. Adding a notes/description field per element enables production teams to annotate requirements. | Low | Simple `notes` text field on breakdown element model. Low complexity, high perceived value. |
| **Visual indicators in screenplay view** | StudioBinder highlights tagged elements in the script with color-coded markup. Showing breakdown elements inline in the screenplay editor connects the two views. | High | Requires modifying the `ScreenplayEditorView` component to overlay color-coded highlights. Complex frontend work. |
| **Breakdown completeness scoring** | Show users how thoroughly their breakdown covers the script. "85% of scenes have been reviewed" or "3 scenes have no location assigned." Helps users trust the AI extraction and know where to focus manual review. | Low | Computed metric: scenes with elements / total scenes, elements with scene links / total elements. |

---

## Anti-Features

Features to deliberately NOT build in this milestone. These are explicitly out of scope per PROJECT.md or would add complexity disproportionate to value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Scheduling / calendar integration** | PROJECT.md explicitly defers this. Scheduling is a massive feature domain (stripboards, day-out-of-day reports, shoot order optimization). Building it alongside breakdown doubles scope. | Build breakdown as a standalone data layer. Ensure the data model supports future scheduling by including scene-element links and element metadata, but do not build scheduling UI or logic. |
| **Budget line items and cost tracking** | PROJECT.md explicitly defers this. Budget requires rate cards, union rules, overtime calculations -- an entirely separate domain. | Element metadata (notes field) can informally capture cost hints. Do not build formal budget structures. |
| **Department assignments** | PROJECT.md explicitly defers this. Assigning elements to crew departments requires a crew/department management system that does not exist. | Category grouping (Props, Wardrobe, etc.) implicitly maps to departments. Users mentally map categories to their departments. |
| **Day/Night and INT/EXT scene classification** | PROJECT.md explicitly defers this. While standard in breakdown sheets, this requires scene header parsing that the current template system does not produce. | Scene "arena" field provides location context. Formal INT/EXT/DAY/NIGHT parsing can be added when screenplay formatting matures. |
| **Full 23-category Movie Magic parity** | Categories like "Animal Wrangler", "Security", "Greenery", "Additional Labor" are production-operations categories, not creative breakdown categories. Supporting 23 categories in V1 creates UI clutter and dilutes focus. | Start with 5 core categories (Cast, Props, Wardrobe, Vehicles, Locations) per PROJECT.md. Add SFX, Makeup/Hair, Set Dressing in a fast follow if users request them. Design the category system as extensible (enum or configurable list, not hardcoded). |
| **Real-time sync (as user types)** | PROJECT.md specifies sync on save/generate, not real-time. Real-time sync requires debouncing, conflict resolution, and WebSocket infrastructure that adds substantial complexity. | Trigger re-extraction on explicit save or generation completion events. |
| **Export to industry formats (PDF breakdown sheets, Movie Magic import)** | PROJECT.md explicitly defers this. PDF generation and .mms file format support are significant features. | Data model should store enough detail that export is feasible later. Do not build export UI or format converters. |
| **Color-coded text highlighting in script** | While industry standard in tools like StudioBinder, this requires a rich text annotation layer on the screenplay editor that is a major frontend undertaking. | Show elements as a separate list view linked to scenes. Defer inline highlighting to a later phase. |
| **Per-element image/document attachments** | StudioBinder's element profiles support images and docs. This requires file upload infrastructure per element. | Support a text `notes` field per element. Defer media attachments. |

---

## Feature Dependencies

```
AI Extraction Service (new)
  -> requires: ScreenplayContent model (exists)
  -> requires: ListItem model with scene data (exists)
  -> requires: PhaseData model with character/story data (exists)
  -> requires: ai_provider.py (exists)
  -> produces: BreakdownElement records with category + scene links

Breakdown Data Model (new)
  -> requires: Project model (exists)
  -> requires: ListItem model for scene references (exists)
  -> produces: BreakdownElement table, BreakdownElementScene junction table

Breakdown API Endpoints (new)
  -> requires: Breakdown Data Model (new, from above)
  -> requires: AI Extraction Service (new, from above)
  -> produces: CRUD endpoints for elements, trigger endpoint for extraction

Breakdown Frontend Page (new)
  -> requires: Breakdown API Endpoints (new, from above)
  -> requires: ProjectWorkspace layout patterns (exists)
  -> produces: Dedicated breakdown view with master lists and scene links

Re-extraction on Script Change (new)
  -> requires: AI Extraction Service (new)
  -> requires: Breakdown Data Model populated (new)
  -> requires: Hook into template_ai_service.py post-generation (exists)
  -> produces: Updated breakdown with merge logic preserving user edits

Bidirectional Sync (new)
  -> requires: Breakdown Data Model with user edit tracking (new)
  -> requires: ScreenplayContent model (exists)
  -> produces: Annotations/suggestions on screenplay when breakdown changes

User Refinement UI (new)
  -> requires: Breakdown API CRUD endpoints (new)
  -> requires: Breakdown Frontend Page (new)
  -> produces: Inline editing, add/remove elements, edit scene links
```

**Critical path:**
1. Breakdown Data Model (DB tables + migrations)
2. AI Extraction Service (core extraction logic)
3. Breakdown API Endpoints (CRUD + extraction trigger)
4. Breakdown Frontend Page (master lists + scene links)
5. User Refinement UI (edit/add/remove)
6. Re-extraction on script change (merge logic)
7. Bidirectional sync (most complex, build last)

Steps 1-3 are sequential. Step 4 can begin once step 3 is partially complete. Step 5 builds on step 4. Steps 6-7 are additive layers on top of the working system.

---

## MVP Recommendation

### Prioritize (ship together -- they form the minimum coherent feature):

1. **Breakdown Data Model** -- `BreakdownElement` table (id, project_id, category, name, description/notes, ai_generated bool, created_at, updated_at) + `BreakdownElementScene` junction table (element_id, scene_list_item_id). Without this, nothing else can work.

2. **AI Extraction Service** -- Service that takes a project's screenplay content + scene data + character data and returns structured JSON of elements per category with scene references. This is the core value. Use the existing `ai_provider.py` for the AI call. Design the extraction prompt to output structured JSON that maps directly to the DB model.

3. **Breakdown API Endpoints** -- `POST /api/projects/{id}/breakdown/extract` (trigger extraction), `GET /api/projects/{id}/breakdown` (get all elements grouped by category with scene links), `PATCH /api/breakdown/elements/{id}` (edit element), `POST /api/projects/{id}/breakdown/elements` (add element), `DELETE /api/breakdown/elements/{id}` (remove element).

4. **Breakdown Frontend Page** -- New tab/route in the project workspace. Master list view with category tabs (Cast, Props, Wardrobe, Vehicles, Locations). Each element shows name, scene count, and expandable scene list. "Extract Breakdown" button. Inline edit/add/remove controls.

5. **User Refinement** -- Inline editing of element names and notes. Add new elements manually. Remove elements (soft delete to preserve for re-extraction merge). Edit scene links (add/remove element from specific scenes).

### Defer:

- **Bidirectional sync (breakdown -> script)** -- Most complex feature. The forward direction (script -> breakdown) is far more valuable for V1. Defer reverse sync until the forward direction is proven and users request it. This aligns with PROJECT.md listing it as a target but the complexity is disproportionate to initial value.

- **Re-extraction merge logic** -- Important but can ship as a follow-up. V1 can simply re-extract and let users manually reconcile. Smart merge (preserving user edits, flagging changes) is a phase 2 enhancement.

- **Visual indicators in screenplay editor** -- High frontend complexity. Decouple from initial breakdown launch.

- **Breakdown completeness scoring** -- Nice-to-have. Easy to add once the core data model exists.

- **Additional categories beyond the core 5** -- Design the category system as extensible but launch with Cast, Props, Wardrobe, Vehicles, Locations per PROJECT.md scope.

---

## Competitor Landscape Summary

| Tool | Extraction | Categories | Scene Links | Sync on Script Change | AI-Powered | Pricing |
|------|-----------|------------|-------------|----------------------|------------|---------|
| **StudioBinder** | Manual tagging (click-and-drag) | Full industry set, customizable | Yes, per breakdown sheet | Yes, manual re-sync | No | Free tier + paid |
| **Filmustage** | AI automatic (supports GPT, Gemini, own models) | Full industry set | Yes | Yes, automatic with diff | Yes (core feature) | Paid |
| **Celtx** | Semi-automatic (auto-tags characters, rest is manual) | Standard set | Yes, via catalog | Limited | Partial | Free tier + paid |
| **Movie Magic Scheduling** | Manual (import + tag) | 23 default categories, customizable | Yes, per breakdown sheet | Script import sync | No | Paid (expensive) |
| **Gorilla** | Manual (import + tag) | Standard set | Yes | Final Draft sync | No | Paid |

**This system's competitive advantage:** Context-aware extraction using structured project data (not just script text), extraction possible before screenplay is complete, and integrated into the same tool where the screenplay is written (no import/export friction).

---

## Sources

- [StudioBinder Script Breakdown Software](https://www.studiobinder.com/script-breakdown-software/) -- feature overview, Elements Manager, color-coded tagging
- [StudioBinder Script Breakdown Colors](https://www.studiobinder.com/blog/script-breakdown-colors/) -- industry standard color codes
- [StudioBinder Script Breakdown Elements Guide](https://www.studiobinder.com/blog/the-complete-guide-to-mastering-script-breakdown-elements/) -- element types and workflow
- [Celtx Script Breakdown](https://www.celtx.com/product/pre-production/breakdown/) -- auto character tagging, catalog integration
- [Filmustage AI Script Breakdown](https://filmustage.com/script-breakdown/) -- AI extraction, multi-model support, auto-sync
- [Filmustage Symbols and Color Codes Guide](https://filmustage.com/blog/script-breakdown-symbols-and-color-codes-a-complete-guide/) -- complete category/color reference
- [Movie Magic Scheduling Categories](https://mms-docs.ep.com/Breakdown/Categories.html) -- 23 default categories (HIGH confidence, official docs)
- [Movie Magic Scheduling Manual](https://mms-docs.ep.com/Breakdown/Breakdown.html) -- breakdown sheet structure
- [Gorilla Scheduling Features](https://junglesoftware.com/gorilla-scheduling-features/) -- breakdown sheets, import, reports
- [First Draft Filmworks Guide to Script Breakdown](https://firstdraftfilmworks.com/blog/the-complete-guide-to-script-breakdown/) -- workflow overview
- [Studiovity AI Breakdown](https://blog.studiovity.com/help/ai-powered-breakdown/) -- AI tagging UX patterns
- [Celtx vs StudioBinder Comparison](https://blog.celtx.com/celtx-vs-studiobinder-comparison/) -- feature comparison
- Codebase analysis: `backend/app/models/database.py` (existing data model)
- Codebase analysis: `backend/app/templates/short_movie.json` (scene structure, template phases)
- Codebase analysis: `backend/app/templates/shared/write_phase.json` (screenplay editor structure)
- Project spec: `.planning/PROJECT.md` (scope, requirements, out-of-scope items)
