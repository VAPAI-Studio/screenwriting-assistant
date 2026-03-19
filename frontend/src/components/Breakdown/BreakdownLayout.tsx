import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { FileText, MessageSquare } from 'lucide-react';
import { STORAGE_KEYS } from '../../lib/constants';
import { BreakdownPanel } from './BreakdownPanel';
import { ShotlistPanel } from './ShotlistPanel';
import { ScriptReadView } from './ScriptReadView';

const MIN_PANEL_WIDTH = 200;

function readStoredWidth(key: string, fallbackPct: number): number {
  const stored = localStorage.getItem(key);
  if (stored) {
    const parsed = parseInt(stored, 10);
    const max = Math.floor(window.innerWidth * 0.45);
    if (!isNaN(parsed) && parsed >= MIN_PANEL_WIDTH && parsed <= max) return parsed;
  }
  return Math.floor(window.innerWidth * fallbackPct);
}

function readStoredBool(key: string, fallback: boolean): boolean {
  const stored = localStorage.getItem(key);
  if (stored === 'true') return true;
  if (stored === 'false') return false;
  return fallback;
}

export function BreakdownLayout() {
  const { projectId } = useParams<{ projectId: string }>();

  // Mode class lifecycle — MUST clean up on unmount
  useEffect(() => {
    document.documentElement.classList.add('breakdown-mode');
    return () => {
      document.documentElement.classList.remove('breakdown-mode');
    };
  }, []);

  // Panel state
  const [leftWidth, setLeftWidth] = useState(() =>
    readStoredWidth(STORAGE_KEYS.BREAKDOWN_LEFT_WIDTH, 0.25)
  );
  const [rightWidth, setRightWidth] = useState(() =>
    readStoredWidth(STORAGE_KEYS.BREAKDOWN_RIGHT_WIDTH, 0.25)
  );
  const [leftCollapsed, setLeftCollapsed] = useState(() =>
    readStoredBool(STORAGE_KEYS.BREAKDOWN_LEFT_COLLAPSED, false)
  );
  const [rightCollapsed, setRightCollapsed] = useState(() =>
    readStoredBool(STORAGE_KEYS.BREAKDOWN_RIGHT_COLLAPSED, false)
  );

  // Drag refs
  const isDraggingLeft = useRef(false);
  const isDraggingRight = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const latestLeftWidth = useRef(leftWidth);
  const latestRightWidth = useRef(rightWidth);

  useEffect(() => { latestLeftWidth.current = leftWidth; }, [leftWidth]);
  useEffect(() => { latestRightWidth.current = rightWidth; }, [rightWidth]);

  // Drag handlers
  const handleLeftDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingLeft.current = true;
    startX.current = e.clientX;
    startWidth.current = latestLeftWidth.current;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const handleRightDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRight.current = true;
    startX.current = e.clientX;
    startWidth.current = latestRightWidth.current;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const maxWidth = Math.floor(window.innerWidth * 0.45);

    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingLeft.current) {
        // Left panel: dragging right increases width
        const delta = e.clientX - startX.current;
        const newWidth = Math.min(maxWidth, Math.max(MIN_PANEL_WIDTH, startWidth.current + delta));
        setLeftWidth(newWidth);
      } else if (isDraggingRight.current) {
        // Right panel: dragging left increases width (matches existing ResizablePanel.tsx)
        const delta = startX.current - e.clientX;
        const newWidth = Math.min(maxWidth, Math.max(MIN_PANEL_WIDTH, startWidth.current + delta));
        setRightWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      if (isDraggingLeft.current) {
        isDraggingLeft.current = false;
        localStorage.setItem(STORAGE_KEYS.BREAKDOWN_LEFT_WIDTH, String(latestLeftWidth.current));
      } else if (isDraggingRight.current) {
        isDraggingRight.current = false;
        localStorage.setItem(STORAGE_KEYS.BREAKDOWN_RIGHT_WIDTH, String(latestRightWidth.current));
      }
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const toggleLeft = useCallback(() => {
    setLeftCollapsed(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEYS.BREAKDOWN_LEFT_COLLAPSED, String(next));
      return next;
    });
  }, []);

  const toggleRight = useCallback(() => {
    setRightCollapsed(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEYS.BREAKDOWN_RIGHT_COLLAPSED, String(next));
      return next;
    });
  }, []);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">

      {/* Left panel */}
      <BreakdownPanel
        title="Script / Assets"
        side="left"
        collapsed={leftCollapsed}
        onToggleCollapse={toggleLeft}
        style={{ width: leftWidth, borderRight: '1px solid hsl(var(--border))' }}
      >
        {projectId ? (
          <ScriptReadView projectId={projectId} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 px-6 text-center">
            <FileText className="h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm font-medium text-muted-foreground">No project selected</p>
          </div>
        )}
      </BreakdownPanel>

      {/* Left drag handle */}
      {!leftCollapsed && (
        <div
          onMouseDown={handleLeftDragStart}
          className="w-1 flex-shrink-0 cursor-col-resize z-10 hover:bg-primary/30 transition-colors duration-150 bg-transparent"
          style={{ borderRight: '1px solid hsl(var(--border))' }}
        />
      )}

      {/* Center panel — flex:1, fills remaining space */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <div className="flex items-center justify-between px-3 py-2 flex-shrink-0"
          style={{ borderBottom: '1px solid hsl(var(--border))' }}>
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Shotlist
          </span>
        </div>
        <ShotlistPanel />
      </div>

      {/* Right drag handle */}
      {!rightCollapsed && (
        <div
          onMouseDown={handleRightDragStart}
          className="w-1 flex-shrink-0 cursor-col-resize z-10 hover:bg-primary/30 transition-colors duration-150 bg-transparent"
          style={{ borderLeft: '1px solid hsl(var(--border))' }}
        />
      )}

      {/* Right panel */}
      <BreakdownPanel
        title="AI Chat"
        side="right"
        collapsed={rightCollapsed}
        onToggleCollapse={toggleRight}
        style={{ width: rightWidth, borderLeft: '1px solid hsl(var(--border))' }}
      >
        <div className="flex flex-col items-center justify-center h-full gap-3 px-6 text-center">
          <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm font-medium text-muted-foreground">AI Chat</p>
          <p className="text-xs text-muted-foreground/60">Available in Phase 24</p>
        </div>
      </BreakdownPanel>

    </div>
  );
}
