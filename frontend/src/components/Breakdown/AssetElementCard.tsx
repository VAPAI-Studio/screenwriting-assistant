import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import type { BreakdownElement } from '../../types';

interface AssetElementCardProps {
  element: BreakdownElement;
  projectId: string;
}

export function AssetElementCard({ element, projectId }: AssetElementCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Suppress unused-variable warning — projectId will be used in Plan 02 for media queries
  void projectId;

  return (
    <div className="rounded-lg border border-border/50 hover:border-border bg-card/40 hover:bg-card/60 transition-all">
      {/* Header row (always visible, clickable) */}
      <div
        className="flex items-center gap-2 px-4 py-3 cursor-pointer"
        onClick={() => setIsExpanded(prev => !prev)}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
        <span className="text-sm font-semibold text-foreground truncate flex-1">
          {element.name}
        </span>
        {/* Media count badge added in Plan 02 */}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 animate-accordion-down">
          {element.description && (
            <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
              {element.description}
            </p>
          )}
          {/* Media thumbnails, audio players, and upload zone added in Plan 02 */}
          <div className="text-xs text-muted-foreground/40 italic">Media display coming soon</div>
        </div>
      )}
    </div>
  );
}
