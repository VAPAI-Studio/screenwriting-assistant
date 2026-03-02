import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Check, AlertCircle } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, DEBOUNCE_DELAY } from '../../lib/constants';
import { FieldRenderer } from '../Shared/FieldRenderer';
import { AIActionBar } from '../Shared/AIActionBar';
import type { SubsectionConfig, PhaseDataResponse, TemplateConfig, ListItemResponse } from '../../types/template';

interface IndividualEditorViewProps {
  subsection: SubsectionConfig;
  projectId: string;
  phase: string;
  phaseData: PhaseDataResponse | null;
  templateConfig: TemplateConfig;
  itemId?: string;
}

export function IndividualEditorView({ subsection, projectId, phase, phaseData, itemId }: IndividualEditorViewProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saveTimer, setSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const editorConfig = subsection.editor_config;
  const fields = editorConfig?.fields || subsection.fields || [];
  const layout = editorConfig?.layout || 'single_column';

  const { data: allItems = [] } = useQuery({
    queryKey: QUERY_KEYS.LIST_ITEMS(phaseData?.id || ''),
    queryFn: () => api.getListItems(phaseData!.id),
    enabled: !!phaseData?.id,
  });

  const { data: item, isLoading } = useQuery({
    queryKey: QUERY_KEYS.LIST_ITEM(itemId || ''),
    queryFn: () => api.getListItem(itemId!),
    enabled: !!itemId,
  });

  useEffect(() => {
    if (item?.content) {
      setFormData(item.content as Record<string, string>);
    }
  }, [item]);

  const saveMutation = useMutation({
    mutationFn: (content: Record<string, string>) =>
      api.updateListItem(itemId!, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEM(itemId!) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEMS(phaseData?.id || '') });
    },
  });

  const handleFieldChange = useCallback((key: string, value: string) => {
    setFormData(prev => {
      const updated = { ...prev, [key]: value };
      if (saveTimer) clearTimeout(saveTimer);
      const timer = setTimeout(() => {
        saveMutation.mutate(updated);
      }, DEBOUNCE_DELAY * 3);
      setSaveTimer(timer);
      return updated;
    });
  }, [saveTimer, saveMutation, itemId]);

  const currentIndex = allItems.findIndex((i) => i.id === itemId);
  const prevItem = currentIndex > 0 ? allItems[currentIndex - 1] : null;
  const nextItem = currentIndex < allItems.length - 1 ? allItems[currentIndex + 1] : null;

  const navigateToItem = (item: ListItemResponse) => {
    navigate(`/projects/${projectId}/${phase}/${subsection.key}/${item.id}`);
  };

  const listSubsectionKey = subsection.key.replace('_detail', '_list');

  if (!itemId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 animate-fade-in">
        <p className="text-sm text-muted-foreground">Select an item from the list to edit it.</p>
        <button
          onClick={() => navigate(`/projects/${projectId}/${phase}/${listSubsectionKey}`)}
          className="text-sm text-amber-400 hover:text-amber-300 transition-colors"
        >
          Go to list
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      {/* Navigation Header */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={() => navigate(`/projects/${projectId}/${phase}/${listSubsectionKey}`)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to list
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => prevItem && navigateToItem(prevItem)}
            disabled={!prevItem}
            className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20 disabled:cursor-not-allowed transition-all"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-muted-foreground font-mono min-w-[4rem] text-center">
            {currentIndex + 1} / {allItems.length}
          </span>
          <button
            onClick={() => nextItem && navigateToItem(nextItem)}
            disabled={!nextItem}
            className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20 disabled:cursor-not-allowed transition-all"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Title */}
      <div className="mb-6">
        <h2 className="font-display text-xl font-semibold text-foreground">
          {formData.summary || formData.name || `Item ${currentIndex + 1}`}
        </h2>
      </div>

      {/* AI Actions */}
      {subsection.ai_actions && subsection.ai_actions.length > 0 && (
        <div className="mb-8">
          <AIActionBar
            actions={subsection.ai_actions}
            projectId={projectId}
            phase={phase}
            subsectionKey={subsection.key}
            itemId={itemId}
          />
        </div>
      )}

      {/* Fields */}
      {layout === 'two_column' ? (
        <div className="grid grid-cols-2 gap-5">
          {fields.map((field) => (
            <div key={field.key} className={field.column === 2 ? 'col-start-2' : ''}>
              <FieldRenderer
                field={field}
                value={formData[field.key] || ''}
                onChange={handleFieldChange}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          {fields.map((field) => (
            <FieldRenderer
              key={field.key}
              field={field}
              value={formData[field.key] || ''}
              onChange={handleFieldChange}
            />
          ))}
        </div>
      )}

      {/* Save status */}
      <div className="mt-6 flex justify-end">
        <div className="flex items-center gap-1.5 text-xs">
          {saveMutation.isPending && <span className="text-muted-foreground animate-pulse-warm">Saving...</span>}
          {saveMutation.isSuccess && (
            <span className="flex items-center gap-1 text-emerald-400"><Check className="h-3 w-3" /> Saved</span>
          )}
          {saveMutation.isError && (
            <span className="flex items-center gap-1 text-destructive"><AlertCircle className="h-3 w-3" /> Failed</span>
          )}
        </div>
      </div>
    </div>
  );
}
