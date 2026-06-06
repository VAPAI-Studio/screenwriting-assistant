import { useState, useEffect, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Loader2, Sparkles, Check } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import { Button } from '../UI/Button';
import type { RegenerateSceneResponse } from '../../types';

interface SceneCompareModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  phase: string;
  subsectionKey: string;
  episodeIndex: number;
  currentTitle: string;
  currentContent: string;
}

/** Shared screenplay paper renderer — identical to ScreenplayEditorView view mode,
 *  minus pagination, with the UI-SPEC narrower-pane padding (40px 48px). Applied
 *  identically to BOTH panes so old-vs-new is judged on content, not formatting. */
function ScreenplayPane({
  label,
  ariaLabel,
  badgeClassName,
  children,
  dimmed,
}: {
  label: string;
  ariaLabel: string;
  badgeClassName: string;
  children: React.ReactNode;
  dimmed?: boolean;
}) {
  return (
    <section
      aria-label={ariaLabel}
      className={`flex flex-col min-h-0 transition-opacity ${dimmed ? 'opacity-60' : ''}`}
    >
      <div className="mb-2 flex items-center">
        <span
          className={`text-[11px] font-medium uppercase tracking-wider px-2 py-0.5 rounded ${badgeClassName}`}
        >
          {label}
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-auto bg-background rounded-sm">
        <div
          className="bg-[hsl(240,5%,8.5%)] border border-border/30 rounded-sm shadow-2xl"
          style={{ padding: '40px 48px' }}
        >
          {children}
        </div>
      </div>
    </section>
  );
}

function ScreenplayText({ text }: { text: string }) {
  return (
    <pre
      className="font-screenplay text-[13px] text-foreground/90 whitespace-pre-wrap break-words"
      style={{ lineHeight: '20px' }}
    >
      {text}
    </pre>
  );
}

export function SceneCompareModal({
  open,
  onOpenChange,
  projectId,
  phase,
  subsectionKey,
  episodeIndex,
  currentTitle,
  currentContent,
}: SceneCompareModalProps) {
  const queryClient = useQueryClient();

  // Freshly generated scene retained in component state so a keep-new retry after
  // a persist failure does NOT re-regenerate (UI-SPEC keep-new error state).
  const [generated, setGenerated] = useState<RegenerateSceneResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [keepError, setKeepError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  const regenerateMutation = useMutation({
    mutationFn: () =>
      api.regenerateScene({ project_id: projectId, phase, episode_index: episodeIndex }),
    onSuccess: (result) => {
      // The backend may return a soft error payload ({error}) instead of throwing.
      if (result.error) {
        setGenError(result.error);
        setGenerated(null);
      } else {
        setGenerated(result);
        setGenError(null);
      }
    },
    onError: (err: any) => {
      setGenError(err?.message || 'Regeneration failed.');
      setGenerated(null);
    },
  });

  const runRegenerate = useCallback(() => {
    setGenerated(null);
    setGenError(null);
    setKeepError(null);
    regenerateMutation.mutate();
    // regenerateMutation identity is stable; intentionally excluded to avoid re-fire loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, phase, episodeIndex]);

  // Kick off regeneration when the modal opens; reset transient state when it closes.
  useEffect(() => {
    if (open) {
      runRegenerate();
    } else {
      setGenerated(null);
      setGenError(null);
      setKeepError(null);
      setSavedFlash(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const keepMutation = useMutation({
    mutationFn: () =>
      api.keepSceneVersion({
        project_id: projectId,
        phase,
        episode_index: episodeIndex,
        title: generated?.title ?? '',
        content: generated?.content ?? '',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsectionKey),
      });
      setKeepError(null);
      setSavedFlash(true);
      // Brief amber check before close (permitted, UI-SPEC).
      setTimeout(() => onOpenChange(false), 600);
    },
    onError: () => {
      setKeepError(
        "Couldn't save the new version. Your stored scene is unchanged — try again.",
      );
    },
  });

  const isGenerating = regenerateMutation.isPending;
  const isPersisting = keepMutation.isPending;
  const hasResult = generated !== null && !genError;

  const sceneNumber = episodeIndex + 1;

  // Close is disabled only while persisting (prevents closing mid-write); allowed
  // during generating (cancels the regenerate via component unmount/abort timeout).
  const closeDisabled = isPersisting;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (closeDisabled) return;
        onOpenChange(o);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in z-40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[92vw] max-w-[1100px] h-[88vh] flex flex-col rounded-xl bg-card border border-border shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-hidden z-50"
          onEscapeKeyDown={(e) => {
            if (isPersisting) e.preventDefault();
          }}
          onInteractOutside={(e) => {
            if (closeDisabled) e.preventDefault();
          }}
        >
          {/* ── Header band ── */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border/60 bg-card/95">
            <div className="flex items-center gap-3 min-w-0">
              <Dialog.Title className="font-display text-xl font-semibold text-foreground truncate">
                Compare scene {sceneNumber}: {currentTitle || 'Untitled'}
              </Dialog.Title>
              <span className="shrink-0 text-[11px] font-mono text-amber-500/70 bg-amber-500/5 border border-amber-500/10 px-2.5 py-0.5 rounded-full">
                Scene {sceneNumber}
              </span>
            </div>
            <Dialog.Description className="sr-only">
              Compare the stored scene with a regenerated version and choose which to keep.
            </Dialog.Description>
            <Dialog.Close asChild>
              <button
                className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40 disabled:pointer-events-none"
                aria-label="Close"
                disabled={closeDisabled}
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* ── Body: two-column compare ── */}
          <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-8 px-6 py-4 overflow-hidden">
            {/* LEFT — CURRENT */}
            <ScreenplayPane
              label="Current"
              ariaLabel="Current stored version"
              badgeClassName="text-muted-foreground bg-muted/40"
              dimmed={isPersisting}
            >
              {currentContent ? (
                <ScreenplayText text={currentContent} />
              ) : (
                <p className="font-screenplay text-[13px] text-muted-foreground/60 italic">
                  No stored text for this scene yet.
                </p>
              )}
            </ScreenplayPane>

            {/* RIGHT — NEW */}
            <ScreenplayPane
              label="New"
              ariaLabel="Regenerated version"
              badgeClassName="text-amber-400 bg-amber-500/10 border border-amber-500/20"
              dimmed={isPersisting}
            >
              {isGenerating ? (
                <div
                  className="flex flex-col items-center justify-center text-center py-16"
                  aria-live="polite"
                >
                  <Loader2 className="h-8 w-8 text-amber-400 animate-spin mb-4" />
                  <p className="font-display text-base font-semibold text-foreground">
                    Regenerating scene…
                  </p>
                  <p className="mt-2 max-w-sm text-xs text-muted-foreground leading-relaxed">
                    Rewriting with the improved continuity, voice, and craft passes. This
                    can take up to a minute.
                  </p>
                </div>
              ) : genError ? (
                <div className="py-12 text-center" aria-live="polite">
                  <p className="text-sm font-semibold text-destructive">
                    Regeneration failed. Your current version is untouched.
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground break-words line-clamp-3">
                    {genError}
                  </p>
                  <div className="mt-5 flex items-center justify-center gap-2.5">
                    <Button
                      variant="default"
                      size="sm"
                      onClick={runRegenerate}
                      disabled={isGenerating}
                    >
                      <Sparkles className="h-3.5 w-3.5 mr-1.5" /> Try again
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <ScreenplayText text={generated?.content ?? ''} />
              )}
            </ScreenplayPane>
          </div>

          {/* ── Footer band ── */}
          <div className="flex items-center justify-end gap-2.5 px-6 py-4 border-t border-border/60 bg-card/95">
            {keepError && (
              <span className="mr-auto text-xs text-destructive">{keepError}</span>
            )}
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPersisting}
            >
              Keep current
            </Button>
            <Button
              variant="default"
              onClick={() => {
                setKeepError(null);
                keepMutation.mutate();
              }}
              disabled={isGenerating || !hasResult || isPersisting}
              title="Replaces the stored scene and flags the breakdown and shotlist as out of date."
            >
              {savedFlash ? (
                <>
                  <Check className="h-4 w-4 mr-1.5 text-amber-200" /> Saved
                </>
              ) : isPersisting ? (
                'Saving…'
              ) : (
                'Keep new version'
              )}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
