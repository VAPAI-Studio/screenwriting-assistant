# Phase 23: Assets Panel & Media Display - Research

**Researched:** 2026-03-19
**Domain:** React frontend -- panel toggle, media display, drag-and-drop uploads, audio playback
**Confidence:** HIGH

## Summary

Phase 23 is a **frontend-only** phase. The backend media API (Phase 22) and breakdown elements API (Phase 10/13) are fully implemented. The work is adding an "Assets" view to the existing left panel in `BreakdownLayout.tsx`, which currently renders only `ScriptReadView`. The Assets view must display breakdown elements grouped by category with their attached media (image thumbnails, audio players), support drag-and-drop upload, and preserve panel state when toggling between Script and Assets views.

The codebase already has all the patterns needed: `BreakdownPage.tsx` shows how to fetch breakdown elements with `api.getBreakdownElements()`, `CategoryTabs.tsx` demonstrates Radix UI tabs for category grouping, `ElementCard.tsx` provides the element display pattern, and `BookManager.tsx` shows FormData-based file upload. The media API returns `file_path` (e.g., `/media/{project_id}/{filename}`) and `thumbnail_path` (e.g., `/media/{project_id}/thumbs/{filename}`) -- these paths are served by FastAPI's `StaticFiles` mount at `/media`. The Vite dev proxy currently only proxies `/api`, so a `/media` proxy entry must be added.

**Primary recommendation:** Build the AssetsPanel as a sibling to ScriptReadView, toggled by a local state variable in BreakdownLayout. Use the native HTML5 drag-and-drop API (no library needed). Use the native HTML `<audio>` element with custom controls for audio playback. Preserve scroll position and expanded-item state via `useRef` when toggling views.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ASST-01 | Left panel has a toggle between "Script" view and "Assets" view | BreakdownLayout already has left panel with `BreakdownPanel` wrapper; add toggle state and conditional rendering |
| ASST-02 | Assets view shows breakdown elements grouped by category (Characters, Locations, Props, Wardrobe, Vehicles) | Reuse `BREAKDOWN_CATEGORIES` constant and `api.getBreakdownElements()` -- same pattern as `CategoryTabs.tsx` |
| ASST-03 | Each element shows attached media (image thumbnails, audio players) | Use `api.listMedia()` (needs to be added to frontend api.tsx) filtered by `element_id`; media API returns `file_path` and `thumbnail_path` |
| ASST-04 | User can upload media from assets panel via drag-and-drop or file picker | HTML5 drag-and-drop API + FormData upload to `POST /api/media/{project_id}` with `element_id` form field |
| ASST-05 | Toggling between Script and Assets preserves panel state (scroll position, expanded items) | Use `useRef` to store scroll position and expanded element IDs; restore on re-mount via `display: none` CSS toggle or ref-based state preservation |
| MDIA-03 | Uploaded images display as thumbnails in the assets panel | Backend generates thumbnails at upload time (Phase 22); frontend renders `<img src={thumbnail_path}>` |
| MDIA-04 | Uploaded audio files have playable controls (play, pause, stop) | Native `<audio>` element with custom UI wrapping `play()`, `pause()`, `currentTime = 0` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.2 | Component framework | Already in project |
| @tanstack/react-query | 5.x | Data fetching, caching, mutations | Already in project; media queries follow existing patterns |
| @radix-ui/react-tabs | 1.0.4 | Category tabs | Already in project; used in BreakdownPage |
| lucide-react | 0.314 | Icons (Image, Music, Upload, Play, Pause, Square) | Already in project |
| Tailwind CSS | 3.4 | Styling | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Native HTML5 DnD API | N/A | Drag-and-drop file upload | `onDragOver`, `onDragLeave`, `onDrop` events on drop zone |
| Native `<audio>` element | N/A | Audio playback | `HTMLAudioElement` API: `play()`, `pause()`, `currentTime = 0` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native DnD API | react-dropzone | react-dropzone adds convenience but is an unnecessary dependency for a single drop zone; native API is well-documented and ~20 lines of code |
| Native `<audio>` | wavesurfer.js / react-h5-audio-player | Waveform visualization is explicitly deferred to v3.1 (ADVM-01); native element is sufficient for play/pause/stop |
| CSS `display: none` toggle | Conditional rendering | `display: none` preserves DOM state (scroll position) without additional ref management; avoids re-mount cost |

**Installation:**
No new dependencies needed. Everything is already available in the project.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/Breakdown/
  BreakdownLayout.tsx          # MODIFY: add leftPanelView state, toggle, conditional render
  ScriptReadView.tsx           # UNCHANGED
  AssetsPanel.tsx              # NEW: category-grouped element list with media
  AssetElementCard.tsx         # NEW: single element with media thumbnails + audio + upload
  MediaThumbnail.tsx           # NEW: image thumbnail component
  AudioPlayer.tsx              # NEW: custom audio player with play/pause/stop
  MediaUploadZone.tsx          # NEW: drag-and-drop + file picker upload zone
```

### Pattern 1: Left Panel Toggle (ASST-01)

**What:** Toggle between Script and Assets views in the left panel
**When to use:** When the left panel needs to switch between two views while preserving state

```typescript
// In BreakdownLayout.tsx
const [leftPanelView, setLeftPanelView] = useState<'script' | 'assets'>('script');

// In the BreakdownPanel title area, replace static title with toggle
<div className="flex items-center gap-1">
  <button
    onClick={() => setLeftPanelView('script')}
    className={leftPanelView === 'script' ? 'active-style' : 'inactive-style'}
  >
    Script
  </button>
  <button
    onClick={() => setLeftPanelView('assets')}
    className={leftPanelView === 'assets' ? 'active-style' : 'inactive-style'}
  >
    Assets
  </button>
</div>

// Render both but hide inactive to preserve state (ASST-05)
<div style={{ display: leftPanelView === 'script' ? 'block' : 'none' }}>
  <ScriptReadView projectId={projectId} />
</div>
<div style={{ display: leftPanelView === 'assets' ? 'block' : 'none' }}>
  <AssetsPanel projectId={projectId} />
</div>
```

### Pattern 2: State Preservation via CSS Display Toggle (ASST-05)

**What:** Preserve scroll position and expanded items when toggling views
**When to use:** When switching between two views that should maintain their state

The key insight: instead of conditionally rendering (`{view === 'script' && <ScriptReadView />}`), render both and use `display: none` on the inactive view. This keeps the DOM alive, preserving:
- Scroll position (the scrollable container stays mounted)
- Expanded/collapsed elements (React state persists)
- React Query cache hits (components remain subscribed)

```typescript
// Both are always mounted, only one is visible
<div className="flex-1 overflow-hidden" style={{ display: leftPanelView === 'script' ? 'contents' : 'none' }}>
  <ScriptReadView projectId={projectId} />
</div>
<div className="flex-1 overflow-hidden" style={{ display: leftPanelView === 'assets' ? 'contents' : 'none' }}>
  <AssetsPanel projectId={projectId} />
</div>
```

### Pattern 3: Media Fetch Per Element

**What:** Fetch media for each element using the existing media API
**When to use:** When displaying media attached to breakdown elements

```typescript
// In AssetElementCard.tsx
const { data: media } = useQuery({
  queryKey: QUERY_KEYS.ELEMENT_MEDIA(element.id),
  queryFn: () => api.listElementMedia(projectId, element.id),
  enabled: isExpanded, // only fetch when element is expanded
  staleTime: 60_000,
});
```

The API endpoint `GET /api/media/{project_id}?element_id={element_id}` already supports filtering by element. The frontend `api.tsx` needs a new function to expose this.

### Pattern 4: Drag-and-Drop Upload

**What:** HTML5 native drag-and-drop for file upload
**When to use:** When users need to upload files via drag-and-drop or file picker

```typescript
function MediaUploadZone({ projectId, elementId, onUploadComplete }: Props) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach(file => uploadFile(file));
  };

  const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    if (elementId) formData.append('element_id', elementId);
    // POST to /api/media/{project_id}
    await api.uploadMedia(projectId, formData);
    onUploadComplete();
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={isDragOver ? 'border-primary bg-primary/5' : 'border-dashed border-border'}
    >
      {/* Drop zone content + file picker button */}
      <input type="file" accept="image/*,audio/*" onChange={...} className="hidden" />
    </div>
  );
}
```

### Pattern 5: Audio Player Controls

**What:** Custom audio player with play, pause, stop buttons
**When to use:** For audio files attached to breakdown elements

```typescript
function AudioPlayer({ src, filename }: { src: string; filename: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const play = () => { audioRef.current?.play(); setIsPlaying(true); };
  const pause = () => { audioRef.current?.pause(); setIsPlaying(false); };
  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
  };

  return (
    <div className="flex items-center gap-2">
      <audio ref={audioRef} src={src} onEnded={() => setIsPlaying(false)} />
      {isPlaying ? (
        <button onClick={pause}><Pause /></button>
      ) : (
        <button onClick={play}><Play /></button>
      )}
      <button onClick={stop}><Square /></button>
      <span className="text-xs truncate">{filename}</span>
    </div>
  );
}
```

### Anti-Patterns to Avoid
- **Fetching all media at panel mount:** Do NOT fetch media for all elements at once. Fetch per-element when expanded to avoid N+1 waterfalls on the frontend. React Query handles caching.
- **Using conditional rendering for view toggle:** Do NOT use `{view === 'script' && <ScriptReadView />}` because it destroys the component and loses scroll position and expanded state.
- **Installing react-dropzone or audio player libraries:** The requirements are simple enough that native APIs suffice. Adding dependencies for minimal use increases bundle size and maintenance burden.
- **Hard-coding media URLs:** Always construct media URLs from the `file_path` and `thumbnail_path` returned by the API. In dev mode, ensure the Vite proxy covers `/media`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Category grouping | Custom category logic | `BREAKDOWN_CATEGORIES` constant + `api.getBreakdownElements(projectId, category)` | Already defined and used in BreakdownPage |
| Tab UI | Custom tab implementation | `@radix-ui/react-tabs` | Already in the project, handles accessibility and keyboard nav |
| File type validation | Frontend-only validation | Let backend validate; show backend error messages | Backend already validates types and size (Phase 22) |
| Thumbnail generation | Frontend-side resizing | Backend Pillow thumbnails via `thumbnail_path` | Backend generates WebP thumbnails at upload time |

**Key insight:** This phase is purely frontend assembly. All backend APIs exist. The main complexity is UI state management (toggle, scroll preservation, expand/collapse) and integrating existing API calls into new components.

## Common Pitfalls

### Pitfall 1: Media URL Proxy Missing
**What goes wrong:** Images and audio fail to load in dev mode with 404 errors
**Why it happens:** Vite only proxies `/api` but media is served at `/media/{project_id}/...` by FastAPI StaticFiles
**How to avoid:** Add `/media` to the Vite proxy config:
```typescript
// vite.config.ts
proxy: {
  '/api': { target: '...', changeOrigin: true },
  '/media': { target: '...', changeOrigin: true },
}
```
**Warning signs:** Broken images in dev mode, network tab showing 404 for `/media/...` URLs

### Pitfall 2: Scroll Position Loss on View Toggle
**What goes wrong:** User expands several elements, scrolls down, switches to Script, switches back -- everything is reset
**Why it happens:** Conditional rendering (`&&`) unmounts the component, destroying all DOM state
**How to avoid:** Use `display: none` / `display: contents` instead of conditional rendering. Both views stay mounted but only one is visible.
**Warning signs:** Testing toggle and noticing elements collapse and scroll jumps to top

### Pitfall 3: FormData Content-Type Header
**What goes wrong:** File upload returns 422 or fails
**Why it happens:** Setting `Content-Type: application/json` on a FormData request. The browser must set `Content-Type: multipart/form-data` with the correct boundary automatically.
**How to avoid:** When uploading with FormData, do NOT set Content-Type header. Use the existing pattern from `uploadBook()`:
```typescript
// Authorization header only -- NO Content-Type header
headers: { 'Authorization': getAuthToken() }
```
**Warning signs:** 422 Unprocessable Entity or "Invalid content type" errors

### Pitfall 4: Fetching Media for All Elements on Mount
**What goes wrong:** Panel load triggers dozens of API calls, slow initial render
**Why it happens:** Each `AssetElementCard` fetches its media on mount
**How to avoid:** Only fetch media when an element is expanded. Use `enabled: isExpanded` on the query.
**Warning signs:** Network waterfall of `/api/media/{project_id}?element_id=...` calls on panel open

### Pitfall 5: Audio Playback Overlap
**What goes wrong:** Multiple audio files play simultaneously when user clicks play on different items
**Why it happens:** Each `AudioPlayer` manages its own `<audio>` element independently
**How to avoid:** Lift playing state to the `AssetsPanel` level or use a simple context/callback that pauses the currently-playing audio before starting a new one.
**Warning signs:** Audio cacophony when testing multiple audio elements

### Pitfall 6: BreakdownPanel Title Replacement
**What goes wrong:** The toggle replaces the panel title but breaks the collapsed state display
**Why it happens:** `BreakdownPanel` renders the title in both expanded and collapsed states
**How to avoid:** Either modify `BreakdownPanel` to accept a custom header render prop, or place the toggle inside the children area below the header. The simplest approach: keep the static title "Script / Assets" and put the toggle buttons inside the panel content area at the top.
**Warning signs:** Collapsed panel shows wrong or broken text

## Code Examples

### API Functions (add to api.tsx)

```typescript
// Media API functions to add to the api object in api.tsx

async listElementMedia(projectId: string, elementId: string): Promise<AssetMedia[]> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/media/${projectId}?element_id=${elementId}`,
    { headers: getHeaders() }
  );
  if (!response.ok) throw new Error('Failed to fetch element media');
  return response.json();
},

async uploadMedia(projectId: string, formData: FormData): Promise<AssetMedia> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/media/${projectId}`,
    {
      method: 'POST',
      headers: { 'Authorization': getAuthToken() },  // NO Content-Type!
      body: formData,
    }
  );
  if (!response.ok) throw new Error('Failed to upload media');
  return response.json();
},

async deleteMedia(projectId: string, mediaId: string): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/media/${projectId}/${mediaId}`,
    {
      method: 'DELETE',
      headers: getHeaders(),
    }
  );
  if (!response.ok) throw new Error('Failed to delete media');
},
```

### TypeScript Types (add to types/index.ts)

```typescript
// AssetMedia type matching backend AssetMediaResponse
export interface AssetMedia {
  id: string;
  project_id: string;
  element_id: string | null;
  shot_id: string | null;
  file_type: 'image' | 'audio';
  file_path: string;
  thumbnail_path: string | null;
  original_filename: string;
  file_size_bytes: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
}
```

### Query Keys (add to constants.ts)

```typescript
// Add to QUERY_KEYS
ELEMENT_MEDIA: (elementId: string) => ['element-media', elementId] as const,
PROJECT_MEDIA: (projectId: string) => ['project-media', projectId] as const,
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom file upload libraries | Native HTML5 File API + DnD | Stable since 2020 | No library needed for basic drag-and-drop |
| `<audio>` with browser-default controls | Custom controls wrapping `<audio>` | Always available | Consistent cross-browser UI while using native playback |
| Conditional rendering for view switching | CSS display toggle for state preservation | React pattern | Preserves DOM state including scroll position |

**Deprecated/outdated:**
- Nothing relevant -- all patterns used are stable.

## Open Questions

1. **Per-element media fetch vs. bulk fetch**
   - What we know: API supports both `GET /api/media/{project_id}` (all project media) and `GET /api/media/{project_id}?element_id={id}` (element-filtered)
   - What's unclear: For a project with many elements but few media files, a single bulk fetch might be more efficient than per-element lazy fetches
   - Recommendation: Start with per-element fetch on expand (lazy loading). If performance is an issue, switch to a single project-level fetch and group client-side. The bulk approach is simpler but loads all media data upfront; the lazy approach is more scalable.

2. **Vite proxy for /media**
   - What we know: `/media` is not currently proxied in vite.config.ts; in Docker the backend serves `/media` directly on port 8000
   - What's unclear: Whether Docker Compose nginx or the frontend container handles `/media` routing
   - Recommendation: Add `/media` to the Vite proxy for dev mode. In Docker, the frontend container accesses the backend directly, so the proxy config handles both cases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + manual (frontend) |
| Config file | backend/pytest.ini (if exists) or pyproject.toml |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_media_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASST-01 | Left panel toggle between Script/Assets | manual | Visual inspection in browser | N/A |
| ASST-02 | Assets view shows elements grouped by category | manual | Visual inspection; relies on existing breakdown API tests | N/A |
| ASST-03 | Elements display attached media (thumbnails, audio) | manual | Visual inspection; media API tested in test_media_api.py | N/A |
| ASST-04 | Drag-and-drop / file picker upload from assets panel | manual | Visual inspection + network tab verification | N/A |
| ASST-05 | Toggle preserves panel state (scroll, expanded items) | manual | Visual inspection: scroll, expand items, toggle, toggle back | N/A |
| MDIA-03 | Images display as thumbnails | manual | Visual inspection: upload image, verify thumbnail renders | N/A |
| MDIA-04 | Audio files have play/pause/stop controls | manual | Visual inspection: upload audio, verify controls work | N/A |

### Sampling Rate
- **Per task commit:** `npm run build` (TypeScript compilation check)
- **Per wave merge:** `npm run build && cd backend && pytest app/tests/test_media_api.py -x`
- **Phase gate:** Full build + existing backend tests pass

### Wave 0 Gaps
- None -- this phase is frontend-only; backend API tests already exist from Phase 22. Frontend has no unit test infrastructure (no jest/vitest configured), which is consistent with the project convention.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `BreakdownLayout.tsx`, `ScriptReadView.tsx`, `BreakdownPanel.tsx` -- current left panel architecture
- Codebase analysis: `media.py` (backend) -- media API endpoints, URL patterns, file type handling
- Codebase analysis: `api.tsx` -- existing API wrapper patterns for FormData uploads (see `uploadBook`)
- Codebase analysis: `CategoryTabs.tsx`, `ElementCard.tsx` -- breakdown element display patterns
- Codebase analysis: `vite.config.ts` -- proxy configuration (only `/api` proxied currently)
- Codebase analysis: `constants.ts` -- `BREAKDOWN_CATEGORIES`, `QUERY_KEYS`, `STORAGE_KEYS`
- Codebase analysis: `types/index.ts` -- `BreakdownElement`, `BreakdownCategory` types

### Secondary (MEDIUM confidence)
- HTML5 Drag and Drop API -- stable web standard, well-supported in all modern browsers
- HTMLAudioElement API -- stable web standard, `play()`, `pause()`, `currentTime` are universally supported

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies
- Architecture: HIGH -- patterns extracted directly from existing codebase
- Pitfalls: HIGH -- identified from codebase analysis (proxy gap, FormData header, scroll preservation)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (30 days -- stable patterns, no fast-moving dependencies)
