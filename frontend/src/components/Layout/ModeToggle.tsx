import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ChevronDown, PenLine, Clapperboard } from 'lucide-react';
import { ROUTES } from '../../lib/constants';

export function ModeToggle() {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();

  // Only render when inside a project route
  if (!projectId) return null;

  const isBreakdown = location.pathname.endsWith('/breakdown');
  const currentMode = isBreakdown ? 'breakdown' : 'screenwriting';

  const handleSelect = (mode: 'screenwriting' | 'breakdown') => {
    if (mode === 'breakdown') {
      navigate(ROUTES.PROJECT_BREAKDOWN(projectId));
    } else {
      navigate(ROUTES.PROJECT(projectId));
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
            bg-muted/40 hover:bg-muted/70 text-foreground transition-colors"
        >
          {currentMode === 'screenwriting'
            ? <PenLine className="h-3.5 w-3.5" />
            : <Clapperboard className="h-3.5 w-3.5" />}
          <span>
            {currentMode === 'screenwriting' ? 'Screenwriting' : 'Script Breakdown'}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-50 min-w-[190px] rounded-lg border border-border bg-card shadow-lg p-1"
          sideOffset={4}
        >
          <DropdownMenu.Item
            onSelect={() => handleSelect('screenwriting')}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer
              hover:bg-muted/60 text-foreground outline-none"
          >
            <PenLine className="h-3.5 w-3.5" />
            <span>Screenwriting</span>
            {currentMode === 'screenwriting' && (
              <span className="ml-auto text-xs" style={{ color: 'hsl(var(--accent))' }}>Active</span>
            )}
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={() => handleSelect('breakdown')}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer
              hover:bg-muted/60 text-foreground outline-none"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span>Script Breakdown</span>
            {currentMode === 'breakdown' && (
              <span className="ml-auto text-xs" style={{ color: 'hsl(var(--accent))' }}>Active</span>
            )}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
