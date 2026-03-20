import { useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { api } from '../../lib/api';
import { BREAKDOWN_CATEGORIES, QUERY_KEYS } from '../../lib/constants';
import type { BreakdownElement } from '../../types';
import { AssetElementCard } from './AssetElementCard';

interface AssetsPanelProps {
  projectId: string;
}

export function AssetsPanel({ projectId }: AssetsPanelProps) {
  // Audio overlap prevention (MDIA-04)
  const stopCurrentAudioRef = useRef<(() => void) | null>(null);

  const handlePlaybackStart = useCallback((_mediaId: string, stopFn: () => void) => {
    // Stop any currently-playing audio before starting new one
    if (stopCurrentAudioRef.current) {
      stopCurrentAudioRef.current();
    }
    stopCurrentAudioRef.current = stopFn;
  }, []);

  const { data: allElements = [] } = useQuery<BreakdownElement[]>({
    queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId),
    queryFn: () => api.getBreakdownElements(projectId),
  });

  // Group elements by category, filter out empty categories
  const groupedCategories = BREAKDOWN_CATEGORIES
    .map(cat => ({
      ...cat,
      elements: allElements.filter(el => el.category === cat.value),
    }))
    .filter(cat => cat.elements.length > 0);

  // Empty state: no elements in any category
  if (groupedCategories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 px-6 text-center">
        <FileText className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-sm font-semibold text-foreground">No breakdown elements</p>
        <p className="text-xs text-muted-foreground">
          Run a script breakdown from Screenwriting mode to populate assets. Elements like
          characters, locations, and props will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full">
      {groupedCategories.map(cat => (
        <div key={cat.value}>
          {/* Sticky category header */}
          <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-2 border-b border-border bg-card/30">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {cat.label}
            </span>
            <span className="text-[10px] bg-muted/60 px-1.5 py-0.5 rounded-full tabular-nums text-muted-foreground">
              {cat.elements.length}
            </span>
          </div>
          {/* Element cards */}
          <div className="px-2 py-2 space-y-1.5">
            {cat.elements.map(element => (
              <AssetElementCard
                key={element.id}
                element={element}
                projectId={projectId}
                onPlaybackStart={handlePlaybackStart}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
