import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, BookOpen, Tv } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, ROUTES } from '../../lib/constants';
import type { Project } from '../../types';

interface SeriesNavProps {
  showId: string;
  episodeNumber: number | null;
  episodeTitle: string;
}

/**
 * Breadcrumb + prev/next navigation shown above an episode's editor so the author
 * can move between episodes and back to the series / bible without losing their place.
 * The bible link goes to the show page (/shows/:id), where the bible + episode list live.
 */
export function SeriesNav({ showId, episodeNumber, episodeTitle }: SeriesNavProps) {
  const navigate = useNavigate();

  const { data: show } = useQuery({
    queryKey: QUERY_KEYS.SHOW(showId),
    queryFn: () => api.getShow(showId),
    staleTime: Infinity,
  });

  const { data: episodes = [] } = useQuery<Project[]>({
    queryKey: QUERY_KEYS.EPISODES(showId),
    queryFn: () => api.getEpisodes(showId),
    staleTime: 30_000,
  });

  // Episodes ordered by episode_number (reliable key).
  const ordered = [...episodes].sort(
    (a, b) => (a.episode_number ?? 0) - (b.episode_number ?? 0)
  );
  const idx = ordered.findIndex((e) => e.episode_number === episodeNumber);
  const prev = idx > 0 ? ordered[idx - 1] : null;
  const next = idx >= 0 && idx < ordered.length - 1 ? ordered[idx + 1] : null;

  const goToEpisode = (ep: Project) => {
    navigate(`/projects/${ep.id}/${(ep as any).current_phase || 'idea'}`);
  };

  return (
    <div className="flex items-center gap-2 px-6 py-2 border-b border-border/60 bg-card/30 text-sm">
      {/* Breadcrumb: Series ▸ Bible */}
      <Link
        to={ROUTES.SHOW(showId)}
        className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 transition-colors truncate max-w-[220px]"
      >
        <Tv className="h-3.5 w-3.5 flex-shrink-0" />
        {show?.title ?? 'Series'}
      </Link>

      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60 flex-shrink-0" />

      <Link
        to={ROUTES.SHOW(showId)}
        className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
        title="Series bible (on the show page)"
      >
        <BookOpen className="h-3.5 w-3.5" />
        Bible
      </Link>

      {/* Prev / current / next episode */}
      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={() => prev && goToEpisode(prev)}
          disabled={!prev}
          title={prev ? `Episode ${prev.episode_number}: ${prev.title}` : 'No previous episode'}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Previous episode"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        <span className="px-2 text-foreground truncate max-w-[260px]">
          <span className="text-indigo-400 font-medium">Ep. {episodeNumber}</span>
          {episodeTitle ? <span className="text-muted-foreground">: {episodeTitle}</span> : null}
        </span>

        <button
          type="button"
          onClick={() => next && goToEpisode(next)}
          disabled={!next}
          title={next ? `Episode ${next.episode_number}: ${next.title}` : 'No next episode'}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Next episode"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
