import { ShotRow } from './ShotRow';
import type { Shot, ShotFields } from '../../types';

interface SceneGroupData {
  sceneItemId: string | null;
  sceneTitle: string;
  shots: Shot[];
}

interface SceneGroupProps {
  group: SceneGroupData;
  groupIndex: number;
  onUpdateField: (shotId: string, fieldKey: string, newValue: string, existingFields: ShotFields) => void;
  renderActionCell?: (shot: Shot, groupShots: Shot[]) => React.ReactNode;
  renderAddButton?: (sceneItemId: string | null) => React.ReactNode;
}

export function SceneGroup({ group, onUpdateField, renderActionCell, renderAddButton }: SceneGroupProps) {
  const shotCount = group.shots.length;
  const countLabel = shotCount === 1 ? '1 shot' : `${shotCount} shots`;

  return (
    <div>
      {/* Scene header */}
      <div className="flex items-center justify-between px-4 py-2 bg-card/60"
        style={{ borderBottom: '1px solid hsl(var(--border))' }}>
        <span className="text-[13px] font-semibold text-foreground">
          {group.sceneTitle}
        </span>
        <span className="text-xs text-muted-foreground">
          {countLabel}
        </span>
      </div>

      {/* Shot rows */}
      {group.shots.map(shot => (
        <div key={shot.id} style={{ borderBottom: '1px solid hsl(var(--border) / 0.5)' }}>
          <ShotRow
            shot={shot}
            onUpdateField={onUpdateField}
            actionCell={renderActionCell?.(shot, group.shots)}
          />
        </div>
      ))}

      {/* Add shot button slot (rendered by Plan 02) */}
      {renderAddButton?.(group.sceneItemId)}
    </div>
  );
}

export type { SceneGroupData };
