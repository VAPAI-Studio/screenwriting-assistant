import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Wand2, Loader2, Lock } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import { QUERY_KEYS } from '../../lib/constants';
import type { SeasonMapResult } from '../../types';

interface SeasonMapWizardModalProps {
  seasonId: string;
  showId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultPremise: string;
  existingSlotCount: number;
  lockedSlotCount: number;
}

const FIELD_CLS =
  'w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 transition-all';
const LABEL_CLS = 'block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2';

export function SeasonMapWizardModal({
  seasonId, showId, open, onOpenChange, defaultPremise, existingSlotCount, lockedSlotCount,
}: SeasonMapWizardModalProps) {
  const queryClient = useQueryClient();
  const [episodeCount, setEpisodeCount] = useState(existingSlotCount || 8);
  const [premise, setPremise] = useState(defaultPremise);
  const [guidance, setGuidance] = useState('');
  const [runId, setRunId] = useState<string | null>(null);

  const runMutation = useMutation({
    mutationFn: () =>
      api.runSeasonMapWizard(seasonId, {
        episode_count: episodeCount,
        premise,
        custom_guidance: guidance,
      }),
    onSuccess: (run) => setRunId(run.id),
  });

  // Poll the run while it's pending/running (same lifecycle as project wizards).
  const { data: run } = useQuery({
    queryKey: ['season-map-run', runId],
    queryFn: () => api.getWizardRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'completed' || status === 'failed' ? false : 2500;
    },
  });

  const applyMutation = useMutation({
    mutationFn: () => api.applyWizardResults(runId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASON(seasonId) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEASONS(showId) });
      handleClose(false);
    },
  });

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      setRunId(null);
      runMutation.reset();
      applyMutation.reset();
    }
    onOpenChange(nextOpen);
  };

  const generating = !!runId && (!run || run.status === 'pending' || run.status === 'running');
  const failed = run?.status === 'failed';
  const result = run?.status === 'completed' ? (run.result as SeasonMapResult) : null;

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[640px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-y-auto">
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-indigo-400" />
              Season map wizard
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="px-6 pb-6">
            {/* Step 1: setup form */}
            {!runId && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  runMutation.mutate();
                }}
                className="space-y-4"
              >
                {lockedSlotCount > 0 && (
                  <p className="flex items-center gap-1.5 text-xs text-muted-foreground px-3 py-2 rounded-lg bg-muted/20 border border-border/40">
                    <Lock className="h-3.5 w-3.5 flex-shrink-0" />
                    {lockedSlotCount} slot{lockedSlotCount !== 1 ? 's' : ''} with an existing episode will be kept as-is; the map is planned around them.
                  </p>
                )}
                <div>
                  <label className={LABEL_CLS}>Episodes in the season</label>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={episodeCount}
                    onChange={(e) => setEpisodeCount(Math.max(1, Number(e.target.value) || 1))}
                    className={`${FIELD_CLS} max-w-[120px]`}
                  />
                </div>
                <div>
                  <label className={LABEL_CLS}>Season premise / arc direction</label>
                  <textarea
                    value={premise}
                    onChange={(e) => setPremise(e.target.value)}
                    rows={4}
                    className={FIELD_CLS}
                    placeholder="Where the season starts, what it's about, where it should land"
                  />
                </div>
                <div>
                  <label className={LABEL_CLS}>Custom guidance (optional)</label>
                  <textarea
                    value={guidance}
                    onChange={(e) => setGuidance(e.target.value)}
                    rows={2}
                    className={FIELD_CLS}
                    placeholder="Constraints, must-have episodes, B-plots…"
                  />
                </div>
                {runMutation.isError && (
                  <p className="text-sm text-red-300">{(runMutation.error as Error).message}</p>
                )}
                <div className="flex justify-end gap-2.5 pt-2">
                  <Button type="button" variant="ghost" onClick={() => handleClose(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={runMutation.isPending}>
                    {runMutation.isPending ? 'Starting…' : 'Generate map'}
                  </Button>
                </div>
              </form>
            )}

            {/* Step 2: generating */}
            {generating && (
              <div className="flex flex-col items-center justify-center py-14 gap-3">
                <Loader2 className="h-7 w-7 animate-spin text-indigo-400" />
                <p className="text-sm text-muted-foreground">Mapping the season…</p>
              </div>
            )}

            {/* Failed */}
            {failed && (
              <div className="space-y-4">
                <p className="text-sm text-red-300">
                  Generation failed: {run?.error_message || 'unknown error'}
                </p>
                <div className="flex justify-end">
                  <Button variant="ghost" onClick={() => setRunId(null)}>Back</Button>
                </div>
              </div>
            )}

            {/* Step 3: preview + apply */}
            {result && (
              <div className="space-y-4">
                {((result as any).doctrine_used?.length ?? 0) > 0 && (
                  <p className="text-[11px] text-muted-foreground">
                    <span className="text-amber-400/80">📚 Doctrina aplicada:</span>{' '}
                    {((result as any).doctrine_used as { name: string; source: string }[])
                      .map((d) => `${d.name} (${d.source})`).join(' · ')}
                  </p>
                )}
                {result.arc_summary.trim() && (
                  <div className="px-4 py-3 text-sm rounded-lg bg-muted/20 border border-border/40 text-muted-foreground">
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground/70 block mb-1">
                      Season arc
                    </span>
                    {result.arc_summary}
                  </div>
                )}
                <div className="space-y-2 max-h-[40vh] overflow-y-auto pr-1">
                  {result.slots.map((slot) => (
                    <div key={slot.slot_number} className="rounded-lg border border-border bg-card/60 px-4 py-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="w-6 h-6 rounded bg-muted/50 text-[11px] font-semibold text-muted-foreground flex items-center justify-center flex-shrink-0">
                          {slot.slot_number}
                        </span>
                        <span className="text-sm font-medium text-foreground">{slot.title || 'Untitled'}</span>
                        {slot.arc_function.trim() && (
                          <span className="ml-auto px-2 py-0.5 text-[10px] rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20 flex-shrink-0">
                            {slot.arc_function}
                          </span>
                        )}
                      </div>
                      {slot.logline.trim() && <p className="text-xs text-muted-foreground">{slot.logline}</p>}
                      {slot.cliffhanger.trim() && (
                        <p className="text-[11px] text-muted-foreground/80 mt-1">
                          <span className="font-medium text-muted-foreground">Out:</span> {slot.cliffhanger}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
                {applyMutation.isError && (
                  <p className="text-sm text-red-300">{(applyMutation.error as Error).message}</p>
                )}
                <div className="flex justify-end gap-2.5">
                  <Button variant="ghost" onClick={() => setRunId(null)}>
                    Regenerate
                  </Button>
                  <Button onClick={() => applyMutation.mutate()} disabled={applyMutation.isPending}>
                    {applyMutation.isPending ? 'Applying…' : 'Apply to season map'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
