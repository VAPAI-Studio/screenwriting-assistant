# Phase 49: Side-by-Side Quality Compare - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 7 (3 backend, 4 frontend)
**Analogs found:** 7 / 7 (all have strong in-repo analogs)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/services/template_ai_service.py` (add `regenerate_single_scene` helper) | service | transform (LLM gen) | `_generate_scripts` (same file, lines 305-481) | exact (same module, extract the per-scene body) |
| `backend/app/api/endpoints/wizards.py` (add regenerate-scene + keep endpoints) | route/controller | request-response + CRUD | `run_wizard` / `apply_wizard_result_to_db` (same file) | exact (same file, mirror auth + persist branch) |
| `backend/app/models/schemas.py` (add request/response schemas) | model (schema) | request-response | `WizardRunRequest` / `ScreenplayContentResponse` (same file, lines 483-558) | exact |
| `frontend/src/lib/api.tsx` (add `regenerateScene` + `keepSceneVersion`) | service (client) | request-response | `runWizard` / `generateShotlist` (same file) | exact |
| `frontend/src/types/index.ts` (add TS types) | model (types) | — | existing request/response interfaces (same file) | exact |
| `frontend/src/components/Patterns/SceneCompareModal.tsx` (NEW) | component (modal) | event-driven (mutation) | `CreateProjectModal.tsx` (Radix Dialog) + `ScreenplayEditorView` (paper renderer) | role-match (compose two analogs) |
| `frontend/src/components/Patterns/ScreenplayEditorView.tsx` (add trigger) | component | event-driven | itself (toolbar button + saveMutation pattern) | exact (extend in place) |

---

## Pattern Assignments

### `backend/app/services/template_ai_service.py` — `regenerate_single_scene` helper (service, transform)

**Analog:** `_generate_scripts` at `backend/app/services/template_ai_service.py:305-481`. This is the WHOLE point of D-49-01 — reuse the improved prompt body, do NOT write a divergent prompt.

**What to extract and reuse — the per-scene prompt body (lines 334-411):** The continuity block (334-345), the character/voice block (347-358), the UNCONDITIONAL craft block embedded in the prompt (391-397, lines `## Screenwriting Craft` ... `white space`), and the native-output TITLE contract (408-411). All four blocks MUST be present in the regenerated-scene prompt — the backend tests assert their anchor substrings (`"Story so far"`, `"distinct, consistent voice"`, `"## Screenwriting Craft"`, `"on-the-nose"`, `TITLE:`).

**Recommended refactor (planner discretion, lowest-risk):** Extract the single-scene body (lines 331-471, the loop interior) into a private `async def _generate_one_scene(self, ep, i, total, project_context, character_section, scene_outline, runtime_target, guidance, synopsis, prev_scene_text) -> dict` that returns `{title, content, episode_index}`. Then `_generate_scripts` calls it in its loop (behavior byte-identical → keeps phases 45-48 suites green per D-49-05), and the new public `regenerate_single_scene(...)` calls it once with the supplied `synopsis`/`prev_scene_text` for ONE episode. If a refactor feels risky against the existing test anchors, an additive standalone method that copies the prompt construction is acceptable — but then the anchor substrings must be kept verbatim.

**Native parse + title split to copy verbatim** (lines 429-461): the code-fence tolerance and the `TITLE:` line split (`first_line.strip().lower().startswith("title:")`), plus the empty-title fallback to `summary`. The regenerated scene MUST go through the same parse so its shape matches `screenplays[]`.

**LLM call signature to reuse** (lines 415-423):
```python
text = await chat_completion(
    messages=[
        {"role": "system", "content": "You are an expert screenwriter who lays out scenes in industry-standard screenplay format. Return the screenplay as native plain text only — no JSON, no markdown code fences."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7, max_tokens=4000, json_mode=False,
)
```
**Test-mock anchor:** patch `app.services.template_ai_service.chat_completion` (per CONTEXT code_context — the established mocking pattern for the script suites).

**Regenerate inputs** — fetch via the existing wizards.py helpers (do not reinvent):
- Project context: `_get_project_context(db, project, bible_context=...)` (`wizards.py:22-43`).
- Characters → `config["_characters"]`: `_get_character_data(db, project.id)` (`wizards.py:46-58`).
- Bible context: `build_bible_context(db, project)` (imported in `wizards.py:15`).
- Scene input for episode i: scene ListItems under `PhaseData(phase="scenes", subsection_key="scene_list")` ordered by `sort_order` (same query shape as `_get_character_data`, different phase/key).
- Continuity inputs (`synopsis`, `prev_scene_text`): per D-49-05 the planner may leave the global synopsis untouched; for the regenerate prompt, supply the stored `synopsis` from `screenplay_editor` PhaseData.content and `prev_scene_text = screenplays[episode_index - 1].content` (empty string for index 0 → no continuity block, matching lines 343-345).

---

### `backend/app/api/endpoints/wizards.py` — regenerate-scene + keep endpoints (route, request-response + CRUD)

**Analog (auth/DI/ownership shape):** `run_wizard` at `wizards.py:116-164`. Every new endpoint copies this exact header:
```python
@router.post("/regenerate-scene", response_model=schemas.RegenerateSceneResponse)
async def regenerate_scene(
    request: schemas.RegenerateSceneRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
```
(The 404-on-not-owned pattern is at lines 124-129 and repeated at 181-186, 204-209.)

**LATENCY DECISION (flagged — informs endpoint shape):** A single scene at `max_tokens=4000` can exceed the 30s `API_TIMEOUT`. Two valid shapes:
1. **Sync endpoint** returning the new scene directly — simplest, but the FRONTEND client MUST call it with the 120s `CHAT_TIMEOUT` AbortController (see `generateShotlist` analog `api.tsx:1002-1017`), not the default 30s `fetchWithTimeout`.
2. **run/poll** via the existing `WizardRun` infra (`run_wizard` → `_run_wizard_background` → `get_wizard_run`) — more moving parts, no client timeout worry. Given the UI-SPEC generating state already tolerates ~60s and copy says "up to a minute," the **sync endpoint + CHAT_TIMEOUT** is the lower-surface choice and is recommended unless gen reliably exceeds ~90s.

The regenerate endpoint returns the new `{title, content, episode_index}` as a PREVIEW and does NOT write (D-49-02).

**Analog (keep-new persistence):** `apply_wizard_result_to_db` `script_writer_wizard` branch at `wizards.py:250-285`. The keep endpoint mirrors this EXACTLY but updates ONE array slot instead of replacing the whole list:
```python
# Read screenplay_editor PhaseData (query shape from wizards.py:256-260)
phase_data = db.query(database.PhaseData).filter(
    database.PhaseData.project_id == project.id,
    database.PhaseData.phase == phase,                    # "write"
    database.PhaseData.subsection_key == "screenplay_editor",
).first()

content = dict(phase_data.content or {})
screenplays = content.get("screenplays", [])
# update ONE slot by episode_index (D-49-03: array-position key)
screenplays[episode_index] = {"title": new_title, "content": new_content, "episode_index": episode_index}
content["screenplays"] = screenplays           # leave content["synopsis"] untouched (D-49-05)
phase_data.content = content
flag_modified(phase_data, "content")           # the established JSONB write pattern (wizards.py:272)
```
Then update the matching `ScreenplayContent` row (D-49-03: match by `project_id` + `formatted_content["episode_index"]`; fall back to stable ordering if absent — NO migration):
```python
sc = db.query(database.ScreenplayContent).filter(
    database.ScreenplayContent.project_id == project.id,
).all()
# pick the row whose formatted_content.episode_index == episode_index (fallback: ordering)
# update sc.content = new_content; sc.formatted_content = {title,content,episode_index}
```
**Staleness — ONLY on keep-new** (D-49-02), reuse the imported helpers (`wizards.py:16`):
```python
_mark_breakdown_stale(db, project.id)
_mark_shotlist_stale(db, project.id)
db.commit()
```
(`_mark_breakdown_stale`/`_mark_shotlist_stale` defined at `phase_data.py:21-53` — they no-op when no breakdown/shots exist, and do NOT commit; the caller's `db.commit()` covers them.)

---

### `backend/app/models/schemas.py` — request/response schemas (model, request-response)

**Analog:** `WizardRunRequest` (`schemas.py:483-487`) and `ScreenplayContentResponse` (`schemas.py:549-558`).

- `RegenerateSceneRequest`: `project_id: UUID`, `phase: str` (default `"write"`), `episode_index: int`. Mirror `WizardRunRequest`'s `project_id: UUID` + `Field` usage.
- `RegenerateSceneResponse`: `title: str`, `content: str`, `episode_index: int`, optional `error: Optional[str] = None`. Plain `BaseModel`, no `from_attributes` needed (built from a dict).
- `KeepSceneVersionRequest`: `project_id: UUID`, `phase: str`, `episode_index: int`, `title: str`, `content: str`.
- Keep response: a small `{status, episode_index}` dict is fine (matches the `{"status": "success", ...}` return idiom in `apply_wizard_result_to_db`); no schema strictly required.

Use `model_config = ConfigDict(from_attributes=True)` only where reading from ORM (the `ScreenplayContentResponse` pattern, line 558) — the regenerate/keep responses are dict-built so they don't need it.

---

### `frontend/src/lib/api.tsx` — `regenerateScene` + `keepSceneVersion` client methods (service, request-response)

**Analog for the standard POST:** `runWizard` at `api.tsx:758-766` (uses `fetchWithTimeout` + `getHeaders()` + `JSON.stringify` + `if (!response.ok) throw`).

**Analog for the LONG-RUNNING call (USE THIS for `regenerateScene`):** `generateShotlist` at `api.tsx:995-1018` — the explicit `AbortController` + `CHAT_TIMEOUT` (120s) pattern, because regenerate exceeds the 30s `API_TIMEOUT` baked into `fetchWithTimeout` (`api.tsx:31`):
```typescript
async regenerateScene(data: { project_id: string; phase: string; episode_index: number }): Promise<RegenerateSceneResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT); // 120s — NOT the default 30s
  try {
    const response = await fetch(`${API_BASE_URL}/wizards/regenerate-scene`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify(data), signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!response.ok) throw new Error('Failed to regenerate scene');
    return response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') throw new Error('Request timeout');
    throw error;
  }
}
```
`keepSceneVersion` is a normal `fetchWithTimeout` POST (the persist is fast) following the `runWizard` shape. `CHAT_TIMEOUT` and `API_TIMEOUT` are already imported at `api.tsx:15`.

---

### `frontend/src/types/index.ts` — TS types (model)

**Analog:** the existing request/response interfaces in the same file (e.g. `BreakdownElementCreate`, `ShotCreate`). Add:
```typescript
export interface RegenerateSceneResponse { title: string; content: string; episode_index: number; error?: string; }
```
Mirror the backend `Screenplay` shape already declared inline in `ScreenplayEditorView.tsx:19-24` (`{ episode_index, title, content, error? }`) so panes and persistence share one shape. `WizardRunResponse` lives in `types/template.ts:184` — keep the new types in `types/index.ts` consistent with that style.

---

### `frontend/src/components/Patterns/SceneCompareModal.tsx` (NEW) (component, event-driven)

**Analog A — Radix Dialog skeleton:** `CreateProjectModal.tsx:71-201`. Copy the exact composition:
- `Dialog.Root open onOpenChange` (line 71), `Dialog.Portal`, `Dialog.Overlay` (line 73: `fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in`), `Dialog.Content` (line 74) — but resized per UI-SPEC to `w-[92vw] max-w-[1100px] h-[88vh]` with internal flex column.
- Header `Dialog.Title` + `Dialog.Close` icon button (lines 77-84) — reuse the `<X className="h-4 w-4" />` close button styling verbatim.
- Footer actions use `Button` from `../UI/Button` (imported line 9): `variant="outline"` for "Keep current", `variant="default"` (amber) for "Keep new version" — matches UI-SPEC Actions/Footer table.

**Analog B — screenplay paper renderer (both panes):** `ScreenplayEditorView.tsx:304-306` view-mode `<pre>`:
```tsx
<pre className="font-screenplay text-[13px] text-foreground/90 whitespace-pre-wrap break-words" style={{ lineHeight: '20px' }}>
  {paneText}
</pre>
```
wrapped in the paper panel `bg-[hsl(240,5%,8.5%)] border border-border/30 rounded-sm shadow-2xl` (line 289), with the UI-SPEC's reduced `40px 48px` padding (NOT the full-page `72px 80px` at line 290), applied identically to BOTH panes. No pagination needed (single scene per pane).

**Analog C — keep-new mutation + invalidation:** `ScreenplayEditorView.tsx` `saveMutation` at lines 153-165:
```tsx
const keepMutation = useMutation({
  mutationFn: () => api.keepSceneVersion({ project_id, phase, episode_index, title, content }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsection.key) });
    onOpenChange(false);
  },
});
```
`QUERY_KEYS.SUBSECTION_DATA` is the exact key the screenplay view reads (`constants.ts:180`), so invalidating it re-renders the kept scene (UI-SPEC keep-new success state).

**Regenerate-on-open:** kick off `api.regenerateScene(...)` when the modal opens (right pane → generating state). Use a `useMutation` or `useQuery(enabled: open)`; on error, retain the modal open with the destructive error block (UI-SPEC error state) — "Keep current" stays a safe exit.

**Icons:** `Sparkles`/`Wand2`, `Loader2` (spin), `X`, `Check`, `FileText` from `lucide-react` (UI-SPEC Design System) — same import style as `ScreenplayEditorView.tsx:3`.

---

### `frontend/src/components/Patterns/ScreenplayEditorView.tsx` — add per-scene "Regenerate & Compare" trigger (component, event-driven)

**Analog (in-file):** the toolbar `Edit` button at lines 241-247 (ghost style `text-xs font-medium text-foreground/80 bg-muted/40 border border-border/40 rounded-lg hover:bg-muted/70`) and the absolute hover affordances at lines 294-301 (`absolute top-5 right-7` page number, `absolute top-5 left-7` group-hover "Click to edit").

**Placement (UI-SPEC Component Spec — Per-Scene Trigger):** a per-scene-header inline button, NOT a modal picker. The current renderer paginates the MERGED document (`buildDocument` lines 27-34, `paginateText` lines 82-89), so scene boundaries are not currently per-page. The planner must surface a per-scene anchor — simplest faithful approach: render the trigger keyed to each `screenplays[i]` (e.g. a thin per-scene control row, or anchor at each title boundary), passing that scene's `episode_index` to `SceneCompareModal`.
- Style: ghost icon+label matching the `Edit` button, amber `Sparkles`/`Wand2` `h-3.5 w-3.5`, label "Regenerate & Compare" (icon-only `aria-label` when narrow).
- **Must `stopPropagation`** so clicking it does NOT trigger the page-level `onClick={startEditing}` (line 291) — UI-SPEC accessibility note.
- Manage modal open state + selected `episode_index` via local `useState`; render `<SceneCompareModal open=... onOpenChange=... episodeIndex=... .../>` once.

---

## Shared Patterns

### Project ownership + auth (all backend endpoints)
**Source:** `wizards.py:116-129` (`Depends(get_current_user)`, `Depends(get_db)`, owner-scoped `.filter(owner_id == current_user.id)`, 404 if not found).
**Apply to:** both new backend endpoints. Mock auth `Bearer mock-token` in dev (CLAUDE.md); backend tests authenticate the same way.

### JSONB write (keep-new persistence)
**Source:** `wizards.py:271-272` — assign a fresh dict to `phase_data.content`, then `flag_modified(phase_data, "content")`. This is the established Phase 45/46 pattern for mutating `screenplay_editor` content; SQLAlchemy will NOT detect in-place dict mutation without it.
**Apply to:** the keep-new endpoint.

### Staleness marking (keep-new only)
**Source:** `phase_data.py:21-53` helpers, imported at `wizards.py:16`, called at `wizards.py:282-283`.
**Apply to:** keep-new endpoint ONLY (D-49-02). Regenerate-preview and keep-current never mark stale. The helpers no-op when no breakdown/shots exist and rely on the caller's `db.commit()`.

### Client error/timeout handling (frontend)
**Source:** `api.tsx:1002-1017` (`generateShotlist`) for long calls; `api.tsx:758-766` (`runWizard`) for fast calls. Both: `getHeaders()` Bearer auth, `if (!response.ok) throw new Error(...)`, AbortController → `'Request timeout'`.
**Apply to:** `regenerateScene` (long, CHAT_TIMEOUT) and `keepSceneVersion` (fast, fetchWithTimeout).

### Modal + mutation + invalidation (frontend)
**Source:** `CreateProjectModal.tsx` (Dialog skeleton + `useMutation` onSuccess → `invalidateQueries` + `onOpenChange(false)`, lines 38-47) and `ScreenplayEditorView.tsx:153-165` (`SUBSECTION_DATA` invalidation).
**Apply to:** `SceneCompareModal` keep-new flow.

---

## No Analog Found

None. Every file maps to a strong in-repo analog (most in the SAME file being modified). The only genuinely-new artifact is `SceneCompareModal.tsx`, and it is a composition of two existing analogs (CreateProjectModal Dialog shell + ScreenplayEditorView paper renderer), so it requires no novel pattern.

---

## Testing Notes (carry into plans)

- **Backend gets pytest** (`backend/app/tests`). New tests (CONTEXT code_context): (1) `regenerate_single_scene` returns one `{title,content,episode_index}` whose PROMPT contains the improved-path anchors (continuity `"Story so far"`, voice `"distinct, consistent voice"`, craft `"## Screenwriting Craft"`/`"on-the-nose"`, native `TITLE:`); (2) keep-new persists into `screenplays[i]` + the matching `ScreenplayContent` row + marks breakdown/shotlist stale; (3) regenerate-preview and keep-current do NOT persist and do NOT mark stale. Patch `app.services.template_ai_service.chat_completion`. New tests MUST pass in isolation (`.planning/v6.0-PREEXISTING-TEST-CONCERN.md`). Keep existing suites green (continuity 10, voice 8, craft 6, wizard 3) — favoring the additive/extract-shared-helper refactor protects their anchor assertions.
- **NO frontend test harness exists** — only `tsc` (`npm run build`) + ESLint (`npm run lint`). Frontend verification = tsc + lint + manual UAT against the UI-SPEC states table. Do NOT stand up vitest/jest (CONTEXT deferred + out of scope).

---

## Metadata

**Analog search scope:** `backend/app/services`, `backend/app/api/endpoints`, `backend/app/models`, `frontend/src/lib`, `frontend/src/components/{Patterns,Projects,UI}`, `frontend/src/types`.
**Files scanned (read):** template_ai_service.py (305-481), wizards.py (full), schemas.py (483-558), phase_data.py (21-53), api.tsx (targeted ranges), ScreenplayEditorView.tsx (full), CreateProjectModal.tsx (full), Button.tsx (full), constants.ts (grep), database.py (286-297), types/index.ts (grep).
**Pattern extraction date:** 2026-06-06
