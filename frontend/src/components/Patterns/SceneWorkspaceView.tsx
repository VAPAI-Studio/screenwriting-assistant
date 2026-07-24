import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Plus, GripVertical, Trash2, Wand2, X,
  ChevronLeft, ChevronRight, Check, AlertCircle, Loader2,
} from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, DEBOUNCE_DELAY } from '../../lib/constants';
import { FieldRenderer } from '../Shared/FieldRenderer';
import { WizardView } from './WizardView';
import type { SubsectionConfig, PhaseDataResponse, TemplateConfig, ListItemResponse } from '../../types/template';

interface SceneWorkspaceViewProps {
  subsection: SubsectionConfig;
  projectId: string;
  phase: string;
  phaseData: PhaseDataResponse | null;
  templateConfig: TemplateConfig;
  itemId?: string;
}

const STATUS_STYLES: Record<string, string> = {
  complete: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  in_progress: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  draft: 'bg-muted text-muted-foreground border-transparent',
};

// Master-detail fusion of the old scene_wizard / scene_list / scene_detail tabs:
// the list is the master pane, the per-scene editor the detail pane, and the
// wizard renders as the empty-state action (or on demand from the list header).
// The hidden sibling subsections still supply wizard_config / editor_config.
export function SceneWorkspaceView({ subsection, projectId, phase, phaseData, templateConfig, itemId }: SceneWorkspaceViewProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saveTimer, setSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [fillingKey, setFillingKey] = useState<string | null>(null);

  const listConfig = subsection.list_config;
  const itemType = listConfig?.item_type || 'scene';

  const phaseConfig = templateConfig?.phases?.find((p) => p.id === phase);
  const wizardSub = phaseConfig?.subsections?.find(
    (s) => s.key === subsection.key.replace('_list', '_wizard')
  );
  const detailSub = phaseConfig?.subsections?.find(
    (s) => s.key === subsection.key.replace('_list', '_detail')
  );
  const editorConfig = detailSub?.editor_config;
  const fields = editorConfig?.fields || [];
  const layout = editorConfig?.layout || 'single_column';

  const { data: items = [], isLoading } = useQuery({
    queryKey: QUERY_KEYS.LIST_ITEMS(phaseData?.id || ''),
    queryFn: () => api.getListItems(phaseData!.id),
    enabled: !!phaseData?.id,
  });

  // Route-driven selection with first-item fallback (deep links keep working;
  // deleting the selected scene falls back gracefully).
  const selectedId = itemId && items.some((i) => i.id === itemId) ? itemId : items[0]?.id;
  const selectedIndex = items.findIndex((i) => i.id === selectedId);

  const { data: selectedItem } = useQuery({
    queryKey: QUERY_KEYS.LIST_ITEM(selectedId || ''),
    queryFn: () => api.getListItem(selectedId!),
    enabled: !!selectedId,
  });

  useEffect(() => {
    if (selectedItem?.content) {
      setFormData(selectedItem.content as Record<string, string>);
    }
  }, [selectedItem]);

  const selectItem = (item: ListItemResponse) => {
    navigate(`/projects/${projectId}/${phase}/${subsection.key}/${item.id}`, { replace: true });
    setShowWizard(false);
  };

  // ── List mutations ────────────────────────────────────────────────────
  const invalidateList = () =>
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEMS(phaseData!.id) });

  const createMutation = useMutation({
    mutationFn: () => api.createListItem(phaseData!.id, { item_type: itemType, content: {} }),
    onSuccess: (created: ListItemResponse) => {
      invalidateList();
      navigate(`/projects/${projectId}/${phase}/${subsection.key}/${created.id}`, { replace: true });
      setShowWizard(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteListItem(id),
    onSuccess: invalidateList,
  });

  const reorderMutation = useMutation({
    mutationFn: (reordered: Array<{ id: string; sort_order: number }>) =>
      api.reorderListItems(phaseData!.id, reordered),
    onSuccess: invalidateList,
  });

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    const newItems = [...items];
    const [draggedItem] = newItems.splice(draggedIndex, 1);
    newItems.splice(index, 0, draggedItem);
    setDraggedIndex(index);
    reorderMutation.mutate(newItems.map((item, i) => ({ id: item.id, sort_order: i })));
  };

  // ── Detail editor mutations ───────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: (content: Record<string, string>) => api.updateListItem(selectedId!, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEM(selectedId!) });
      invalidateList();
    },
  });

  const autofillMutation = useMutation({
    mutationFn: (fieldKey: string) =>
      api.fillBlanks({
        project_id: projectId,
        phase,
        subsection_key: detailSub?.key || subsection.key,
        item_id: selectedId,
        field_key: fieldKey,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEM(selectedId!) });
      invalidateList();
      setFillingKey(null);
    },
    onError: () => setFillingKey(null),
  });

  const handleFieldChange = useCallback((key: string, value: string) => {
    setFormData((prev) => {
      const updated = { ...prev, [key]: value };
      if (saveTimer) clearTimeout(saveTimer);
      const timer = setTimeout(() => saveMutation.mutate(updated), DEBOUNCE_DELAY * 3);
      setSaveTimer(timer);
      return updated;
    });
  }, [saveTimer, saveMutation, selectedId]);

  const handleAutofill = useCallback((fieldKey: string) => {
    setFillingKey(fieldKey);
    autofillMutation.mutate(fieldKey);
  }, [autofillMutation]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-sm text-muted-foreground">Loading scenes...</span>
      </div>
    );
  }

  // ── Empty state: the wizard IS the surface ────────────────────────────
  if (items.length === 0) {
    return (
      <div className="h-full overflow-y-auto animate-fade-in">
        {wizardSub ? (
          <>
            <WizardView
              subsection={wizardSub}
              projectId={projectId}
              phase={phase}
              phaseData={null}
              templateConfig={templateConfig}
            />
            <div className="pb-10 -mt-2 text-center">
              <button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4 disabled:opacity-40"
              >
                o empezá a mano con una escena vacía
              </button>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <p className="text-sm text-muted-foreground">Todavía no hay escenas.</p>
            <button
              onClick={() => createMutation.mutate()}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium bg-primary text-primary-foreground rounded-lg hover:bg-amber-600 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" /> Agregar escena
            </button>
          </div>
        )}
      </div>
    );
  }

  const renderField = (field: any) => {
    const isFilling = fillingKey === field.key;
    return (
      <div key={field.key} className="group/field relative">
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <FieldRenderer field={field} value={formData[field.key] || ''} onChange={handleFieldChange} />
          </div>
          <button
            onClick={() => handleAutofill(field.key)}
            disabled={isFilling}
            title="Autofill with AI"
            className="mt-6 p-1.5 rounded-md text-muted-foreground/50 hover:text-amber-400 hover:bg-amber-500/10 transition-colors opacity-0 group-hover/field:opacity-100 disabled:opacity-100 flex-shrink-0"
          >
            {isFilling ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
            ) : (
              <Wand2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-full overflow-hidden animate-fade-in">
      {/* Master: scene list */}
      <div className="w-72 xl:w-80 border-r border-border flex flex-col flex-shrink-0 bg-card/20">
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div>
            <h2 className="font-display text-sm font-semibold text-foreground">{subsection.name}</h2>
            <span className="text-[11px] text-muted-foreground font-mono">{items.length} {items.length === 1 ? 'escena' : 'escenas'}</span>
          </div>
          <div className="flex items-center gap-1">
            {wizardSub && (
              <button
                onClick={() => setShowWizard((v) => !v)}
                title={showWizard ? 'Cerrar el generador' : 'Generar escenas con IA'}
                className={`p-1.5 rounded-lg border transition-colors ${
                  showWizard
                    ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                    : 'border-border text-muted-foreground hover:text-amber-400 hover:border-amber-500/30'
                }`}
              >
                <Wand2 className="h-3.5 w-3.5" />
              </button>
            )}
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              title="Agregar escena"
              className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {items.map((item, index) => {
            const summary =
              (item.content as Record<string, string>).summary || `Escena ${index + 1}`;
            const status = item.status || 'draft';
            const isSelected = item.id === selectedId && !showWizard;

            return (
              <div
                key={item.id}
                draggable={listConfig?.sortable !== false}
                onDragStart={() => setDraggedIndex(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={() => setDraggedIndex(null)}
                onClick={() => selectItem(item)}
                className={`
                  group flex items-center gap-2 px-2.5 py-2.5 rounded-lg border cursor-pointer transition-all duration-150
                  ${isSelected
                    ? 'border-amber-500/25 bg-amber-500/5'
                    : 'border-transparent hover:bg-card hover:border-border'}
                  ${draggedIndex === index ? 'opacity-40 scale-[0.98]' : ''}
                `}
              >
                {listConfig?.sortable !== false && (
                  <GripVertical className="h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-muted-foreground/60 cursor-grab flex-shrink-0" />
                )}
                <span className="text-[11px] text-muted-foreground font-mono w-5 text-right flex-shrink-0">{index + 1}</span>
                <span className={`flex-1 text-xs leading-snug line-clamp-2 ${isSelected ? 'text-amber-100' : 'text-foreground'}`}>
                  {summary}
                </span>
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0 ${STATUS_STYLES[status] || STATUS_STYLES.draft}`}>
                  {status}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('¿Borrar esta escena?')) deleteMutation.mutate(item.id);
                  }}
                  className="p-0.5 text-transparent group-hover:text-muted-foreground hover:!text-destructive transition-colors rounded flex-shrink-0"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail: wizard panel or per-scene editor */}
      <div className="flex-1 overflow-y-auto">
        {showWizard && wizardSub ? (
          <div className="relative">
            <button
              onClick={() => setShowWizard(false)}
              title="Cerrar"
              className="absolute top-4 right-4 z-10 p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
            <WizardView
              subsection={wizardSub}
              projectId={projectId}
              phase={phase}
              phaseData={null}
              templateConfig={templateConfig}
            />
          </div>
        ) : selectedId ? (
          <div className="p-8 max-w-3xl mx-auto">
            {/* Header: title + prev/next */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl font-semibold text-foreground truncate pr-4">
                {formData.summary || `Escena ${selectedIndex + 1}`}
              </h2>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => selectedIndex > 0 && selectItem(items[selectedIndex - 1])}
                  disabled={selectedIndex <= 0}
                  className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-muted-foreground font-mono min-w-[4rem] text-center">
                  {selectedIndex + 1} / {items.length}
                </span>
                <button
                  onClick={() => selectedIndex < items.length - 1 && selectItem(items[selectedIndex + 1])}
                  disabled={selectedIndex >= items.length - 1}
                  className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Fields */}
            {layout === 'two_column' ? (
              <div className="grid grid-cols-2 gap-5">
                {fields.map((field) => (
                  <div key={field.key} className={field.full_width ? 'col-span-full' : ''}>
                    {renderField(field)}
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-5">{fields.map((field) => renderField(field))}</div>
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
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground">Elegí una escena de la lista.</p>
          </div>
        )}
      </div>
    </div>
  );
}
