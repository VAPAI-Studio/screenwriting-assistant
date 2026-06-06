---
phase: 49-side-by-side-quality-compare
plan: 02
subsystem: frontend
tags: [screenplay, scene-compare, regenerate, eval-01, radix-dialog]
requires:
  - "49-01: POST /api/wizards/regenerate-scene (preview) + POST /api/wizards/keep-scene-version (persist + stale)"
  - "ScreenplayEditorView screenplays[] {episode_index,title,content,error?} shape"
  - "QUERY_KEYS.SUBSECTION_DATA (constants.ts) — the key the screenplay view reads"
  - "Radix Dialog (CreateProjectModal skeleton) + Button cva variants + lucide-react"
provides:
  - "api.regenerateScene (120s CHAT_TIMEOUT) + api.keepSceneVersion (fast) client methods"
  - "RegenerateSceneRequest/Response + KeepSceneVersionRequest TS types"
  - "SceneCompareModal — two-pane current-vs-regenerated compare with keep-current/keep-new"
  - "Per-scene 'Regenerate & Compare' rail in ScreenplayEditorView carrying each scene's episode_index"
affects:
  - "Completes EVAL-01 user-facing flow (pending human UAT — Task 4)"
tech-stack:
  added: []
  patterns:
    - "regenerate-on-open: mutation kicked off in a useEffect gated on `open`"
    - "generated text retained in component state so keep-retry after persist failure does not re-regenerate"
    - "compose two analogs: CreateProjectModal Radix Dialog shell + ScreenplayEditorView paper renderer"
key-files:
  created:
    - frontend/src/components/Patterns/SceneCompareModal.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/api.tsx
    - frontend/src/components/Patterns/ScreenplayEditorView.tsx
decisions:
  - "Per-scene trigger surfaced as a thin per-scene RAIL (one row per screenplays[i]) above the paper stack, not an over-page floating button — the view renders a MERGED paginated document so scene boundaries are not per-page; the rail is the faithful per-scene anchor (UI-SPEC per-scene-trigger intent) and sits outside the clickable paper, so stopPropagation past startEditing is trivially satisfied (also applied explicitly on the button)"
  - "No new ESLint config created — the lint gate cannot run (pre-existing missing-config); tsc (npm run build) is the binding type-safety gate for this plan"
metrics:
  duration_minutes: 3
  completed: 2026-06-06
  tasks: 3
  files_changed: 4
---

# Phase 49 Plan 02: Side-by-Side Quality Compare (Frontend) Summary

The user-facing EVAL-01 slice: a per-scene "Regenerate & Compare" rail in the screenplay view opens a two-pane `SceneCompareModal` (current left vs freshly regenerated right) and lets the user keep either version — keep-new persisting through the 49-01 backend with the 120s `CHAT_TIMEOUT` regenerate path and a `SUBSECTION_DATA` invalidation so the view re-renders the kept scene. **AUTO tasks 1-3 complete and build clean; Task 4 (manual UAT) is PENDING USER — not run, not fabricated.**

## What Was Built

**Task 1 — types + API client (commit d4b035c):**
Added `RegenerateSceneRequest`, `RegenerateSceneResponse` (`{title, content, episode_index, error?}`), and `KeepSceneVersionRequest` to `types/index.ts`, mirroring the inline `Screenplay` shape. Added two methods to the `api` object: `regenerateScene` copies the `generateShotlist` AbortController + `setTimeout(controller.abort, CHAT_TIMEOUT)` (120s) pattern verbatim — POST `/wizards/regenerate-scene`, `AbortError → 'Request timeout'`; `keepSceneVersion` uses the fast `fetchWithTimeout` (runWizard) path — POST `/wizards/keep-scene-version`.

**Task 2 — SceneCompareModal (commit 66cb7e3):**
New `SceneCompareModal.tsx` composing the CreateProjectModal Radix Dialog skeleton (`w-[92vw] max-w-[1100px] h-[88vh]` flex column, overlay `bg-black/60 backdrop-blur-sm`, `animate-scale-in`) with the ScreenplayEditorView paper renderer. Header: `Dialog.Title` "Compare scene {n}: {title}", amber scene pill, disabled-while-persisting `X` close, `sr-only` `Dialog.Description`. Body: two columns (`grid-cols-1 md:grid-cols-2 gap-8`), LEFT `<section aria-label="Current stored version">` neutral CURRENT badge, RIGHT `<section aria-label="Regenerated version">` amber NEW badge — both render the identical `font-screenplay text-[13px]` `<pre>` at `lineHeight:'20px'` in the `hsl(240,5%,8.5%)` paper panel with the declared `40px 48px` pane padding, each scrolling independently. States per UI-SPEC: generating (amber `Loader2`, "Regenerating scene…", `aria-live="polite"`), loaded (both panes + buttons enabled), error (destructive "Regeneration failed. Your current version is untouched." + truncated server message + amber "Try again" / ghost "Cancel", keep-new disabled), keep-new persisting (panes `opacity-60`, "Saving…", all disabled including close), keep-new error (restored, retained generated text, "Couldn't save…"). Regenerate kicked off on open via a `useEffect` gated on `open`; the generated `{title,content}` is held in state so a keep retry after a persist failure does not re-regenerate. keep-new wires `api.keepSceneVersion` → `invalidateQueries(QUERY_KEYS.SUBSECTION_DATA)` → 600ms amber `Check` → close. keep-current is a pure no-op `onOpenChange(false)`. `onEscapeKeyDown`/`onInteractOutside` blocked only while persisting.

**Task 3 — per-scene trigger in ScreenplayEditorView (commit 0f657a8):**
Added a per-scene rail in view mode (one row per `screenplays[i]`: index + title + "Regenerate & Compare" button) above the paper stack. Button matches the Edit-toolbar ghost style with an amber `Sparkles` icon, label hidden under `sm` (`aria-label="Regenerate & compare this scene"`), and `e.stopPropagation()` so it never triggers the page-level `startEditing`. Local `compareIndex` `useState<number | null>` drives a single `SceneCompareModal` mount with the selected scene's `episodeIndex` / `currentTitle` / `currentContent` and `subsectionKey={subsection.key}`. Existing view/edit/save/pagination logic untouched (additive only).

## API Contract Verification (vs 49-01 shipped)

Verified against `backend/app/api/endpoints/wizards.py` (lines 367-486) and `backend/app/models/schemas.py` (565-587) — **no mismatch**:
- `POST /api/wizards/regenerate-scene` — `RegenerateSceneRequest {project_id: UUID, phase: str="write", episode_index: int}` → `RegenerateSceneResponse {title, content, episode_index, error?}`. The frontend sends `{project_id, phase, episode_index}` and handles the soft `error` payload (does not throw) in addition to thrown/timeout errors — matches the backend's preview-with-possible-error shape.
- `POST /api/wizards/keep-scene-version` — `KeepSceneVersionRequest {project_id, phase, episode_index, title, content}` → `{status, episode_index}`. The frontend sends exactly that body; `subsectionKey` is NOT in the request body (it is used only for the React Query invalidation key, per the critical constraint) — confirmed, the backend keys by `phase` + hardcoded `screenplay_editor`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed a no-op ternary in keep-new `onError`**
- **Found during:** Task 2
- **Issue:** The initial keep-new `onError` had `setKeepError(err?.message ? <same string> : <same string>)` — both branches produced the identical message, a dead ternary.
- **Fix:** Simplified to a single unconditional `setKeepError("Couldn't save the new version. Your stored scene is unchanged — try again.")`.
- **Files modified:** `frontend/src/components/Patterns/SceneCompareModal.tsx`
- **Commit:** 66cb7e3

### Soft-error handling (Rule 2 — missing critical functionality, additive)

`regenerateScene` resolves with `200 {error: ...}` on a generation failure (the backend `_generate_one_scene` failure branch is returned as a preview, not an HTTP error). The modal's `regenerateMutation.onSuccess` therefore checks `result.error` and routes to the error state (not just `onError`), so a soft failure still shows "Regeneration failed. Your current version is untouched." rather than rendering an empty/`[Generation failed: …]` right pane. This is correctness coverage for the documented backend contract, not a plan deviation in intent.

## Verification

- `cd frontend && npm run build` (`tsc && vite build`) — **PASS**, zero TypeScript errors, "✓ built in ~1.6s", 1912 modules (SceneCompareModal wired into the bundle). Also confirmed standalone `npx tsc --noEmit` → exit 0.
- `cd frontend && npm run lint` (`eslint . --max-warnings 0`) — **CANNOT RUN (pre-existing tooling gap, NOT caused by 49-02).** ESLint fails with "ESLint couldn't find a configuration file." No ESLint config has ever existed in the repo (no `.eslintrc*`, no `eslint.config.js`, no `package.json eslintConfig`; git history confirms). The failure is independent of source content. Logged in `deferred-items.md`. The binding type-safety gate for this plan is `npm run build`, which passes clean.

## Pending — Task 4 Manual UAT (NOT DONE — awaiting user)

Task 4 is a **`checkpoint:human-verify` (gate=blocking)** step: it requires the running stack and a human judging screenplay quality. It was **NOT executed and NOT fabricated.** The user must run the following UAT checklist against the running app and confirm each acceptance criterion:

1. Start the stack: `docker compose up --build` (or backend `uvicorn app.main:app --reload --port 8000` + frontend `npm run dev`).
2. Open a project that already has generated screenplays (Script Writer Wizard output) and go to the screenplay view. If a breakdown and shotlist already exist for it, note them (for the staleness check).
3. For a NON-first scene, click "Regenerate & Compare". Confirm: the modal opens, the LEFT pane shows the current stored scene immediately, the RIGHT pane shows the generating state ("Regenerating scene…", spinner) and then the regenerated scene (may take up to ~60s). Both panes render in the same Courier screenplay style.
4. Click "Keep current" → modal closes, the screenplay view is unchanged.
5. Re-open the same scene, wait for the new version, click "Keep new version" → button shows "Saving…", modal closes, and the screenplay view re-renders showing the NEW text for that scene (and only that scene).
6. Confirm persistence: reload the page — the kept scene text persists.
7. Confirm staleness: the project's breakdown and shotlist are now flagged stale (out-of-date indicator) — and ONLY after keep-new, not after keep-current.
8. Error path (optional): if regeneration fails (e.g. temporarily break OPENAI_API_KEY), the right pane shows "Regeneration failed. Your current version is untouched." with Try again / Cancel, and the stored scene is unchanged.

**Acceptance criterion (Task 4):** Old vs new shown side-by-side for the chosen scene; keep-current is a no-op; keep-new persists only that scene and survives reload; breakdown+shotlist go stale only on keep-new. Resume signal: type "approved" or describe issues.

## Known Stubs

None. The modal wires live data end-to-end: left pane from the stored `screenplays[i]`, right pane from `api.regenerateScene`, persist via `api.keepSceneVersion`. No placeholder/mock data paths.

## Threat Flags

None. No new network surface beyond the two 49-01 endpoints (both via `getHeaders()` Bearer auth). Screenplay text is rendered via React `<pre>` text nodes (no `dangerouslySetInnerHTML`) — no XSS surface introduced (matches T-49-07 disposition).

## Self-Check: PASSED

- FOUND: frontend/src/components/Patterns/SceneCompareModal.tsx
- FOUND: frontend/src/types/index.ts (modified — scene-compare types present)
- FOUND: frontend/src/lib/api.tsx (modified — regenerateScene/keepSceneVersion present)
- FOUND: frontend/src/components/Patterns/ScreenplayEditorView.tsx (modified — SceneCompareModal + trigger present)
- FOUND commits: d4b035c (Task 1), 66cb7e3 (Task 2), 0f657a8 (Task 3)
