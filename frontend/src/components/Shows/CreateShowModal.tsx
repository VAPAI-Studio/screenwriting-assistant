import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Zap, Link, LayoutGrid, type LucideIcon } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import { QUERY_KEYS, ROUTES, SHOW_PRESETS } from '../../lib/constants';
import type { Show } from '../../types';

const PRESET_ICON_MAP: Record<string, LucideIcon> = {
  Zap,
  Link,
  LayoutGrid,
};

// Raised when the show was created but the chained bible seed failed (CR-01).
// Lets onError distinguish "nothing created" from "created, defaults not seeded".
class BibleSeedError extends Error {
  // `cause` would be the standard slot, but the project targets ES2020 (no
  // Error.cause); expose the underlying error under a distinct name instead.
  constructor(public readonly show: Show, public readonly seedError: unknown) {
    super('Show created, but applying the preset defaults failed.');
    this.name = 'BibleSeedError';
  }
}

interface CreateShowModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateShowModal({ open, onOpenChange }: CreateShowModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [seasonArc, setSeasonArc] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const selectedPresetObj = SHOW_PRESETS.find((p) => p.id === selectedPreset);
  const isConnected = selectedPresetObj?.mode === 'connected';

  const createShowMutation = useMutation({
    mutationFn: async (): Promise<Show> => {
      const preset = selectedPresetObj;
      const show = await api.createShow({
        title,
        description: description || undefined,
        continuity_mode: preset?.mode,
      });

      // Two-call sequence (PATTERNS Integration Finding #2): episode_duration_minutes
      // and bible_season_arc are Bible fields, not ShowCreate fields — seed them via a
      // single chained updateBible after the show (and its auto-provisioned bible) exist.
      const bibleUpdate: { episode_duration_minutes?: number | null; bible_season_arc?: string } = {};
      if (preset && preset.duration !== null) {
        bibleUpdate.episode_duration_minutes = preset.duration;
      }
      if (preset?.mode === 'connected' && seasonArc.trim()) {
        bibleUpdate.bible_season_arc = seasonArc.trim();
      }
      if (Object.keys(bibleUpdate).length > 0) {
        // If the bible seed fails after the show was created, surface it as an error
        // (CR-01) — the show exists but its preset defaults were not persisted. The
        // navigate target carries the show id so the user can finish setup there.
        try {
          await api.updateBible(show.id, bibleUpdate);
        } catch (err) {
          throw new BibleSeedError(show, err);
        }
      }

      return show;
    },
    onSuccess: (show) => {
      finishAndGoToShow(show.id);
    },
    onError: (err) => {
      // The show was created but the bible seed failed (CR-01). Don't strand the user
      // in the modal (NEW-02): refresh the list and navigate so they can finish setup
      // on the show page. A non-BibleSeedError means nothing was created — keep the
      // modal open and let the inline error copy explain.
      if (err instanceof BibleSeedError) {
        finishAndGoToShow(err.show.id);
      }
    },
  });

  // Reset local state BEFORE closing — onOpenChange(false) unmounts this dialog,
  // so setState after it would warn on an unmounted component (CR-02).
  const finishAndGoToShow = (showId: string) => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SHOWS] });
    setTitle('');
    setDescription('');
    setSelectedPreset(null);
    setSeasonArc('');
    onOpenChange(false);
    navigate(ROUTES.SHOW(showId));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createShowMutation.mutate();
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border p-0 shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground">
              New Show
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-5">
            {/* Title */}
            <div>
              <label htmlFor="show-title" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Title
              </label>
              <input
                id="show-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all"
                placeholder="My TV Show"
                required
                autoFocus
              />
            </div>

            {/* Continuity */}
            <div>
              <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                Continuity
              </label>
              <div className="space-y-2.5">
                {SHOW_PRESETS.map((preset) => {
                  const isSelected = selectedPreset === preset.id;
                  const Icon = PRESET_ICON_MAP[preset.icon] || LayoutGrid;

                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => setSelectedPreset(preset.id)}
                      className={`w-full text-left flex items-center gap-4 p-4 rounded-xl border transition-all duration-200
                        ${isSelected
                          ? 'border-amber-500/40 bg-amber-500/5 glow-amber'
                          : 'border-border hover:border-muted-foreground/20 hover:bg-muted/30'
                        }`}
                    >
                      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors
                        ${isSelected ? 'bg-amber-500/15 text-amber-400' : 'bg-muted text-muted-foreground'}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-foreground">{preset.label}</div>
                        <p className="text-xs text-muted-foreground mt-0.5">{preset.helper}</p>
                      </div>
                      {isSelected && (
                        <div className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Description */}
            <div>
              <label htmlFor="show-description" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Description
              </label>
              <textarea
                id="show-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all resize-none"
                placeholder="What's this show about?"
                rows={3}
              />
            </div>

            {/* Season Arc — connected presets only (D-07) */}
            {isConnected && (
              <div className="animate-fade-up">
                <label htmlFor="show-season-arc" className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Season Arc
                </label>
                <textarea
                  id="show-season-arc"
                  value={seasonArc}
                  onChange={(e) => setSeasonArc(e.target.value)}
                  className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all resize-none"
                  placeholder="Outline the overarching story arc for the season..."
                  rows={3}
                />
              </div>
            )}

            {/* Error copy (CR-01 / WR-01) */}
            {createShowMutation.isError && (
              <p className="text-xs text-red-400" role="alert">
                {createShowMutation.error instanceof BibleSeedError
                  ? 'Show created, but applying the preset defaults failed. Open the show to finish setting it up.'
                  : 'Could not create the show. Check your connection and try again.'}
              </p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2.5 pt-2">
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!title || !selectedPreset || createShowMutation.isPending}
              >
                {createShowMutation.isPending ? 'Creating...' : 'Create Show'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
