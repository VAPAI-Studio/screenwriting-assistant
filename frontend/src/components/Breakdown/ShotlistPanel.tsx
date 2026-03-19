import { useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import { SceneGroup } from './SceneGroup';
import { ShotlistEmptyState } from './ShotlistEmptyState';
import { AddShotButton } from './AddShotButton';
import { DeleteShotButton } from './DeleteShotButton';
import { ReorderControls } from './ReorderControls';
import type { SceneGroupData } from './SceneGroup';
import type { Shot, ShotFields, ShotCreate } from '../../types';

// ============================================================
// Scene grouping — pure function
// ============================================================

function groupShotsByScene(shots: Shot[]): SceneGroupData[] {
  const groups = new Map<string, Shot[]>();
  const groupOrder: string[] = [];

  for (const shot of shots) {
    const key = shot.scene_item_id ?? 'unassigned';
    if (!groups.has(key)) {
      groups.set(key, []);
      groupOrder.push(key);
    }
    groups.get(key)!.push(shot);
  }

  // Move unassigned to end if present
  const unassignedIdx = groupOrder.indexOf('unassigned');
  if (unassignedIdx >= 0 && unassignedIdx < groupOrder.length - 1) {
    groupOrder.splice(unassignedIdx, 1);
    groupOrder.push('unassigned');
  }

  return groupOrder.map((key, index) => ({
    sceneItemId: key === 'unassigned' ? null : key,
    sceneTitle: key === 'unassigned' ? 'Unassigned Shots' : `Scene ${index + 1}`,
    shots: groups.get(key)!,
  }));
}

// ============================================================
// Column header grid template (shared with ShotRow)
// ============================================================

const GRID_TEMPLATE = '48px repeat(2, minmax(80px, 1fr)) minmax(80px, 1fr) repeat(2, minmax(120px, 2fr)) 80px';

const COLUMN_HEADERS = ['#', 'Size', 'Angle', 'Movement', 'Description', 'Action', ''];

// ============================================================
// ShotlistPanel
// ============================================================

export function ShotlistPanel() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  // Fetch shots
  const {
    data: shots,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.SHOTS(projectId!),
    queryFn: () => api.listShots(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // Update mutation with optimistic update
  const updateMutation = useMutation({
    mutationFn: ({ shotId, data }: { shotId: string; data: { fields: ShotFields } }) =>
      api.updateShot(projectId!, shotId, data),
    onMutate: async ({ shotId, data }) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
      const previous = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId!));
      queryClient.setQueryData(
        QUERY_KEYS.SHOTS(projectId!),
        (old: Shot[] | undefined) =>
          (old ?? []).map(shot =>
            shot.id === shotId
              ? { ...shot, fields: { ...shot.fields, ...data.fields } }
              : shot
          )
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
    },
  });

  // Create mutation (optimistic)
  const createMutation = useMutation({
    mutationFn: (data: ShotCreate) => api.createShot(projectId!, data),
    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
      const previous = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId!));
      const optimisticShot: Shot = {
        id: `temp-${Date.now()}`,
        project_id: projectId!,
        scene_item_id: data.scene_item_id ?? null,
        shot_number: data.shot_number ?? 1,
        script_text: data.script_text ?? '',
        script_range: {},
        fields: (data.fields ?? {}) as ShotFields,
        sort_order: data.sort_order ?? 0,
        source: (data.source ?? 'user') as 'user' | 'ai',
        created_at: new Date().toISOString(),
        updated_at: null,
      };
      queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), (old: Shot[] | undefined) =>
        [...(old ?? []), optimisticShot]
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
    },
  });

  // Delete mutation (optimistic)
  const deleteMutation = useMutation({
    mutationFn: (shotId: string) => api.deleteShot(projectId!, shotId),
    onMutate: async (shotId) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
      const previous = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId!));
      queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), (old: Shot[] | undefined) =>
        (old ?? []).filter(s => s.id !== shotId)
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
    },
  });

  // Reorder mutation (optimistic)
  const reorderMutation = useMutation({
    mutationFn: (items: Array<{ id: string; sort_order: number }>) =>
      api.reorderShots(projectId!, items),
    onMutate: async (items) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
      const previous = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId!));
      const orderMap = new Map(items.map(i => [i.id, i.sort_order]));
      queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), (old: Shot[] | undefined) => {
        if (!old) return old;
        return old
          .map(s => orderMap.has(s.id) ? { ...s, sort_order: orderMap.get(s.id)! } : s)
          .sort((a, b) => {
            if (a.scene_item_id !== b.scene_item_id) {
              if (a.scene_item_id === null) return 1;
              if (b.scene_item_id === null) return -1;
              return (a.scene_item_id ?? '').localeCompare(b.scene_item_id ?? '');
            }
            return a.sort_order - b.sort_order;
          });
      });
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId!), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
    },
  });

  // Handler passed to SceneGroup -> ShotRow -> InlineEditCell
  const handleUpdateField = useCallback(
    (shotId: string, fieldKey: string, newValue: string, existingFields: ShotFields) => {
      updateMutation.mutate({
        shotId,
        data: { fields: { ...existingFields, [fieldKey]: newValue } },
      });
    },
    [updateMutation]
  );

  // Create shot handler — auto-calculates shot_number and sort_order
  const handleCreateShot = useCallback((sceneItemId: string | null) => {
    const groupShots = (shots ?? []).filter(s =>
      sceneItemId === null
        ? s.scene_item_id === null
        : s.scene_item_id === sceneItemId
    );
    const maxNumber = groupShots.reduce((max, s) => Math.max(max, s.shot_number), 0);
    const maxSortOrder = groupShots.reduce((max, s) => Math.max(max, s.sort_order), -1);

    createMutation.mutate({
      scene_item_id: sceneItemId,
      shot_number: maxNumber + 1,
      sort_order: maxSortOrder + 1,
      source: 'user',
    });
  }, [shots, createMutation]);

  // Move shot handler — swaps sort_order with adjacent shot
  const handleMoveShot = useCallback((shot: Shot, direction: 'up' | 'down', groupShots: Shot[]) => {
    const sorted = [...groupShots].sort((a, b) => a.sort_order - b.sort_order);
    const idx = sorted.findIndex(s => s.id === shot.id);

    if (direction === 'up' && idx <= 0) return;
    if (direction === 'down' && idx >= sorted.length - 1) return;

    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    const other = sorted[swapIdx];

    reorderMutation.mutate([
      { id: shot.id, sort_order: other.sort_order },
      { id: other.id, sort_order: shot.sort_order },
    ]);
  }, [reorderMutation]);

  // ---- Loading state ----
  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-4 py-3 space-y-3">
          <div className="h-9 w-48 rounded bg-muted/20 animate-pulse" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 rounded bg-muted/20 animate-pulse" />
          ))}
          <div className="h-9 w-48 rounded bg-muted/20 animate-pulse" />
          {[...Array(5)].map((_, i) => (
            <div key={`b-${i}`} className="h-10 rounded bg-muted/20 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ---- Error state ----
  if (isError) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden p-4">
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 flex items-start gap-3">
          <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-foreground">
              Failed to load shots. Check your connection and try again.
            </p>
            {error instanceof Error && (
              <p className="text-xs text-muted-foreground mt-1">{error.message}</p>
            )}
            <button
              onClick={() => refetch()}
              className="text-sm text-primary hover:underline mt-2"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ---- Empty state ----
  if (!shots || shots.length === 0) {
    return (
      <ShotlistEmptyState
        onAddShot={() => handleCreateShot(null)}
        isPending={createMutation.isPending}
      />
    );
  }

  // ---- Data state ----
  const groups = groupShotsByScene(shots);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Column headers — sticky */}
      <div
        className="grid sticky top-0 bg-background z-10"
        style={{
          gridTemplateColumns: GRID_TEMPLATE,
          borderBottom: '1px solid hsl(var(--border))',
        }}
      >
        {COLUMN_HEADERS.map((header, i) => (
          <div
            key={i}
            className={`px-2 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider
              ${i > 0 ? 'border-l border-border/50' : ''}
              ${i === 0 ? 'text-center' : ''}`}
          >
            {header}
          </div>
        ))}
      </div>

      {/* Scrollable scene groups */}
      <div className="flex-1 overflow-auto">
        {groups.map((group, idx) => (
          <SceneGroup
            key={group.sceneItemId ?? 'unassigned'}
            group={group}
            groupIndex={idx}
            onUpdateField={handleUpdateField}
            renderActionCell={(shot, groupShots) => {
              const sorted = [...groupShots].sort((a, b) => a.sort_order - b.sort_order);
              const sortedIdx = sorted.findIndex(s => s.id === shot.id);
              return (
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <ReorderControls
                    onMoveUp={() => handleMoveShot(shot, 'up', groupShots)}
                    onMoveDown={() => handleMoveShot(shot, 'down', groupShots)}
                    isFirst={sortedIdx === 0}
                    isLast={sortedIdx === sorted.length - 1}
                    isPending={reorderMutation.isPending}
                  />
                  <DeleteShotButton
                    onDelete={() => deleteMutation.mutate(shot.id)}
                    isPending={deleteMutation.isPending}
                  />
                </div>
              );
            }}
            renderAddButton={(sceneItemId) => (
              <AddShotButton
                onClick={() => handleCreateShot(sceneItemId)}
                isPending={createMutation.isPending}
              />
            )}
          />
        ))}
      </div>
    </div>
  );
}
