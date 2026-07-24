import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import type { EpisodeSlot, Project } from '../../types';

/** character_states dict <-> editable "Name: state" lines. */
export function statesToLines(states: Record<string, string>): string {
  return Object.entries(states).map(([name, state]) => `${name}: ${state}`).join('\n');
}

export function linesToStates(text: string): Record<string, string> {
  const states: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const idx = line.indexOf(':');
    if (idx <= 0) continue;
    const name = line.slice(0, idx).trim();
    const state = line.slice(idx + 1).trim();
    if (name && state) states[name] = state;
  }
  return states;
}

interface SlotEditModalProps {
  slot: EpisodeSlot;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  /** The show's episodes, for manual assignment. */
  episodes: Project[];
  /** project_ids already linked to OTHER slots (not selectable here). */
  takenProjectIds: Set<string>;
}

const FIELD_CLS =
  'w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 transition-all';
const LABEL_CLS = 'block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2';

export function SlotEditModal({ slot, open, onOpenChange, onSaved, episodes, takenProjectIds }: SlotEditModalProps) {
  const [title, setTitle] = useState(slot.title);
  const [logline, setLogline] = useState(slot.logline);
  const [arcFunction, setArcFunction] = useState(slot.arc_function);
  const [statesText, setStatesText] = useState(statesToLines(slot.character_states));
  const [cliffhanger, setCliffhanger] = useState(slot.cliffhanger);
  const [notes, setNotes] = useState(slot.notes);
  const [assignedId, setAssignedId] = useState<string>(slot.project_id ?? '');
  // Selectable: episodes not slotted elsewhere (plus the one already linked here).
  const assignable = episodes.filter(
    (e) => !takenProjectIds.has(e.id) || e.id === slot.project_id
  );

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateSlot(slot.id, {
        title,
        logline,
        arc_function: arcFunction,
        character_states: linesToStates(statesText),
        cliffhanger,
        notes,
        project_id: assignedId || null,
      }),
    onSuccess: () => {
      onSaved();
      onOpenChange(false);
    },
  });

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-y-auto">
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground">
              Slot {slot.slot_number} — episode plan
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              saveMutation.mutate();
            }}
            className="px-6 pb-6 space-y-4"
          >
            <div>
              <label className={LABEL_CLS}>Working title</label>
              <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className={FIELD_CLS} placeholder="Episode title" />
            </div>
            <div>
              <label className={LABEL_CLS}>Logline</label>
              <textarea value={logline} onChange={(e) => setLogline(e.target.value)} rows={3} className={FIELD_CLS} placeholder="What the episode is about, in 1-2 sentences" />
            </div>
            <div>
              <label className={LABEL_CLS}>Function in the season arc</label>
              <input type="text" value={arcFunction} onChange={(e) => setArcFunction(e.target.value)} className={FIELD_CLS} placeholder='e.g. "midpoint reversal — the ally defects"' />
            </div>
            <div>
              <label className={LABEL_CLS}>Character states at end of episode</label>
              <textarea
                value={statesText}
                onChange={(e) => setStatesText(e.target.value)}
                rows={4}
                className={`${FIELD_CLS} font-mono text-xs`}
                placeholder={'One per line:\nMara: suspects the betrayal\nLeo: exiled from the crew'}
              />
            </div>
            <div>
              <label className={LABEL_CLS}>Cliffhanger / out</label>
              <textarea value={cliffhanger} onChange={(e) => setCliffhanger(e.target.value)} rows={2} className={FIELD_CLS} placeholder="What pulls into the next episode (empty = clean resolution)" />
            </div>
            <div>
              <label className={LABEL_CLS}>Episodio asignado</label>
              <select
                value={assignedId}
                onChange={(e) => setAssignedId(e.target.value)}
                className={FIELD_CLS}
              >
                <option value="">— Sin episodio (solo plan) —</option>
                {assignable.map((e) => (
                  <option key={e.id} value={e.id}>
                    Ep {e.episode_number ?? '?'} — {e.title}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-muted-foreground mt-1">
                Conectá un episodio ya creado con esta casilla del mapa — el plan pasa a seguir a ese episodio.
              </p>
            </div>
            <div>
              <label className={LABEL_CLS}>Notes</label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className={FIELD_CLS} placeholder="Anything else" />
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? 'Saving…' : 'Save plan'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
