import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Tv, Loader2, Send, ExternalLink } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, VAPAI_ENABLED } from '../../lib/constants';
import type { SendSeriesToVapaiResponse } from '../../types';
import { BibleEditor } from './BibleEditor';
import { EpisodeList } from './EpisodeList';
import { SeasonMap } from './SeasonMap';

interface ShowDetailProps {
  showId: string;
}

export function ShowDetail({ showId }: ShowDetailProps) {
  const navigate = useNavigate();

  const { data: show, isLoading: showLoading, isError: showError } = useQuery({
    queryKey: QUERY_KEYS.SHOW(showId),
    queryFn: () => api.getShow(showId),
  });

  const { data: bible, isLoading: bibleLoading } = useQuery({
    queryKey: QUERY_KEYS.BIBLE(showId),
    queryFn: () => api.getBible(showId),
  });

  // Push the whole series to vapai-studio. Inline banner feedback (no toast system).
  const sendSeriesMutation = useMutation<SendSeriesToVapaiResponse, Error>({
    mutationFn: () => api.sendSeriesToVapai(showId),
  });

  const isLoading = showLoading || bibleLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-amber-400" />
        <p className="text-sm text-muted-foreground">Loading show...</p>
      </div>
    );
  }

  if (showError || !show) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-sm text-muted-foreground">Failed to load show.</p>
        <button
          onClick={() => navigate('/')}
          className="text-sm text-amber-400 hover:text-amber-300 transition-colors"
        >
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-10 animate-fade-in">
      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Home
      </button>

      {/* Show header */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-indigo-500/15 flex items-center justify-center">
            <Tv className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
              {show.title}
            </h1>
            {show.description && (
              <p className="text-muted-foreground mt-1">{show.description}</p>
            )}
          </div>
        </div>

        {VAPAI_ENABLED && (
          <button
            onClick={() => sendSeriesMutation.mutate()}
            disabled={sendSeriesMutation.isPending}
            title="Enviar toda la serie (episodios + biblia) a vapai-studio para producción"
            className="flex-shrink-0 flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-foreground/80 bg-muted/40 border border-border/40 rounded-lg hover:bg-muted/70 hover:text-foreground transition-colors disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
            {sendSeriesMutation.isPending ? 'Enviando serie…' : 'Enviar serie a vapai-studio'}
          </button>
        )}
      </div>

      {/* vapai-studio send feedback (inline banners) */}
      {sendSeriesMutation.isSuccess && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 mb-6 px-4 py-2.5 text-sm rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
        >
          <span>
            Serie enviada a vapai-studio ·{' '}
            {sendSeriesMutation.data.episodes.filter((e) => !e.screenplay_empty).length} con guión,{' '}
            {sendSeriesMutation.data.episodes.filter((e) => e.screenplay_empty).length} sin guión.
          </span>
          {sendSeriesMutation.data.deep_link && (
            <a
              href={sendSeriesMutation.data.deep_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-medium underline hover:no-underline whitespace-nowrap"
            >
              Abrir en vapai <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      )}
      {sendSeriesMutation.isError && (
        <div
          role="alert"
          className="mb-6 px-4 py-2.5 text-sm rounded-lg bg-red-500/10 border border-red-500/20 text-red-300"
        >
          No se pudo enviar la serie a vapai-studio: {sendSeriesMutation.error.message}
        </div>
      )}

      {/* Series Bible */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-foreground mb-4">Series Bible</h2>
        {bible && <BibleEditor key={showId} showId={showId} bible={bible} continuityMode={show.continuity_mode} />}
      </section>

      {/* Season Map (Phase 4 -- capa de temporada) */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-foreground mb-4">Season Map</h2>
        <SeasonMap showId={showId} bibleSeasonArc={bible?.bible_season_arc ?? ''} />
      </section>

      {/* Episode List */}
      <section>
        <h2 className="text-xl font-semibold text-foreground mb-4">Episodes</h2>
        <EpisodeList showId={showId} />
      </section>
    </div>
  );
}
