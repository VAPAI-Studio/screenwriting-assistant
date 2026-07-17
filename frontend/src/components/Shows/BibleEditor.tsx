import { useState, useEffect, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Check, Zap, Link, LayoutGrid, Plus, Trash2, Users, Wand2 } from 'lucide-react';
import { api } from '../../lib/api';
import { BIBLE_SECTIONS, SHOW_PRESETS, QUERY_KEYS } from '../../lib/constants';
import type { BibleResponse, BibleUpdate, ContinuityMode, RegularCastMember } from '../../types';
import { BibleWizardModal } from './BibleWizardModal';
import { EpisodeDurationPicker } from './EpisodeDurationPicker';

interface BibleEditorProps {
  showId: string;
  bible: BibleResponse;
  continuityMode: ContinuityMode;
}

// Maps the preset's icon string (from SHOW_PRESETS) to its lucide component.
const PRESET_ICON_MAP: Record<string, typeof Zap> = { Zap, Link, LayoutGrid };

// Pre-selection rule (UI-SPEC :102): duration 2 + connected -> Microserie,
// other connected -> Serie conectada, anthology -> Antología. A show in the
// pre-existing 'standalone' (feature-film) mode maps to NO preset card (IN-02):
// none of the three presets represents standalone, so highlighting Antología
// would be misleading.
function presetIdForMode(mode: ContinuityMode, durationMinutes: number | null): string {
  if (mode === 'connected') {
    return durationMinutes === 2 ? 'microserie' : 'serie-conectada';
  }
  if (mode === 'anthology') {
    return 'antologia';
  }
  return '';
}

export function BibleEditor({ showId, bible, continuityMode }: BibleEditorProps) {
  const queryClient = useQueryClient();

  const [values, setValues] = useState<Record<string, string>>({
    bible_central_premise: bible.bible_central_premise,
    bible_story_engine: bible.bible_story_engine,
    bible_series_questions: bible.bible_series_questions,
    bible_characters: bible.bible_characters,
    bible_world_setting: bible.bible_world_setting,
    bible_season_arc: bible.bible_season_arc,
    bible_tone_style: bible.bible_tone_style,
  });

  const [duration, setDuration] = useState<number | null>(bible.episode_duration_minutes);

  // Structured regular cast — a repeatable list, not a textarea.
  const [regularCast, setRegularCast] = useState<RegularCastMember[]>(bible.bible_regular_cast || []);
  const [castExpanded, setCastExpanded] = useState(false);
  // Stable per-row keys so removing a row doesn't shift React keys by position
  // (which would jump focus/cursor to the wrong row). Not persisted — UI only.
  const castKeySeq = useRef(0);
  const [castKeys, setCastKeys] = useState<number[]>(
    () => (bible.bible_regular_cast || []).map(() => castKeySeq.current++)
  );

  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    bible_central_premise: true,
    bible_story_engine: false,
    bible_series_questions: false,
    bible_characters: false,
    bible_world_setting: false,
    bible_season_arc: false,
    bible_tone_style: false,
  });

  const [savedField, setSavedField] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  // Pre-select the preset card matching the show's current mode (UI-SPEC :102).
  const [selectedPreset, setSelectedPreset] = useState<string>(
    () => presetIdForMode(continuityMode, bible.episode_duration_minutes)
  );

  // Timed "Saved" flashes — tracked so they can be cancelled on unmount (NEW-01).
  const modeSavedTimer = useRef<ReturnType<typeof setTimeout>>();
  const savedFieldTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => {
    if (modeSavedTimer.current) clearTimeout(modeSavedTimer.current);
    if (savedFieldTimer.current) clearTimeout(savedFieldTimer.current);
  }, []);

  // Initialize from bible props on mount only -- avoid overwriting local edits on query refetch
  const loaded = useRef(false);
  useEffect(() => {
    if (!loaded.current) {
      setValues({
        bible_central_premise: bible.bible_central_premise,
        bible_story_engine: bible.bible_story_engine,
        bible_series_questions: bible.bible_series_questions,
        bible_characters: bible.bible_characters,
        bible_world_setting: bible.bible_world_setting,
        bible_season_arc: bible.bible_season_arc,
        bible_tone_style: bible.bible_tone_style,
      });
      setDuration(bible.episode_duration_minutes);
      setRegularCast(bible.bible_regular_cast || []);
      setCastKeys((bible.bible_regular_cast || []).map(() => castKeySeq.current++));
      // Seed the selected preset once; later query refetches must not clobber
      // a user's in-session mode change.
      setSelectedPreset(presetIdForMode(continuityMode, bible.episode_duration_minutes));
      loaded.current = true;
    }
  }, [bible, continuityMode]);

  const [modeSaved, setModeSaved] = useState(false);

  const updateShowMutation = useMutation({
    mutationFn: (mode: ContinuityMode) => api.updateShow(showId, { continuity_mode: mode }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOW(showId) });
      // The stored episode_duration_minutes in the BIBLE cache is the sole input to
      // presetIdForMode's Microserie-vs-Serie-conectada disambiguation, so it must be
      // refreshed too or a navigate-away-and-return can re-select the wrong card (WR-03).
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BIBLE(showId) });
      // Auto-dismiss the "Saved" indicator instead of leaving it on forever (WR-02).
      setModeSaved(true);
      if (modeSavedTimer.current) clearTimeout(modeSavedTimer.current);
      modeSavedTimer.current = setTimeout(() => setModeSaved(false), 2000);
    },
    onError: () => {
      // A failed mode-change PUT leaves the card selected locally but the backend
      // still holds the prior mode (WR-01). Revert to the persisted selection so the
      // UI doesn't lie, and surface the failure inline.
      setSelectedPreset(presetIdForMode(continuityMode, duration));
    },
  });

  const handlePresetSelect = (presetId: string, mode: ContinuityMode) => {
    if (presetId === selectedPreset) return;
    setSelectedPreset(presetId);
    updateShowMutation.mutate(mode);
  };

  const updateBibleMutation = useMutation({
    mutationFn: (data: Partial<BibleUpdate>) => api.updateBible(showId, data),
    onSuccess: (_data, variables) => {
      const field = Object.keys(variables)[0];
      setSavedField(field);
      if (savedFieldTimer.current) clearTimeout(savedFieldTimer.current);
      savedFieldTimer.current = setTimeout(() => setSavedField(null), 2000);
    },
  });

  const handleBlur = (key: string) => {
    updateBibleMutation.mutate({ [key]: values[key] });
  };

  const handleDurationChange = (val: number | null) => {
    setDuration(val);
    updateBibleMutation.mutate({ episode_duration_minutes: val });
  };

  // Regular cast: local-edit while typing, persist the whole list on blur/add/remove.
  const persistCast = (next: RegularCastMember[]) => {
    updateBibleMutation.mutate({ bible_regular_cast: next });
  };
  const updateCastMember = (index: number, field: keyof RegularCastMember, value: string) => {
    setRegularCast(prev => prev.map((m, i) => (i === index ? { ...m, [field]: value } : m)));
  };
  const addCastMember = () => {
    const next = [...regularCast, { name: '', role: '', arc: '' }];
    setRegularCast(next);
    setCastKeys(prev => [...prev, castKeySeq.current++]);
    setCastExpanded(true);
  };
  const removeCastMember = (index: number) => {
    const next = regularCast.filter((_, i) => i !== index);
    setRegularCast(next);
    setCastKeys(prev => prev.filter((_, i) => i !== index));
    persistCast(next);
  };

  return (
    <div className="space-y-3">
      <BibleWizardModal showId={showId} open={wizardOpen} onOpenChange={setWizardOpen} />

      {/* AI bible wizard — drafts every section from a short seed */}
      <button
        type="button"
        onClick={() => setWizardOpen(true)}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-amber-500/30 bg-amber-500/5 text-sm font-medium text-amber-300 hover:bg-amber-500/10 hover:border-amber-500/50 transition-colors"
      >
        <Wand2 className="h-4 w-4" /> Draft the bible with AI
      </button>

      {/* Continuity mode-change control -- reuses the creation preset cards */}
      <div className="border border-border rounded-xl px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Continuity
          </span>
          {modeSaved && !updateShowMutation.isPending && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <Check className="h-3 w-3" /> Saved
            </span>
          )}
        </div>
        <div className="space-y-2.5">
          {SHOW_PRESETS.map((preset) => {
            const isSelected = selectedPreset === preset.id;
            const Icon = PRESET_ICON_MAP[preset.icon] || Zap;
            return (
              <button
                key={preset.id}
                type="button"
                disabled={updateShowMutation.isPending}
                onClick={() => handlePresetSelect(preset.id, preset.mode)}
                className={`w-full text-left flex items-center gap-4 p-4 rounded-xl border transition-all duration-200
                  ${isSelected
                    ? 'border-amber-500/40 bg-amber-500/5 glow-amber'
                    : 'border-border hover:border-muted-foreground/20 hover:bg-muted/30'
                  }
                  ${updateShowMutation.isPending ? 'opacity-60 cursor-not-allowed' : ''}`}
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
        {updateShowMutation.isError && (
          <p className="mt-2.5 text-xs text-red-400" role="alert">
            Could not change the continuity mode. Check your connection and try again.
          </p>
        )}
      </div>

      {BIBLE_SECTIONS.map((section) => (
        <div key={section.key} className="border border-border rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => setExpanded(prev => ({ ...prev, [section.key]: !prev[section.key] }))}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground hover:bg-muted/30 transition-colors"
          >
            <span>{section.label}</span>
            <div className="flex items-center gap-2">
              {savedField === section.key && (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <Check className="h-3 w-3" /> Saved
                </span>
              )}
              <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded[section.key] ? 'rotate-180' : ''}`} />
            </div>
          </button>
          {expanded[section.key] && (
            <div className="px-4 pb-4">
              <textarea
                value={values[section.key] || ''}
                onChange={(e) => setValues(prev => ({ ...prev, [section.key]: e.target.value }))}
                onBlur={() => handleBlur(section.key)}
                placeholder={section.placeholder}
                rows={6}
                className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all resize-y min-h-[120px]"
              />
            </div>
          )}
        </div>
      ))}

      {/* Regular Cast — structured repeatable roster (not a textarea) */}
      <div className="border border-border rounded-xl overflow-hidden">
        <button
          type="button"
          onClick={() => setCastExpanded(prev => !prev)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground hover:bg-muted/30 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            Regular Cast
            {regularCast.length > 0 && (
              <span className="text-xs text-muted-foreground">({regularCast.length})</span>
            )}
          </span>
          <div className="flex items-center gap-2">
            {savedField === 'bible_regular_cast' && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <Check className="h-3 w-3" /> Saved
              </span>
            )}
            <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${castExpanded ? 'rotate-180' : ''}`} />
          </div>
        </button>
        {castExpanded && (
          <div className="px-4 pb-4 space-y-3">
            {regularCast.length === 0 && (
              <p className="text-xs text-muted-foreground py-2">
                The fixed roster your episodes lean on. Add the recurring characters an episode can put to work each week.
              </p>
            )}
            {regularCast.map((member, index) => (
              <div key={castKeys[index] ?? index} className="rounded-lg border border-border p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    value={member.name}
                    onChange={(e) => updateCastMember(index, 'name', e.target.value)}
                    onBlur={() => persistCast(regularCast)}
                    placeholder="Name"
                    className="flex-1 rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40"
                  />
                  <button
                    type="button"
                    onClick={() => removeCastMember(index)}
                    aria-label="Remove cast member"
                    className="flex-shrink-0 p-2 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <input
                  value={member.role}
                  onChange={(e) => updateCastMember(index, 'role', e.target.value)}
                  onBlur={() => persistCast(regularCast)}
                  placeholder="Role in the series (what they do, function)"
                  className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40"
                />
                <textarea
                  value={member.arc}
                  onChange={(e) => updateCastMember(index, 'arc', e.target.value)}
                  onBlur={() => persistCast(regularCast)}
                  placeholder="Season-long arc / where they're headed (optional)"
                  rows={2}
                  className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 resize-y"
                />
              </div>
            ))}
            <button
              type="button"
              onClick={addCastMember}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-dashed border-border text-sm text-muted-foreground hover:text-foreground hover:border-muted-foreground/40 transition-colors"
            >
              <Plus className="h-4 w-4" /> Add cast member
            </button>
          </div>
        )}
      </div>

      {/* Episode Duration */}
      <div className="border border-border rounded-xl px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-foreground">Episode Duration</span>
          {savedField === 'episode_duration_minutes' && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <Check className="h-3 w-3" /> Saved
            </span>
          )}
        </div>
        <EpisodeDurationPicker value={duration} onChange={handleDurationChange} />
      </div>
    </div>
  );
}
