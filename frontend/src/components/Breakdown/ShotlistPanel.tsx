import { useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import { SceneGroup } from './SceneGroup';
import type { SceneGroupData } from './SceneGroup';
import type { Shot, ShotFields } from '../../types';

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
      <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="text-sm font-semibold text-foreground">No shots yet</p>
        <p className="text-sm text-muted-foreground max-w-xs">
          Create your first shot to start building your shotlist.
        </p>
      </div>
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
          />
        ))}
      </div>
    </div>
  );
}
