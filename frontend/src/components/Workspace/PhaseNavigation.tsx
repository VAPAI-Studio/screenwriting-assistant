import { Lightbulb, BookOpen, Clapperboard, PenTool } from 'lucide-react';
import type { PhaseConfig } from '../../types/template';

const PHASE_ICONS: Record<string, typeof Lightbulb> = {
  idea: Lightbulb,
  story: BookOpen,
  scenes: Clapperboard,
  write: PenTool,
};

const PHASE_COLORS: Record<string, { active: string; dot: string }> = {
  idea: { active: 'text-violet-400 border-violet-400', dot: 'bg-violet-400' },
  story: { active: 'text-blue-400 border-blue-400', dot: 'bg-blue-400' },
  scenes: { active: 'text-amber-400 border-amber-400', dot: 'bg-amber-400' },
  write: { active: 'text-emerald-400 border-emerald-400', dot: 'bg-emerald-400' },
};

interface PhaseNavigationProps {
  phases: PhaseConfig[];
  currentPhase: string;
  onPhaseChange: (phaseId: string) => void;
  projectTitle?: string;
}

export function PhaseNavigation({ phases, currentPhase, onPhaseChange, projectTitle }: PhaseNavigationProps) {
  return (
    <div className="border-b border-border bg-card/50 backdrop-blur-sm flex-shrink-0">
      <div className="flex items-center px-5 gap-6">
        {/* Project title */}
        {projectTitle && (
          <span className="text-sm font-medium text-muted-foreground truncate max-w-[180px] py-3 border-r border-border pr-6">
            {projectTitle}
          </span>
        )}

        {/* Phase tabs */}
        <nav className="flex items-center gap-0.5" aria-label="Phase Navigation">
          {phases.map((phase, index) => {
            const isActive = phase.id === currentPhase;
            const isPast = phases.findIndex(p => p.id === currentPhase) > index;
            const Icon = PHASE_ICONS[phase.id] || BookOpen;
            const colors = PHASE_COLORS[phase.id] || PHASE_COLORS.idea;

            return (
              <div key={phase.id} className="flex items-center">
                <button
                  onClick={() => onPhaseChange(phase.id)}
                  className={`
                    relative flex items-center gap-2 px-4 py-3 text-xs font-semibold uppercase tracking-wider
                    transition-all duration-200 border-b-2 -mb-px
                    ${isActive
                      ? colors.active
                      : isPast
                        ? 'border-transparent text-muted-foreground/70 hover:text-foreground/80'
                        : 'border-transparent text-muted-foreground/40 hover:text-muted-foreground/70'
                    }
                  `}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{phase.name}</span>
                </button>

                {/* Connector line between phases */}
                {index < phases.length - 1 && (
                  <div className="flex items-center px-1">
                    <div className={`w-4 h-px ${isPast ? 'bg-muted-foreground/30' : 'bg-border'}`} />
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
