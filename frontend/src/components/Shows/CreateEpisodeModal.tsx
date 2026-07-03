import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Tv, Film, Laugh } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../UI/Button';
import { QUERY_KEYS } from '../../lib/constants';
import type { TemplateListItem } from '../../types/template';

const TEMPLATE_ICON_MAP: Record<string, typeof Tv> = {
  tv: Tv,
  film: Film,
  laugh: Laugh,
};

interface CreateEpisodeModalProps {
  showId: string;
  nextEpisodeNumber: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateEpisodeModal({ showId, nextEpisodeNumber, open, onOpenChange }: CreateEpisodeModalProps) {
  const [title, setTitle] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const queryClient = useQueryClient();

  const { data: templates = [] } = useQuery({
    queryKey: [QUERY_KEYS.TEMPLATES],
    queryFn: () => api.getTemplates(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { title: string; template: string }) =>
      api.createEpisode(showId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
      onOpenChange(false);
      setTitle('');
      setSelectedTemplate('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ title, template: selectedTemplate });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border p-0 shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <Dialog.Title className="font-display text-xl font-semibold text-foreground">
              New Episode
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-5">
            {/* Episode Number Preview */}
            <p className="text-sm text-muted-foreground">
              Will be <span className="font-medium text-indigo-400">Episode {nextEpisodeNumber}</span>
            </p>

            {/* Title */}
            <div>
              <label htmlFor="episode-title" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Title
              </label>
              <input
                id="episode-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 transition-all"
                placeholder="Episode title"
                required
                autoFocus
              />
            </div>

            {/* Template Selection */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Template
              </label>
              <div className="space-y-2.5">
                {templates.map((tmpl: TemplateListItem) => {
                  const isSelected = selectedTemplate === tmpl.id;
                  const Icon = TEMPLATE_ICON_MAP[tmpl.icon] || Film;

                  return (
                    <button
                      key={tmpl.id}
                      type="button"
                      onClick={() => setSelectedTemplate(tmpl.id)}
                      className={`w-full text-left flex items-center gap-4 p-4 rounded-xl border transition-all duration-200
                        ${isSelected
                          ? 'border-indigo-500/40 bg-indigo-500/5'
                          : 'border-border hover:border-muted-foreground/20 hover:bg-muted/30'
                        }`}
                    >
                      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors
                        ${isSelected ? 'bg-indigo-500/15 text-indigo-400' : 'bg-muted text-muted-foreground'}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-foreground">{tmpl.name}</div>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{tmpl.description}</p>
                      </div>
                      {isSelected && (
                        <div className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2.5 pt-2">
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!title.trim() || !selectedTemplate || createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Episode'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
