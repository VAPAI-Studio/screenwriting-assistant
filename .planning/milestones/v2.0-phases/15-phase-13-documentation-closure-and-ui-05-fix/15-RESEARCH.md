# Phase 15: Phase 13 Documentation Closure & UI-05 Fix — Research

**Researched:** 2026-03-18
**Domain:** Documentation closure, frontend route bug fix, GSD verification artifact creation
**Confidence:** HIGH

---

## Summary

Phase 15 is a pure gap-closure phase with no new feature development. The work divides into three distinct sub-problems: (1) a one-line frontend route fix in `ElementCard.tsx`, (2) two documentation checkbox and frontmatter updates, and (3) creating a formal Phase 13 VERIFICATION.md that was never written.

All Phase 13 code is already live and functional. The audit confirmed that UI-01 through UI-06 were built in Plans 13-01 and 13-02, and UI-07 (AddElementDialog) plus UI-08 (empty state) were built in Plan 13-03 — but Plan 13-03's `requirements_completed` frontmatter was left empty (`[]`) and the REQUIREMENTS.md checkboxes for UI-07 and UI-08 remain `[ ]`. The missing VERIFICATION.md is what makes all eight UI requirements formally "partial" rather than "satisfied" per the 3-source matrix.

**Primary recommendation:** Fix the route key in one line, update two documentation files, then write a VERIFICATION.md modeled exactly on the Phase 14 VERIFICATION.md format — it will have 8 observable truths, mostly automated-with-human-note entries, and reference specific file:line evidence for each truth.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Dedicated Breakdown page accessible from project workspace navigation | Code confirmed in App.tsx + PhaseNavigation.tsx; VERIFICATION.md will formally verify |
| UI-02 | Category tabs (Characters, Locations, Props, Wardrobe, Vehicles) with count badges | Code confirmed in CategoryTabs.tsx; VERIFICATION.md will formally verify |
| UI-03 | Master list per category with element name, description, scene count, source badge, user-modified indicator | Code confirmed in ElementCard.tsx + ElementList.tsx; VERIFICATION.md will formally verify |
| UI-04 | Inline editing of element names and descriptions | Code confirmed in ElementCard.tsx with optimistic mutation; VERIFICATION.md will formally verify |
| UI-05 | Scene chips on each element showing linked scenes; clickable to navigate to scene | Code exists but has routing bug; fix replaces `'scenes'` with `'scene_list'` as subsection key |
| UI-06 | "Extract Breakdown" button for first extraction; "Refresh" button with staleness banner when outdated | Code confirmed in StalenessBar.tsx + BreakdownPage.tsx; VERIFICATION.md will formally verify |
| UI-07 | Add element dialog for manually creating new elements | Code confirmed in AddElementDialog.tsx (Plan 13-03); REQUIREMENTS.md needs `[ ]` → `[x]`; 13-03-SUMMARY frontmatter needs update |
| UI-08 | Empty state with clear CTA when no breakdown exists yet | Code confirmed in BreakdownPage.tsx empty-state block (Plan 13-03); REQUIREMENTS.md needs `[ ]` → `[x]`; 13-03-SUMMARY frontmatter needs update |
</phase_requirements>

---

## Standard Stack

This phase touches only existing project files — no new libraries or dependencies.

### Core
| Component | Location | Purpose |
|-----------|----------|---------|
| ElementCard.tsx | `frontend/src/components/Breakdown/ElementCard.tsx` | Scene chip navigation — contains the UI-05 route bug |
| REQUIREMENTS.md | `.planning/REQUIREMENTS.md` | UI-07/UI-08 checkbox status |
| 13-03-SUMMARY.md | `.planning/phases/13-breakdown-page/13-03-SUMMARY.md` | requirements_completed frontmatter |
| 13-VERIFICATION.md | `.planning/phases/13-breakdown-page/13-VERIFICATION.md` | Does not yet exist; must be created |

### Supporting reference files (read, not modified)
| File | What it provides |
|------|-----------------|
| `backend/app/templates/short_movie.json` | Authoritative source for phase/subsection key names |
| `frontend/src/lib/constants.ts` | ROUTES.PROJECT_WORKSPACE signature |
| Phase 14 VERIFICATION.md | Gold-standard format to replicate for Phase 13 |
| Phase 12 VERIFICATION.md | Additional format reference |

---

## Architecture Patterns

### Pattern 1: ROUTES.PROJECT_WORKSPACE signature

The route helper in `constants.ts` line 236:
```typescript
PROJECT_WORKSPACE: (id: string, phase?: string, subsectionKey?: string, itemId?: string) => {
  let path = `/projects/${id}`;
  if (phase) path += `/${phase}`;
  if (subsectionKey) path += `/${subsectionKey}`;
  if (itemId) path += `/${itemId}`;
  return path;
}
```

The call at `ElementCard.tsx:253`:
```typescript
navigate(ROUTES.PROJECT_WORKSPACE(projectId, 'write', 'scenes', link.scene_item_id));
```

This generates the URL: `/projects/:id/write/scenes/:scene_item_id`

**The bug:** The third argument `'scenes'` is wrong for two reasons:
1. The phase containing scene lists is `'scenes'` (correct as 2nd arg), not `'write'`
2. The subsection key for the scene list within the scenes phase is `'scene_list'`, not `'scenes'`

The correct call should be:
```typescript
navigate(ROUTES.PROJECT_WORKSPACE(projectId, 'scenes', 'scene_list', link.scene_item_id));
```

This generates: `/projects/:id/scenes/scene_list/:scene_item_id` — which matches the actual template structure.

### Pattern 2: Template structure (from short_movie.json)

```
Phase id=scenes (name="Scenes")
  subsection key=scene_wizard     (name="Scene Wizard")
  subsection key=scene_list       (name="Scene List")   <-- CORRECT TARGET
  subsection key=scene_detail     (name="Individual Scenes")

Phase id=write (name="Write")
  subsection key=script_writer_wizard
  subsection key=screenplay_editor
  subsection key=screenplay_analyzer
```

The scene chips link to `scene_item_id` values which are ListItems in the `scenes` phase (confirmed by BKDN-02: `element_scene_links` junction table linking to scene ListItems). The correct navigation must use phase=`'scenes'` and subsectionKey=`'scene_list'`.

### Pattern 3: VERIFICATION.md format

Modeled on Phase 14 VERIFICATION.md (highest quality example in this project):

**Frontmatter:**
```yaml
---
phase: 13-breakdown-page
verified: <ISO datetime>
status: human_needed   # or passed
score: N/N must-haves verified
re_verification: false
human_verification:
  - test: "..."
    expected: "..."
    why_human: "..."
---
```

**Sections required:**
1. Header block (Phase Goal, Verified date, Status, Re-verification)
2. `## Goal Achievement` > `### Observable Truths` table (# | Truth | Status | Evidence)
3. `## Required Artifacts` table (Artifact | Expected | Status | Details)
4. `## Key Link Verification` table (From | To | Via | Status | Details)
5. `## Requirements Coverage` table (Requirement | Source Plan | Description | Status | Evidence)
6. `## Anti-Patterns Found` table
7. `## Human Verification Required` (numbered list with Test/Expected/Why human)
8. `## Gaps Summary`
9. Footer line with verifier attribution

### Pattern 4: REQUIREMENTS.md checkbox format

Current (to change):
```markdown
- [ ] **UI-07**: Add element dialog for manually creating new elements
- [ ] **UI-08**: Empty state with clear CTA when no breakdown exists yet
```

After fix:
```markdown
- [x] **UI-07**: Add element dialog for manually creating new elements
- [x] **UI-08**: Empty state with clear CTA when no breakdown exists yet
```

### Pattern 5: SUMMARY.md frontmatter format

Current 13-03-SUMMARY.md frontmatter (abridged):
```yaml
---
phase: 13-breakdown-page
plan: "03"
status: completed
---
```

The frontmatter is minimal — it has no `requirements_completed` list. The other SUMMARYs (13-01, 13-02) have full frontmatter with `requires`, `provides`, `affects`, `tech-stack`, `key-files`, `key-decisions`, `patterns-established`, and `requirements-completed`. Plan 13-03-SUMMARY.md was written in a stripped-down format. The update must add a `requirements-completed` list to 13-03-SUMMARY.md frontmatter.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| New test infrastructure | Custom test runners or E2E harness | Phase 15 has no new backend code; use existing pytest suite for verification evidence |
| New UI components | Any new React components | No new components needed — this phase only fixes one line and creates documents |

---

## Common Pitfalls

### Pitfall 1: Wrong phase ID in the scene chip fix

**What goes wrong:** Fixing only the subsection key (`'scenes'` → `'scene_list'`) but leaving the phase argument as `'write'`.
**Root cause:** The bug has two dimensions — wrong phase AND wrong subsection key.
**How to avoid:** Use `ROUTES.PROJECT_WORKSPACE(projectId, 'scenes', 'scene_list', link.scene_item_id)` — both the phase (`'scenes'`) and the subsection (`'scene_list'`) must change.
**Verification:** Navigate to a breakdown element with scene chips, click one, verify the URL becomes `/projects/:id/scenes/scene_list/:scene_item_id`.

### Pitfall 2: 13-03-SUMMARY.md frontmatter not parseable

**What goes wrong:** Adding `requirements-completed` to 13-03-SUMMARY.md but using wrong YAML indentation or mixing `-` with `:` syntax.
**Root cause:** YAML is whitespace-sensitive.
**How to avoid:** Match the exact format from 13-01-SUMMARY.md and 13-02-SUMMARY.md:
```yaml
requirements-completed:
  - UI-07
  - UI-08
```

### Pitfall 3: VERIFICATION.md observable truths miss UI-05 bug status

**What goes wrong:** Writing UI-05 as "VERIFIED" without noting the route fix that must happen in this phase.
**Root cause:** The audit found the route mismatch — VERIFICATION.md should document the pre-fix state and note the fix.
**How to avoid:** Mark UI-05 truth as "VERIFIED (after Phase 15 fix)" with evidence pointing to the corrected line. The VERIFICATION.md is written after the fix is applied, so it documents the corrected state.

### Pitfall 4: REQUIREMENTS.md traceability table not updated

**What goes wrong:** Checking `[x]` for UI-07 and UI-08 in the Frontend section but forgetting to update the Traceability table at the bottom of REQUIREMENTS.md.
**Root cause:** REQUIREMENTS.md has two separate locations for each requirement: the checkbox list and the traceability table.
**How to avoid:** Check both sections. The traceability table currently says:
```
| UI-07 | Phase 15 | Pending |
| UI-08 | Phase 15 | Pending |
```
These should be updated to `Phase 13` (where the code was actually built) with `Complete` status. However, the ROADMAP.md says these are assigned to Phase 15. Check what the audit expects — the audit says "change checkbox to [x]" and "update frontmatter". The traceability table update is secondary but should be consistent.

### Pitfall 5: VERIFICATION.md human-needed items not scoped correctly

**What goes wrong:** Marking all 8 UI truths as human-needed when several have clear automated evidence (file:line references, grep-verifiable patterns).
**Root cause:** Over-conservative classification.
**How to avoid:** For each truth, check if the evidence is greppable/readable (mark VERIFIED automated) vs. requires a running browser (mark VERIFIED + HUMAN NEEDED). Pattern from Phase 14: "JSX conditional render on category prop cannot be verified by running the app in CI" is the human-needed criterion.

---

## Code Examples

### Scene chip fix (the one-line change)

Current (buggy) at `frontend/src/components/Breakdown/ElementCard.tsx:253`:
```typescript
navigate(ROUTES.PROJECT_WORKSPACE(projectId, 'write', 'scenes', link.scene_item_id));
```

Fixed:
```typescript
navigate(ROUTES.PROJECT_WORKSPACE(projectId, 'scenes', 'scene_list', link.scene_item_id));
```

**Evidence for correct key:** `backend/app/templates/short_movie.json` lines 135, 168:
- Phase id: `"scenes"` (line 135)
- Subsection key: `"scene_list"` (line 168, the `OrderedList` view containing scene ListItems)

### REQUIREMENTS.md changes

Lines 79-80 (current):
```markdown
- [ ] **UI-07**: Add element dialog for manually creating new elements
- [ ] **UI-08**: Empty state with clear CTA when no breakdown exists yet
```

Lines 79-80 (after fix):
```markdown
- [x] **UI-07**: Add element dialog for manually creating new elements
- [x] **UI-08**: Empty state with clear CTA when no breakdown exists yet
```

Lines 141-142 (traceability, current):
```markdown
| UI-07 | Phase 15 | Pending |
| UI-08 | Phase 15 | Pending |
```

Lines 141-142 (traceability, after fix):
```markdown
| UI-07 | Phase 13 | Complete |
| UI-08 | Phase 13 | Complete |
```

### 13-03-SUMMARY.md frontmatter addition

Current frontmatter:
```yaml
---
phase: 13-breakdown-page
plan: "03"
status: completed
---
```

Updated frontmatter:
```yaml
---
phase: 13-breakdown-page
plan: "03"
status: completed
requirements-completed:
  - UI-07
  - UI-08
---
```

### VERIFICATION.md observable truths for Phase 13

Evidence gathered from source (for VERIFICATION.md authoring):

| # | Truth | Evidence location |
|---|-------|------------------|
| 1 | UI-01: Breakdown page accessible from workspace navigation | App.tsx: `/projects/:projectId/breakdown` route; PhaseNavigation.tsx: `onBreakdownClick` prop; 13-01-SUMMARY |
| 2 | UI-02: Category tabs with count badges | CategoryTabs.tsx: Radix Tabs with 5 categories + badge from `summary.counts_by_category`; 13-01/02-SUMMARY |
| 3 | UI-03: Master list with name, description, source badge, user-modified indicator | ElementCard.tsx: source badge conditional (line ~192), Pencil user_modified icon (line ~184), ElementList.tsx; 13-02-SUMMARY |
| 4 | UI-04: Inline editing with optimistic updates | ElementCard.tsx: `updateMutation` + `onMutate` cancel/snapshot + `onError` rollback; 13-02-SUMMARY |
| 5 | UI-05: Scene chips navigate to correct scene (after Phase 15 fix) | ElementCard.tsx:253 (post-fix): `ROUTES.PROJECT_WORKSPACE(projectId, 'scenes', 'scene_list', link.scene_item_id)` |
| 6 | UI-06: Extract button + staleness banner | BreakdownPage.tsx: `extractMutation`; StalenessBar.tsx: renders when `is_stale && total_elements > 0`; 13-02-SUMMARY |
| 7 | UI-07: AddElementDialog creates elements manually | AddElementDialog.tsx: Radix Dialog with category select + name input; `api.createBreakdownElement`; 13-03-SUMMARY |
| 8 | UI-08: Empty state renders when no breakdown exists | BreakdownPage.tsx: empty state block with `total_elements === 0`; ListChecks icon + Extract CTA; 13-03-SUMMARY |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No Phase 13 VERIFICATION.md | Create VERIFICATION.md during Phase 15 | Phase 15 (this phase) | Completes 3-source matrix for all UI requirements |
| UI-07/UI-08 unchecked in REQUIREMENTS.md | Check [x] during Phase 15 | Phase 15 (this phase) | Requirements formally satisfied |
| `'scenes'` subsection key in ElementCard | `'scene_list'` subsection key | Phase 15 (this phase) | Scene chip navigation resolves to valid content |

**What was already done (Phase 13):**
- All 5 Breakdown components created: `BreakdownPage.tsx`, `StalenessBar.tsx`, `CategoryTabs.tsx`, `ElementList.tsx`, `ElementCard.tsx`
- `AddElementDialog.tsx` created with full Radix Dialog implementation
- Empty state block added to BreakdownPage.tsx
- Delete with two-click confirm added to ElementCard.tsx

---

## Open Questions

1. **Should REQUIREMENTS.md traceability table show Phase 13 or Phase 15 for UI-07/UI-08?**
   - What we know: The code was built in Phase 13 (Plan 13-03). The ROADMAP.md traceability currently says Phase 15. The audit says to check the checkboxes.
   - What's unclear: Whether to correct the traceability table to say Phase 13 (truthful) or leave it as Phase 15 (where docs gap was formally closed).
   - Recommendation: Update to `Phase 13 | Complete` since the code was built there. Phase 15 is the documentation closure phase, not the implementation phase.

2. **Does 13-03-SUMMARY.md need the full dependency-graph frontmatter (requires/provides/affects)?**
   - What we know: 13-01 and 13-02 SUMMARY files have full frontmatter; 13-03-SUMMARY only has 4 lines.
   - What's unclear: Whether the planner/verifier requires full frontmatter or just `requirements-completed`.
   - Recommendation: Add only `requirements-completed` to the existing minimal frontmatter — the audit only flags the missing `requirements-completed` entries. Don't restructure the whole file.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + TypeScript compiler (frontend) |
| Config file | `backend/app/tests/test_breakdown_api.py` (existing) |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -x -q && cd ../frontend && npm run build && npm run lint` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-05 | Scene chip navigates to `scenes/scene_list/:id` | manual | `cd frontend && npm run build` (TypeScript compile) | ✅ ElementCard.tsx |
| UI-07 | Add element dialog renders + submits | manual | `cd frontend && npm run build` | ✅ AddElementDialog.tsx |
| UI-08 | Empty state renders when total_elements=0 | manual | `cd frontend && npm run build` | ✅ BreakdownPage.tsx |

**Note:** Phase 15 has no backend code changes. All tests are documentation/frontend-lint verification. The route fix in ElementCard.tsx is a one-line string change — TypeScript will not catch it as a type error (all arguments are strings). The fix is verified by reading the corrected line and by manual browser test (click scene chip → verify URL).

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/frontend && npm run build`
- **Per wave merge:** Full suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new test files needed.

---

## Sources

### Primary (HIGH confidence)
- Direct file read: `frontend/src/components/Breakdown/ElementCard.tsx` — confirmed route bug at line 253
- Direct file read: `backend/app/templates/short_movie.json` — confirmed `scenes` phase with `scene_list` subsection key at lines 135, 168
- Direct file read: `frontend/src/lib/constants.ts` — confirmed `ROUTES.PROJECT_WORKSPACE` signature
- Direct file read: `.planning/REQUIREMENTS.md` — confirmed UI-07/UI-08 checkbox status
- Direct file read: `.planning/phases/13-breakdown-page/13-03-SUMMARY.md` — confirmed empty `requirements_completed` frontmatter
- Direct file read: `.planning/phases/14-reverse-sync/14-VERIFICATION.md` — VERIFICATION.md format reference
- Direct file read: `.planning/phases/12-staleness-hooks/12-VERIFICATION.md` — additional format reference
- Direct file read: `.planning/v2.0-MILESTONE-AUDIT.md` — audit findings confirming all gaps

### Secondary (MEDIUM confidence)
- None

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Route bug location and fix: HIGH — confirmed by direct read of ElementCard.tsx:253 and short_movie.json template structure
- REQUIREMENTS.md changes: HIGH — confirmed by direct read of current checkbox states and traceability table
- SUMMARY frontmatter changes: HIGH — confirmed by direct read of 13-03-SUMMARY.md (missing requirements_completed) and audit findings
- VERIFICATION.md format: HIGH — modeled directly on Phase 14 VERIFICATION.md (gold standard in this project)
- All Phase 13 components exist: HIGH — confirmed by audit and direct read of SUMMARY files

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable documentation phase; no external dependencies)
