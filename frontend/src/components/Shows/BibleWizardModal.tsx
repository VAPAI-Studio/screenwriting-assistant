import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Wand2, Loader2, Check } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import { QUERY_KEYS } from '../../lib/constants';
import type { BibleWizardResponse, BibleUpdate, BibleResponse, RegularCastMember } from '../../types';

interface BibleWizardModalProps {
  showId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called with the fresh bible after an apply, so the editor can re-seed its
      local state (its init effect deliberately ignores query refetches). */
  onApplied?: (bible: BibleResponse) => void;
}

const FIELD_CLS =
  'w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all';
const LABEL_CLS = 'block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2';

// The eight proposable fields, in display order, with human labels. `text` marks
// plain-string fields (all but the cast, which renders as a roster list).
const SECTIONS: { key: keyof BibleWizardResponse; label: string; text: boolean }[] = [
  { key: 'bible_central_premise', label: 'Central Premise', text: true },
  { key: 'bible_story_engine', label: 'Story Engine', text: true },
  { key: 'bible_series_questions', label: 'Series Questions', text: true },
  { key: 'bible_regular_cast', label: 'Regular Cast', text: false },
  { key: 'bible_characters', label: 'Characters', text: true },
  { key: 'bible_world_setting', label: 'World / Setting', text: true },
  { key: 'bible_season_arc', label: 'Season Arc', text: true },
  { key: 'bible_tone_style', label: 'Tone & Style', text: true },
];

function hasContent(v: BibleWizardResponse[keyof BibleWizardResponse]): boolean {
  return Array.isArray(v) ? v.length > 0 : !!(v || '').trim();
}

export function BibleWizardModal({ showId, open, onOpenChange, onApplied }: BibleWizardModalProps) {
  const queryClient = useQueryClient();
  const [logline, setLogline] = useState('');
  const [genre, setGenre] = useState('');
  const [tone, setTone] = useState('');
  const [guidance, setGuidance] = useState('');
  const [proposal, setProposal] = useState<BibleWizardResponse | null>(null);
  // Which proposed fields the user has selected to apply. Seeded to all
  // non-empty fields when a proposal arrives.
  const [accepted, setAccepted] = useState<Set<string>>(new Set());

  const runMutation = useMutation({
    mutationFn: () =>
      api.runBibleWizard(showId, {
        logline: logline.trim(),
        genre: genre.trim(),
        tone: tone.trim(),
        custom_guidance: guidance.trim(),
      }),
    onSuccess: (result) => {
      setProposal(result);
      setAccepted(new Set(SECTIONS.filter(s => hasContent(result[s.key])).map(s => s.key)));
    },
  });

  const applyMutation = useMutation({
    mutationFn: () => {
      const data: Partial<BibleUpdate> = {};
      if (proposal) {
        for (const s of SECTIONS) {
          if (accepted.has(s.key)) {
            // key/value types line up field-by-field; assign through a cast.
            (data as Record<string, unknown>)[s.key] = proposal[s.key];
          }
        }
      }
      return api.updateBible(showId, data);
    },
    onSuccess: (fresh) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BIBLE(showId) });
      if (fresh) onApplied?.(fresh);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOW(showId) });
      handleClose(false);
    },
  });

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      setProposal(null);
      setAccepted(new Set());
      runMutation.reset();
      applyMutation.reset();
    }
    onOpenChange(nextOpen);
  };

  const toggle = (key: string) => {
    setAccepted(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const generating = runMutation.isPending;

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[640px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-y-auto">
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-amber-400" />
              Series bible wizard
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="px-6 pb-6">
            {/* Step 1: seed form */}
            {!proposal && !generating && (
              <form
                onSubmit={(e) => { e.preventDefault(); runMutation.mutate(); }}
                className="space-y-4"
              >
                <p className="text-xs text-muted-foreground">
                  Give the wizard a seed and it will draft every bible section. Your current
                  bible is used as grounding — existing content is refined, not overwritten, and
                  nothing is saved until you choose what to apply.
                </p>
                <div>
                  <label className={LABEL_CLS}>Logline / idea</label>
                  <textarea
                    value={logline}
                    onChange={(e) => setLogline(e.target.value)}
                    rows={3}
                    className={FIELD_CLS}
                    placeholder="The show in a sentence or two — what it's about, who it follows"
                  />
                </div>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className={LABEL_CLS}>Genre</label>
                    <input value={genre} onChange={(e) => setGenre(e.target.value)} className={FIELD_CLS} placeholder="e.g. Crime, Comedy" />
                  </div>
                  <div className="flex-1">
                    <label className={LABEL_CLS}>Tone</label>
                    <input value={tone} onChange={(e) => setTone(e.target.value)} className={FIELD_CLS} placeholder="e.g. Grounded, Soapy" />
                  </div>
                </div>
                <div>
                  <label className={LABEL_CLS}>Custom guidance (optional)</label>
                  <textarea
                    value={guidance}
                    onChange={(e) => setGuidance(e.target.value)}
                    rows={2}
                    className={FIELD_CLS}
                    placeholder="Constraints, references, must-haves…"
                  />
                </div>
                {runMutation.isError && (
                  <p className="text-sm text-red-300">{(runMutation.error as Error).message}</p>
                )}
                <div className="flex justify-end gap-2.5 pt-2">
                  <Button type="button" variant="ghost" onClick={() => handleClose(false)}>Cancel</Button>
                  <Button type="submit">Draft the bible</Button>
                </div>
              </form>
            )}

            {/* Step 2: generating */}
            {generating && (
              <div className="flex flex-col items-center justify-center py-14 gap-3">
                <Loader2 className="h-7 w-7 animate-spin text-amber-400" />
                <p className="text-sm text-muted-foreground">Drafting the series bible…</p>
              </div>
            )}

            {/* Step 3: preview with per-field accept toggles */}
            {proposal && !generating && (
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground">
                  Pick the sections to apply. Checked sections overwrite the matching bible field.
                </p>
                <div className="space-y-2 max-h-[52vh] overflow-y-auto pr-1">
                  {SECTIONS.filter(s => hasContent(proposal[s.key])).map((s) => {
                    const on = accepted.has(s.key);
                    return (
                      <button
                        type="button"
                        key={s.key}
                        onClick={() => toggle(s.key)}
                        className={`w-full text-left rounded-lg border p-3 transition-colors ${on ? 'border-amber-500/40 bg-amber-500/5' : 'border-border hover:border-muted-foreground/30'}`}
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 ${on ? 'bg-amber-500 text-white' : 'border border-border'}`}>
                            {on && <Check className="h-3 w-3" />}
                          </span>
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{s.label}</span>
                        </div>
                        {s.text ? (
                          <p className="text-sm text-foreground whitespace-pre-wrap">{proposal[s.key] as string}</p>
                        ) : (
                          <ul className="text-sm text-foreground space-y-0.5">
                            {(proposal.bible_regular_cast as RegularCastMember[]).map((m, i) => (
                              <li key={i}>
                                <span className="font-medium">{m.name || '(unnamed)'}</span>
                                {(m.role || m.arc) && <span className="text-muted-foreground"> — {[m.role, m.arc].filter(Boolean).join(' · ')}</span>}
                              </li>
                            ))}
                          </ul>
                        )}
                      </button>
                    );
                  })}
                </div>
                {applyMutation.isError && (
                  <p className="text-sm text-red-300">{(applyMutation.error as Error).message}</p>
                )}
                <div className="flex justify-end gap-2.5">
                  <Button variant="ghost" onClick={() => { setProposal(null); setAccepted(new Set()); }}>
                    Regenerate
                  </Button>
                  <Button onClick={() => applyMutation.mutate()} disabled={applyMutation.isPending || accepted.size === 0}>
                    {applyMutation.isPending ? 'Applying…' : `Apply ${accepted.size} section${accepted.size !== 1 ? 's' : ''}`}
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
