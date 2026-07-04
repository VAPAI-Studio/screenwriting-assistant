import { useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X, RefreshCw, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import { statesToLines } from './SlotEditModal';
import type { EpisodeSlot } from '../../types';

interface ReconcileSlotModalProps {
  slot: EpisodeSlot;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApplied: () => void;
}

function PlanColumn({ heading, plan }: {
  heading: string;
  plan: { title: string; logline: string; arc_function: string; character_states: Record<string, string>; cliffhanger: string };
}) {
  return (
    <div className="flex-1 min-w-0 rounded-lg border border-border bg-card/60 p-3 space-y-2">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground/70">{heading}</p>
      <p className="text-sm font-medium text-foreground">{plan.title.trim() || 'Untitled'}</p>
      {plan.logline.trim() && <p className="text-xs text-muted-foreground">{plan.logline}</p>}
      {plan.arc_function.trim() && (
        <p className="text-[11px] text-purple-300">{plan.arc_function}</p>
      )}
      {Object.keys(plan.character_states).length > 0 && (
        <pre className="text-[11px] text-muted-foreground/90 whitespace-pre-wrap font-mono">
          {statesToLines(plan.character_states)}
        </pre>
      )}
      {plan.cliffhanger.trim() && (
        <p className="text-[11px] text-muted-foreground/80">
          <span className="font-medium text-muted-foreground">Out:</span> {plan.cliffhanger}
        </p>
      )}
    </div>
  );
}

/** Reconcile a stale plan against the written episode: fetch an AI proposal on
 * open, show plan vs proposal, apply (writes proposal + clears stale) or keep
 * the current plan (clears stale only). */
export function ReconcileSlotModal({ slot, open, onOpenChange, onApplied }: ReconcileSlotModalProps) {
  const reconcileMutation = useMutation({
    mutationFn: () => api.reconcileSlot(slot.id),
  });

  useEffect(() => {
    if (open) reconcileMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, slot.id]);

  const applyMutation = useMutation({
    mutationFn: (proposal: NonNullable<typeof reconcileMutation.data>['proposal']) =>
      api.updateSlot(slot.id, { ...proposal, plan_stale: false }),
    onSuccess: () => {
      onApplied();
      onOpenChange(false);
    },
  });

  const keepMutation = useMutation({
    mutationFn: () => api.updateSlot(slot.id, { plan_stale: false }),
    onSuccess: () => {
      onApplied();
      onOpenChange(false);
    },
  });

  const proposal = reconcileMutation.data?.proposal;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-y-auto">
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-orange-300" />
              Reconcile slot {slot.slot_number}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="px-6 pb-6 space-y-4">
            {reconcileMutation.isPending && (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-orange-300" />
                <p className="text-sm text-muted-foreground">Comparing the plan with the written episode…</p>
              </div>
            )}

            {reconcileMutation.isError && (
              <p className="text-sm text-red-300">{(reconcileMutation.error as Error).message}</p>
            )}

            {proposal && (
              <>
                <div className="flex gap-3 flex-col sm:flex-row">
                  <PlanColumn
                    heading="Current plan"
                    plan={{
                      title: slot.title,
                      logline: slot.logline,
                      arc_function: slot.arc_function,
                      character_states: slot.character_states,
                      cliffhanger: slot.cliffhanger,
                    }}
                  />
                  <PlanColumn heading="From the written episode" plan={proposal} />
                </div>
                {applyMutation.isError && (
                  <p className="text-sm text-red-300">{(applyMutation.error as Error).message}</p>
                )}
                <div className="flex justify-end gap-2.5">
                  <Button variant="ghost" onClick={() => keepMutation.mutate()} disabled={keepMutation.isPending}>
                    {keepMutation.isPending ? 'Saving…' : 'Keep current plan'}
                  </Button>
                  <Button onClick={() => applyMutation.mutate(proposal)} disabled={applyMutation.isPending}>
                    {applyMutation.isPending ? 'Applying…' : 'Accept proposal'}
                  </Button>
                </div>
              </>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
