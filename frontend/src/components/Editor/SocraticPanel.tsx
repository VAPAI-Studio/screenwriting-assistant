import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Brain, ChevronDown, Sparkles, Check } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import type { SocraticCurrent, SocraticQuestion } from '../../types';

interface SocraticPanelProps {
  projectId: string;
}

function formatCooldown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return '<1m';
}

export function SocraticPanel({ projectId }: SocraticPanelProps) {
  const queryClient = useQueryClient();
  const [answer, setAnswer] = useState('');
  const [showHistory, setShowHistory] = useState(false);

  const currentKey = ['socratic-current', projectId];

  const { data, isLoading, isError } = useQuery<SocraticCurrent>({
    queryKey: currentKey,
    queryFn: () => api.getSocraticCurrent(projectId),
    enabled: !!projectId,
    // Generation is a one-shot on open; don't hammer it.
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });

  const { data: history } = useQuery({
    queryKey: ['socratic-history', projectId],
    queryFn: () => api.getSocraticHistory(projectId),
    enabled: !!projectId && showHistory,
  });

  const answerMutation = useMutation({
    mutationFn: ({ questionId, text }: { questionId: string; text: string }) =>
      api.answerSocratic(projectId, questionId, text),
    onSuccess: () => {
      setAnswer('');
      queryClient.invalidateQueries({ queryKey: currentKey });
      queryClient.invalidateQueries({ queryKey: ['socratic-history', projectId] });
    },
  });

  const activeQuestion: SocraticQuestion | null =
    data && (data.status === 'pending' || data.status === 'new') ? data.question : null;

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-amber-500/5 border-b border-border">
        <Brain className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-foreground">Hard Question</h3>
        <span className="text-xs text-muted-foreground ml-auto">grounded in your books + script</span>
      </div>

      <div className="p-4 space-y-4">
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking of a question…
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-400 py-2">Couldn't load a question. Try reopening this view.</p>
        )}

        {/* Active question to answer */}
        {activeQuestion && (
          <div className="space-y-3">
            <p className="text-base text-foreground leading-relaxed">{activeQuestion.question}</p>
            {activeQuestion.rationale && (
              <p className="text-xs text-muted-foreground italic flex gap-1.5">
                <Sparkles className="h-3 w-3 mt-0.5 flex-shrink-0 text-amber-400/70" />
                {activeQuestion.rationale}
              </p>
            )}
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Think it through… your answer becomes context for future writing."
              rows={4}
              className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all resize-y"
            />
            <div className="flex justify-end">
              <Button
                onClick={() => answerMutation.mutate({ questionId: activeQuestion.id, text: answer.trim() })}
                disabled={!answer.trim() || answerMutation.isPending}
              >
                {answerMutation.isPending ? 'Saving…' : 'Save answer'}
              </Button>
            </div>
            {answerMutation.isError && (
              <p className="text-xs text-red-400" role="alert">Could not save. Try again.</p>
            )}
          </div>
        )}

        {/* Cooldown state */}
        {data?.status === 'cooldown' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <Check className="h-4 w-4" />
              Answer saved.
            </div>
            <p className="text-sm text-muted-foreground">
              Next question in <span className="text-foreground font-medium">{formatCooldown(data.cooldown_seconds)}</span>.
              Sit with this one for a while.
            </p>
            {data.last_answered && (
              <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-1">
                <p className="text-xs text-muted-foreground">{data.last_answered.question}</p>
                <p className="text-sm text-foreground">{data.last_answered.answer}</p>
              </div>
            )}
          </div>
        )}

        {/* History */}
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowHistory((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showHistory ? 'rotate-180' : ''}`} />
            Past questions
          </button>
          {showHistory && (
            <div className="mt-3 space-y-3">
              {history?.questions.filter((q) => q.answer).length === 0 && (
                <p className="text-xs text-muted-foreground">No answered questions yet.</p>
              )}
              {history?.questions
                .filter((q) => q.answer)
                .map((q) => (
                  <div key={q.id} className="rounded-lg border border-border bg-muted/10 p-3 space-y-1">
                    <p className="text-xs text-muted-foreground">{q.question}</p>
                    <p className="text-sm text-foreground">{q.answer}</p>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
