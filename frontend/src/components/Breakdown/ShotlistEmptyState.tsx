import { List } from 'lucide-react';
import { Button } from '../UI/Button';

interface ShotlistEmptyStateProps {
  onAddShot: () => void;
  isPending: boolean;
  onGenerate?: () => void;
  isGenerating?: boolean;
  generateError?: string | null;
}

export function ShotlistEmptyState({ onAddShot, isPending }: ShotlistEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 animate-fade-in">
      <List className="h-10 w-10 text-muted-foreground/30" />
      <div className="text-center max-w-xs">
        <p className="text-sm font-semibold text-foreground">No shots yet</p>
        <p className="text-sm text-muted-foreground mt-1">
          Create your first shot to start building your shotlist.
        </p>
      </div>
      <Button
        onClick={onAddShot}
        disabled={isPending}
        className="mt-4"
      >
        Add First Shot
      </Button>
    </div>
  );
}
