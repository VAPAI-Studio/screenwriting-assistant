import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Map as MapIcon, Wand2, Pencil, Trash2, Film, ExternalLink, RefreshCw, AlertTriangle,
} from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, ROUTES } from '../../lib/constants';
import type { EpisodeSlot } from '../../types';
import { Button } from '../UI/Button';
import { SlotEditModal } from './SlotEditModal';
import { SeasonMapWizardModal } from './SeasonMapWizardModal';
import { ReconcileSlotModal } from './ReconcileSlotModal';

interface SeasonMapProps {
  showId: string;
  /** Prefill for the wizard premise when the season has no arc yet. */
  bibleSeasonArc: string;
}

/** Slot lifecycle badge: in progress > planned > empty. */
function slotStatus(slot: EpisodeSlot) {
  if (slot.project_id) {
    return { label: 'In progress', cls: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20' };
  }
  const planned = slot.logline.trim() || slot.arc_function.trim() || slot.cliffhanger.trim();
  return planned
    ? { label: 'Planned', cls: 'bg-amber-500/10 text-amber-300 border-amber-500/20' }
    : { label: 'Empty', cls: 'bg-muted/40 text-muted-foreground border-border/40' };
}

export function SeasonMap({ showId, bibleSeasonArc }: SeasonMapProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedSeasonId, setSelectedSeasonId] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState<EpisodeSlot | null>(null);
  const [reconcilingSlot, setReconcilingSlot] = useState<EpisodeSlot | null>(null);

  const { data: seasons = [], isLoading: seasonsLoading } = useQuery({
    queryKey: QUERY_KEYS.SEASONS(showId),
    queryFn: () => api.getSeasons(showId),
  });

  const activeSeasonId = selectedSeasonId ?? seasons[0]?.id ?? null;

  const { data: season, isLoading: seasonLoading } = useQuery({
    queryKey: QUERY_KEYS.SEASON(activeSeasonId ?? ''),
    queryFn: () => api.getSeason(activeSeasonId!),
    enabled: !!activeSeasonId,
  });

  // Episodes power the per-slot status badge and the open-episode action.
  const { data: episodes = [] } = useQuery({
    queryKey: QUERY_KEYS.EPISODES(showId),
    queryFn: () => api.getEpisodes(showId),
  });
  const episodesById = new Map(episodes.map((e) => [e.id, e]));

  const invalidateSeason = () => {
    if (activeSeasonId) queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASON(activeSeasonId) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASONS(showId) });
  };

  const createSeasonMutation = useMutation({
    mutationFn: () => api.createSeason(showId),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASONS(showId) });
      setSelectedSeasonId(created.id);
    },
  });

  const addSlotMutation = useMutation({
    mutationFn: () => api.createSlot(activeSeasonId!),
    onSuccess: invalidateSeason,
  });

  const deleteSlotMutation = useMutation({
    mutationFn: (slotId: string) => api.deleteSlot(slotId),
    onSuccess: invalidateSeason,
  });

  const deleteSeasonMutation = useMutation({
    mutationFn: (seasonId: string) => api.deleteSeason(seasonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASONS(showId) });
      setSelectedSeasonId(null); // fall back to the first remaining season
    },
  });

  const createEpisodeMutation = useMutation({
    mutationFn: (slotId: string) => api.createEpisodeFromSlot(slotId),
    onSuccess: () => {
      invalidateSeason();
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
    },
  });

  if (seasonsLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (seasons.length === 0) {
    return (
      <div className="text-center py-10 border border-dashed border-border rounded-xl">
        <MapIcon className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground mb-4">
          No seasons yet — create one to plan the episode map
        </p>
        <Button size="sm" onClick={() => createSeasonMutation.mutate()} disabled={createSeasonMutation.isPending}>
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          {createSeasonMutation.isPending ? 'Creating…' : 'Create Season 1'}
        </Button>
      </div>
    );
  }

  const slots = season?.slots ?? [];

  return (
    <>
      {/* Season selector + actions */}
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          {seasons.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedSeasonId(s.id)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                s.id === activeSeasonId
                  ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300'
                  : 'border-border text-muted-foreground hover:text-foreground hover:bg-muted/30'
              }`}
            >
              S{s.number}
            </button>
          ))}
          <button
            onClick={() => createSeasonMutation.mutate()}
            disabled={createSeasonMutation.isPending}
            title="Add season"
            className="px-2 py-1.5 rounded-lg border border-dashed border-border text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (!activeSeasonId || !season) return;
              if (window.confirm(`Delete Season ${season.number}? Its planned slots are removed; already-created episodes are kept (they just lose the season link). This cannot be undone.`)) {
                deleteSeasonMutation.mutate(activeSeasonId);
              }
            }}
            disabled={!activeSeasonId || deleteSeasonMutation.isPending}
            title="Delete this season (episodes are kept)"
            className="p-1.5 rounded-lg text-muted-foreground/40 hover:text-red-300 hover:bg-red-500/10 transition-colors disabled:opacity-40"
          >
            <Trash2 className="h-4 w-4" />
          </button>
          <Button size="sm" variant="ghost" onClick={() => addSlotMutation.mutate()} disabled={!activeSeasonId || addSlotMutation.isPending}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Add slot
          </Button>
          <Button size="sm" onClick={() => setWizardOpen(true)} disabled={!activeSeasonId}>
            <Wand2 className="h-3.5 w-3.5 mr-1.5" />
            {slots.length > 0 ? 'Regenerate map' : 'Generate season map'}
          </Button>
        </div>
      </div>

      {/* Season arc */}
      {season && season.arc_summary.trim() && (
        <div className="mb-4 px-4 py-3 text-sm rounded-lg bg-muted/20 border border-border/40 text-muted-foreground">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground/70 block mb-1">
            Season arc
          </span>
          {season.arc_summary}
        </div>
      )}

      {/* Slots grid */}
      {seasonLoading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : slots.length === 0 ? (
        <div className="text-center py-10 border border-dashed border-border rounded-xl">
          <MapIcon className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            Empty map — generate the season map or add slots by hand
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {slots.map((slot) => {
            const episode = slot.project_id ? episodesById.get(slot.project_id) : undefined;
            const status = slotStatus(slot);
            return (
              <div
                key={slot.id}
                className="flex flex-col rounded-xl border border-border bg-card/60 p-4 gap-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-muted/50 text-xs font-semibold text-muted-foreground flex items-center justify-center">
                      {slot.slot_number}
                    </span>
                    <h3 className="text-sm font-medium text-foreground truncate">
                      {slot.title.trim() || episode?.title || 'Untitled'}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {slot.plan_stale && (
                      <span
                        title="The written episode may have diverged from this plan"
                        className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded border bg-orange-500/10 text-orange-300 border-orange-500/20"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        Plan stale
                      </span>
                    )}
                    <span className={`px-1.5 py-0.5 text-[10px] rounded border ${status.cls}`}>
                      {status.label}
                    </span>
                  </div>
                </div>

                {slot.logline.trim() && (
                  <p className="text-xs text-muted-foreground line-clamp-3">{slot.logline}</p>
                )}
                {slot.arc_function.trim() && (
                  <span className="self-start px-2 py-0.5 text-[10px] rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    {slot.arc_function}
                  </span>
                )}
                {slot.cliffhanger.trim() && (
                  <p className="text-[11px] text-muted-foreground/80">
                    <span className="font-medium text-muted-foreground">Out:</span> {slot.cliffhanger}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center gap-1 mt-auto pt-2 border-t border-border/40">
                  <button
                    onClick={() => setEditingSlot(slot)}
                    title="Edit plan"
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {slot.plan_stale && slot.project_id && (
                    <button
                      onClick={() => setReconcilingSlot(slot)}
                      title="Reconcile plan with the written episode"
                      className="p-1.5 rounded-lg text-orange-300 hover:text-orange-200 hover:bg-orange-500/10 transition-colors"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {!slot.project_id && (
                    <button
                      onClick={() => {
                        if (window.confirm('Delete this slot?')) deleteSlotMutation.mutate(slot.id);
                      }}
                      title="Delete slot"
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <div className="flex-1" />
                  {slot.project_id ? (
                    <button
                      onClick={() => navigate(ROUTES.PROJECT(slot.project_id!))}
                      className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg text-indigo-300 hover:text-indigo-200 hover:bg-indigo-500/10 transition-colors"
                    >
                      Open episode <ExternalLink className="h-3 w-3" />
                    </button>
                  ) : (
                    <button
                      onClick={() => createEpisodeMutation.mutate(slot.id)}
                      disabled={createEpisodeMutation.isPending}
                      className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg text-emerald-300 hover:text-emerald-200 hover:bg-emerald-500/10 transition-colors disabled:opacity-40"
                    >
                      <Film className="h-3 w-3" /> Create episode
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      {activeSeasonId && season && (
        <SeasonMapWizardModal
          seasonId={activeSeasonId}
          showId={showId}
          open={wizardOpen}
          onOpenChange={setWizardOpen}
          defaultPremise={season.arc_summary.trim() || bibleSeasonArc}
          existingSlotCount={slots.length}
          lockedSlotCount={slots.filter((s) => s.project_id).length}
        />
      )}
      {editingSlot && (
        <SlotEditModal
          slot={editingSlot}
          open={!!editingSlot}
          onOpenChange={(open) => !open && setEditingSlot(null)}
          onSaved={invalidateSeason}
        />
      )}
      {reconcilingSlot && (
        <ReconcileSlotModal
          slot={reconcilingSlot}
          open={!!reconcilingSlot}
          onOpenChange={(open) => !open && setReconcilingSlot(null)}
          onApplied={invalidateSeason}
        />
      )}
    </>
  );
}
