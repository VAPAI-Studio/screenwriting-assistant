import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Layers, BookOpen, History } from 'lucide-react';
import { api } from '../../lib/api';
import type { EpisodeContext } from '../../types';

interface EpisodeContextPanelProps {
  projectId: string;
}

const MODE_LABEL: Record<string, string> = {
  connected: 'Connected series',
  anthology: 'Anthology',
  standalone: 'Standalone',
};

function BibleField({ label, value }: { label: string; value: string }) {
  if (!value?.trim()) return null;
  return (
    <div>
      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">{label}</div>
      <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed line-clamp-4">{value}</p>
    </div>
  );
}

export function EpisodeContextPanel({ projectId }: EpisodeContextPanelProps) {
  const [open, setOpen] = useState(false);

  const { data } = useQuery<EpisodeContext>({
    queryKey: ['episode-context', projectId],
    queryFn: () => api.getEpisodeContext(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // Only render for episodes (projects that belong to a show).
  if (!data || data.is_episode === false) return null;

  const { bible } = data;
  const hasBible =
    !!(bible.characters || bible.world_setting || bible.season_arc || bible.tone_style)?.trim?.() ||
    bible.episode_duration_minutes != null;
  const priors = data.prior_episodes;

  return (
    <div className="border-b border-border bg-card/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-5 py-2.5 text-left hover:bg-muted/30 transition-colors"
      >
        <Layers className="h-4 w-4 text-indigo-400 flex-shrink-0" />
        <span className="text-sm font-medium text-foreground">Carried into this episode</span>
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          {MODE_LABEL[data.continuity_mode] || data.continuity_mode}
        </span>
        {data.continuity_mode === 'connected' && (
          <span className="text-xs text-muted-foreground">· {priors.length} prior episode{priors.length === 1 ? '' : 's'}</span>
        )}
        <ChevronDown className={`h-4 w-4 text-muted-foreground ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="px-5 pb-4 grid gap-4 md:grid-cols-2">
          {/* Bible */}
          <div className="rounded-lg border border-border bg-background/40 p-3 space-y-2.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <BookOpen className="h-3.5 w-3.5 text-amber-400" /> Series bible
            </div>
            {hasBible ? (
              <div className="space-y-2.5">
                <BibleField label="Characters" value={bible.characters} />
                <BibleField label="World / Setting" value={bible.world_setting} />
                {data.continuity_mode === 'connected' && <BibleField label="Season arc" value={bible.season_arc} />}
                <BibleField label="Tone & style" value={bible.tone_style} />
                {bible.episode_duration_minutes != null && (
                  <div className="text-[11px] text-muted-foreground">Target duration: {bible.episode_duration_minutes} min</div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No bible content yet. Edit it on the show page.</p>
            )}
          </div>

          {/* Prior episodes (connected only) */}
          {data.continuity_mode === 'connected' && (
            <div className="rounded-lg border border-border bg-background/40 p-3 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <History className="h-3.5 w-3.5 text-indigo-400" /> Prior episodes
              </div>
              {priors.length === 0 ? (
                <p className="text-xs text-muted-foreground">No earlier episodes with a summary yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {priors.map((ep) => (
                    <div key={ep.episode_number}>
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                        Ep. {ep.episode_number}: {ep.title}
                        {ep.stale && <span className="ml-1 text-amber-400/70 normal-case">(summary may be out of date)</span>}
                      </div>
                      <p className="text-xs text-foreground/90 leading-relaxed line-clamp-4">{ep.summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
