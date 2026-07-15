import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Pencil, Check, X, Sparkles, Send, ExternalLink } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, VAPAI_ENABLED } from '../../lib/constants';
import type { SendToVapaiResponse } from '../../types';
import type { SubsectionConfig, TemplateConfig, PhaseDataResponse } from '../../types/template';
import { SceneCompareModal } from './SceneCompareModal';

const LINES_PER_PAGE = 55;
const LINE_HEIGHT_PX = 20;

interface ScreenplayEditorViewProps {
  subsection: SubsectionConfig;
  projectId: string;
  phase: string;
  phaseData: PhaseDataResponse | null;
  templateConfig: TemplateConfig;
}

interface Screenplay {
  episode_index: number;
  title: string;
  content: string;
  error?: string;
}

/** Merge all screenplays into one continuous document with scene headers. */
function buildDocument(screenplays: Screenplay[]): string {
  return screenplays
    .map((sp, i) => {
      const header = sp.title ? `${sp.title.toUpperCase()}\n\n` : '';
      return (i > 0 ? '\n\n\n' : '') + header + sp.content;
    })
    .join('');
}

/**
 * Pure heading-based splitter for the FROM-SCRATCH (zero-originals) case.
 *
 * Splits hand-written text into one scene per screenplay slugline (INT./EXT. …).
 * The heading line becomes the scene `title`; `content` is the body AFTER the
 * heading line — the slugline is STRIPPED from content because `buildDocument`
 * re-prepends `title.toUpperCase()` on render, so keeping the slugline in content
 * too would double-render it. Mirrors generated scenes (title rendered once,
 * content is the body). Sequential `episode_index` 0,1,2…
 *
 * - No recognizable heading in non-empty text → one `{title:"Untitled", content:<all>, episode_index:0}`.
 * - Empty/whitespace text → `[]`.
 * - NEVER returns `[]` for non-empty text.
 *
 * Pure (no React/DOM deps) so it is unit-testable in isolation later.
 */
function splitByHeadings(text: string): Screenplay[] {
  if (!text.trim()) return [];

  // Slugline at line start (optional leading spaces): INT./EXT./INT./EXT./I/E/E/I etc.
  const headingRe = /^\s*(INT\.?\/?EXT\.?|EXT\.?\/?INT\.?|INT\.?|EXT\.?|I\/E|E\/I)[\s.]/i;

  const lines = text.split('\n');
  const scenes: Screenplay[] = [];
  let currentTitle: string | null = null;
  let currentBody: string[] = [];
  const preamble: string[] = []; // text before the first slugline (e.g. FADE IN:, title page)

  const flush = () => {
    if (currentTitle === null) return;
    // Strip a single immediately-following blank line from the body start.
    if (currentBody.length > 0 && currentBody[0].trim() === '') {
      currentBody = currentBody.slice(1);
    }
    scenes.push({
      episode_index: scenes.length,
      title: currentTitle.trim(),
      content: currentBody.join('\n').replace(/\n+$/, ''),
    });
    currentBody = [];
  };

  for (const line of lines) {
    if (headingRe.test(line)) {
      flush();
      currentTitle = line.trim();
    } else if (currentTitle !== null) {
      currentBody.push(line);
    } else {
      // Before the first heading: keep it (WR-01 — never drop preamble like FADE IN:).
      preamble.push(line);
    }
  }
  flush();

  if (scenes.length === 0) {
    // Non-empty text without any recognizable heading → single Untitled scene.
    return [{ episode_index: 0, title: 'Untitled', content: text.trim() }];
  }

  // Preserve any preamble before the first slugline as a leading "Untitled" scene
  // (WR-01: otherwise FADE IN: / a title page typed before scene 1 is lost on save).
  const preambleText = preamble.join('\n').trim();
  if (preambleText) {
    scenes.unshift({ episode_index: 0, title: 'Untitled', content: preambleText });
    scenes.forEach((s, i) => (s.episode_index = i)); // re-index after unshift
  }
  return scenes;
}

/** Re-split edited document back into individual screenplays using original titles as anchors. */
function splitToScreenplays(text: string, originals: Screenplay[]): Screenplay[] {
  if (originals.length === 0) return splitByHeadings(text);
  if (originals.length === 1) {
    const o = originals[0];
    let cleaned = text;
    const titleUp = o.title?.toUpperCase();
    if (titleUp && cleaned.startsWith(titleUp)) {
      cleaned = cleaned.slice(titleUp.length).replace(/^\n+/, '');
    }
    return [{ ...o, content: cleaned.trim() }];
  }

  // Find each title in the document to determine section boundaries
  const anchors: { idx: number; titleLen: number; origIdx: number }[] = [];
  let searchFrom = 0;
  for (let i = 0; i < originals.length; i++) {
    const titleUp = originals[i].title?.toUpperCase();
    if (!titleUp) continue;
    const idx = text.indexOf(titleUp, searchFrom);
    if (idx !== -1) {
      anchors.push({ idx, titleLen: titleUp.length, origIdx: i });
      searchFrom = idx + titleUp.length;
    }
  }

  if (anchors.length === 0) {
    return [{ ...originals[0], content: text.trim() }];
  }

  return anchors.map((a, i) => {
    const contentStart = a.idx + a.titleLen;
    const contentEnd =
      i < anchors.length - 1 ? findSectionBreak(text, anchors[i + 1].idx) : text.length;
    const content = text.slice(contentStart, contentEnd).replace(/^\n+/, '').replace(/\n+$/, '');
    return { ...originals[a.origIdx], content };
  });
}

function findSectionBreak(text: string, nextTitleIdx: number): number {
  // Walk back from the next title to find the triple-newline separator
  const tripleNl = text.lastIndexOf('\n\n\n', nextTitleIdx);
  return tripleNl !== -1 && tripleNl > 0 ? tripleNl : nextTitleIdx;
}

/** Split text into pages of LINES_PER_PAGE lines each. */
function paginateText(text: string): string[] {
  const lines = text.split('\n');
  const pages: string[] = [];
  for (let i = 0; i < lines.length; i += LINES_PER_PAGE) {
    pages.push(lines.slice(i, i + LINES_PER_PAGE).join('\n'));
  }
  return pages.length > 0 ? pages : [''];
}

export function ScreenplayEditorView({
  subsection,
  projectId,
  phase,
  phaseData,
}: ScreenplayEditorViewProps) {
  const queryClient = useQueryClient();
  const raw = phaseData?.content as Record<string, any> | null;
  const screenplays: Screenplay[] = raw?.screenplays || [];
  const fullDocument = useMemo(() => buildDocument(screenplays), [screenplays]);

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(fullDocument);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasChanges, setHasChanges] = useState(false);
  // Per-scene "Regenerate & Compare" — null when closed (EVAL-01 / D-49-04).
  const [compareIndex, setCompareIndex] = useState<number | null>(null);

  const pageEls = useRef<Map<number, HTMLDivElement>>(new Map());
  const editRef = useRef<HTMLTextAreaElement>(null);

  const displayText = isEditing ? editText : fullDocument;
  const pages = useMemo(() => paginateText(displayText), [displayText]);
  const totalPages = pages.length;

  // Keep edit buffer in sync when backend data changes
  useEffect(() => {
    if (!isEditing) setEditText(fullDocument);
  }, [fullDocument, isEditing]);

  // --- View mode: IntersectionObserver tracks visible page ---
  useEffect(() => {
    if (isEditing) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let best = currentPage;
        let bestRatio = 0;
        entries.forEach((e) => {
          if (e.intersectionRatio > bestRatio) {
            bestRatio = e.intersectionRatio;
            best = Number(e.target.getAttribute('data-page') || 1);
          }
        });
        if (bestRatio > 0) setCurrentPage(best);
      },
      { threshold: [0.1, 0.3, 0.5, 0.7] },
    );

    pageEls.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [pages.length, isEditing]);

  // --- Edit mode: derive page number from scroll offset ---
  const handleEditScroll = useCallback(() => {
    if (!editRef.current) return;
    const { scrollTop } = editRef.current;
    const paddingTop = 72; // matches page padding
    const lineAtTop = Math.floor(Math.max(0, scrollTop - paddingTop) / LINE_HEIGHT_PX);
    const page = Math.floor(lineAtTop / LINES_PER_PAGE) + 1;
    setCurrentPage(Math.min(page, totalPages));
  }, [totalPages]);

  // --- Mutations ---
  const saveMutation = useMutation({
    mutationFn: (updated: Screenplay[]) =>
      api.updateSubsectionData(projectId, phase, subsection.key, {
        screenplays: updated,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsection.key),
      });
      setHasChanges(false);
      setIsEditing(false);
    },
  });

  const handleSave = () => saveMutation.mutate(splitToScreenplays(editText, screenplays));

  // Push the completed screenplay to vapai-studio. Feedback is shown inline via an
  // alert banner below the toolbar (the app has no toast system).
  //
  // Series episodes: sending with no scope gets a 409 (isSeriesEpisode); we then
  // show an inline choice — send just this episode into the series, or the whole
  // series. The chosen scope is passed on the retry. showId comes from the 409.
  const [seriesChoice, setSeriesChoice] = useState<{ showId: string } | null>(null);
  const sendToVapaiMutation = useMutation<SendToVapaiResponse, Error, 'series' | 'standalone' | undefined>({
    mutationFn: (scope) => api.sendToVapai(projectId, scope),
    onMutate: () => setSeriesChoice(null),
    onError: (err: Error & { isSeriesEpisode?: boolean; showId?: string }) => {
      if (err.isSeriesEpisode && err.showId) {
        setSeriesChoice({ showId: err.showId });
      }
    },
  });
  const sendSeriesMutation = useMutation({
    mutationFn: (showId: string) => api.sendSeriesToVapai(showId),
    // Choosing "toda la serie" is a fresh action: clear both the choice panel AND
    // the prior 409 that sendToVapaiMutation is still holding, so its error banner
    // (gated on !seriesChoice) doesn't flash the 409 message as a real failure.
    onMutate: () => {
      setSeriesChoice(null);
      sendToVapaiMutation.reset();
    },
  });

  const handleDiscard = () => {
    setEditText(fullDocument);
    setHasChanges(false);
    setIsEditing(false);
  };

  const startEditing = () => {
    // From an existing screenplay, seed the buffer with the full document; from
    // an empty project (no scenes yet) start with a blank buffer so the writer
    // begins from scratch (D-54-02).
    setEditText(screenplays.length === 0 ? '' : fullDocument);
    setIsEditing(true);
    setHasChanges(false);
  };

  // =========== WRITABLE EMPTY STATE (D-54-02) ===========
  // When there are no scenes yet AND we are not editing, offer a "Start writing"
  // affordance that enters edit mode with a blank buffer + slugline placeholder.
  // Once editing begins, fall through to the main editor's edit path below.
  if (screenplays.length === 0 && !isEditing) {
    return (
      <div className="p-8 max-w-3xl mx-auto animate-fade-in">
        <div className="mb-8">
          <h2 className="font-display text-2xl font-semibold text-foreground">
            {subsection.name}
          </h2>
          {subsection.description && (
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {subsection.description}
            </p>
          )}
        </div>
        <div className="border border-dashed border-border rounded-xl p-16 text-center">
          <FileText className="h-8 w-8 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground mb-5">
            No screenplay content yet. Start writing your screenplay below — scenes
            split automatically on INT./EXT. headings — or generate one with the
            Script Writer Wizard.
          </p>
          <button
            onClick={startEditing}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-amber-500 text-amber-950 rounded-lg hover:bg-amber-400 transition-colors"
          >
            <Pencil className="h-4 w-4" /> Start writing
          </button>
        </div>
      </div>
    );
  }

  // =========== MAIN EDITOR ===========
  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* ── Sticky toolbar ── */}
      <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-2.5 bg-card/95 backdrop-blur-sm border-b border-border/60">
        <div className="flex items-center gap-4">
          <h2 className="font-display text-lg font-semibold text-foreground">
            {subsection.name}
          </h2>
          <span className="text-[11px] font-mono text-amber-500/70 bg-amber-500/5 border border-amber-500/10 px-2.5 py-0.5 rounded-full">
            Page {currentPage} / {totalPages}
          </span>
          <span className="text-[11px] text-muted-foreground">
            {screenplays.length} {screenplays.length === 1 ? 'scene' : 'scenes'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleDiscard}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted/40"
              >
                <X className="h-3.5 w-3.5" /> Discard
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || saveMutation.isPending}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-amber-500 text-amber-950 rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-40"
              >
                <Check className="h-3.5 w-3.5" />
                {saveMutation.isPending ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              {VAPAI_ENABLED && (
                <button
                  onClick={() => sendToVapaiMutation.mutate(undefined)}
                  disabled={screenplays.length === 0 || sendToVapaiMutation.isPending || sendSeriesMutation.isPending}
                  title="Enviar este guión a vapai-studio para producción"
                  className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-foreground/80 bg-muted/40 border border-border/40 rounded-lg hover:bg-muted/70 hover:text-foreground transition-colors disabled:opacity-40"
                >
                  <Send className="h-3.5 w-3.5" />
                  {sendToVapaiMutation.isPending ? 'Enviando…' : 'Enviar a vapai-studio'}
                </button>
              )}
              <button
                onClick={startEditing}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-foreground/80 bg-muted/40 border border-border/40 rounded-lg hover:bg-muted/70 hover:text-foreground transition-colors"
              >
                <Pencil className="h-3.5 w-3.5" /> Edit
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── vapai-studio send feedback (inline; app has no toast) ── */}
      {/* Series episode: ask whether to send just this episode into the series or
          the whole series. Shown when the backend returned a 409 (isSeriesEpisode). */}
      {seriesChoice && !sendToVapaiMutation.isPending && !sendSeriesMutation.isPending && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 px-6 py-2 text-xs bg-amber-500/10 border-b border-amber-500/20 text-amber-200"
        >
          <span>Este episodio es parte de una serie. ¿Qué querés enviar?</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => sendToVapaiMutation.mutate('series')}
              className="px-3 py-1 font-medium rounded-md bg-amber-500/20 hover:bg-amber-500/30 transition-colors"
            >
              Solo este episodio
            </button>
            <button
              onClick={() => sendSeriesMutation.mutate(seriesChoice.showId)}
              className="px-3 py-1 font-medium rounded-md bg-amber-500/20 hover:bg-amber-500/30 transition-colors"
            >
              Toda la serie
            </button>
            <button
              onClick={() => setSeriesChoice(null)}
              className="px-2 py-1 text-amber-200/60 hover:text-amber-200 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
      {sendToVapaiMutation.isSuccess && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 px-6 py-2 text-xs bg-emerald-500/10 border-b border-emerald-500/20 text-emerald-300"
        >
          <span>Guión enviado a vapai-studio.</span>
          {sendToVapaiMutation.data.deep_link && (
            <a
              href={sendToVapaiMutation.data.deep_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-medium underline hover:no-underline"
            >
              Abrir en vapai <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}
      {sendSeriesMutation.isSuccess && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 px-6 py-2 text-xs bg-emerald-500/10 border-b border-emerald-500/20 text-emerald-300"
        >
          <span>Serie enviada a vapai-studio.</span>
          {sendSeriesMutation.data?.deep_link && (
            <a
              href={sendSeriesMutation.data.deep_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-medium underline hover:no-underline"
            >
              Abrir en vapai <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}
      {/* Suppress the raw error banner for the 409 series-choice case (that's the
          amber panel above, not a failure). */}
      {sendToVapaiMutation.isError && !seriesChoice && (
        <div
          role="alert"
          className="px-6 py-2 text-xs bg-red-500/10 border-b border-red-500/20 text-red-300"
        >
          No se pudo enviar a vapai-studio: {sendToVapaiMutation.error.message}
        </div>
      )}
      {sendSeriesMutation.isError && (
        <div
          role="alert"
          className="px-6 py-2 text-xs bg-red-500/10 border-b border-red-500/20 text-red-300"
        >
          No se pudo enviar la serie a vapai-studio: {(sendSeriesMutation.error as Error).message}
        </div>
      )}

      {/* ── Content ── */}
      {isEditing ? (
        /* ─── Edit mode: full-document textarea ─── */
        <div className="flex-1 overflow-auto bg-background">
          <div className="max-w-[680px] mx-auto py-8 px-4">
            <div className="relative">
              <textarea
                ref={editRef}
                value={editText}
                onChange={(e) => {
                  setEditText(e.target.value);
                  setHasChanges(true);
                }}
                onScroll={handleEditScroll}
                placeholder={'INT. LOCATION - DAY\n\nAction…'}
                spellCheck={false}
                className="w-full bg-[hsl(240,5%,8.5%)] border border-border/30 rounded-sm shadow-2xl font-screenplay text-[13px] text-foreground/90 focus:outline-none focus:ring-1 focus:ring-amber-500/15 focus:border-amber-500/20 resize-none"
                style={{
                  padding: '72px 80px',
                  lineHeight: `${LINE_HEIGHT_PX}px`,
                  minHeight: `${Math.max(pages.length * LINES_PER_PAGE * LINE_HEIGHT_PX + 144, 880)}px`,
                  tabSize: 4,
                }}
              />
            </div>
          </div>
        </div>
      ) : (
        /* ─── View mode: stacked paper pages ─── */
        <div className="flex-1 overflow-auto bg-background">
          <div className="max-w-[680px] mx-auto py-8 px-4 space-y-6">
            {/* ── Per-scene "Regenerate & Compare" rail (one per scene) ── */}
            {screenplays.length > 0 && (
              <div className="rounded-lg border border-border/40 bg-card/40 divide-y divide-border/30">
                {screenplays.map((sp, i) => (
                  <div
                    key={sp.episode_index ?? i}
                    className="flex items-center justify-between gap-3 px-4 py-2.5 group"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="shrink-0 text-[11px] font-mono text-muted-foreground/40">
                        {i + 1}.
                      </span>
                      <span className="truncate text-xs font-medium text-foreground/80">
                        {sp.title || 'Untitled scene'}
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setCompareIndex(i);
                      }}
                      className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-foreground/80 bg-muted/40 border border-border/40 rounded-lg hover:bg-muted/70 hover:text-foreground transition-colors"
                      aria-label="Regenerate & compare this scene"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                      <span className="hidden sm:inline">Regenerate &amp; Compare</span>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {pages.map((pageText, i) => (
              <div
                key={i}
                ref={(el) => {
                  if (el) pageEls.current.set(i, el);
                  else pageEls.current.delete(i);
                }}
                data-page={i + 1}
                className="relative bg-[hsl(240,5%,8.5%)] border border-border/30 rounded-sm shadow-2xl cursor-pointer group"
                style={{ padding: '72px 80px', minHeight: '880px' }}
                onClick={startEditing}
              >
                {/* Page number */}
                <span className="absolute top-5 right-7 text-[11px] font-mono text-muted-foreground/25 group-hover:text-muted-foreground/40 transition-colors">
                  {i + 1}.
                </span>

                {/* Hover hint */}
                <span className="absolute top-5 left-7 text-[10px] text-muted-foreground/0 group-hover:text-muted-foreground/30 transition-colors flex items-center gap-1">
                  <Pencil className="h-2.5 w-2.5" /> Click to edit
                </span>

                {/* Screenplay text */}
                <pre className="font-screenplay text-[13px] text-foreground/90 whitespace-pre-wrap break-words" style={{ lineHeight: `${LINE_HEIGHT_PX}px` }}>
                  {pageText}
                </pre>
              </div>
            ))}

            {/* End mark */}
            <div className="text-center py-8">
              <span className="text-xs font-mono text-muted-foreground/20 tracking-widest">
                — END —
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Per-scene compare modal (mounted once; regenerates on open) ── */}
      <SceneCompareModal
        open={compareIndex !== null}
        onOpenChange={(o) => {
          if (!o) setCompareIndex(null);
        }}
        projectId={projectId}
        phase={phase}
        subsectionKey={subsection.key}
        episodeIndex={compareIndex ?? 0}
        currentTitle={screenplays[compareIndex ?? 0]?.title ?? ''}
        currentContent={screenplays[compareIndex ?? 0]?.content ?? ''}
      />
    </div>
  );
}
