import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Network } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import { Agent, AgentType, PipelineMapEntry } from '../../types';
import type { TemplateConfig } from '../../types/template';

// ============================================================
// Internal tree types (not exported)
// ============================================================

interface TreePhase {
  phase: string;
  phaseName: string;
  subsections: TreeSubsection[];
}

interface TreeSubsection {
  key: string;
  name: string;
  agents: TreeAgent[];
}

interface TreeAgent {
  agentId: string;
  name: string;
  color: string;
  icon: string;
  agentType: AgentType;
  confidence: number;
  isActive: boolean;
}

// ============================================================
// Pure function: group flat entries into tree hierarchy
// ============================================================

function buildTreeData(
  entries: PipelineMapEntry[],
  agents: Agent[],
  templateConfig: TemplateConfig,
): TreePhase[] {
  const agentMap = new Map(agents.map(a => [a.id, a]));
  const grouped = new Map<string, Map<string, PipelineMapEntry[]>>();

  for (const entry of entries) {
    if (!grouped.has(entry.phase)) grouped.set(entry.phase, new Map());
    const phaseMap = grouped.get(entry.phase)!;
    if (!phaseMap.has(entry.subsection_key)) phaseMap.set(entry.subsection_key, []);
    phaseMap.get(entry.subsection_key)!.push(entry);
  }

  return templateConfig.phases
    .filter(p => grouped.has(p.id))
    .map(phase => ({
      phase: phase.id,
      phaseName: phase.name,
      subsections: phase.subsections
        .filter(s => grouped.get(phase.id)?.has(s.key))
        .map(sub => ({
          key: sub.key,
          name: sub.name,
          agents: (grouped.get(phase.id)?.get(sub.key) || [])
            .map(entry => {
              const agent = agentMap.get(entry.agent_id);
              return agent ? {
                agentId: entry.agent_id,
                name: agent.name,
                color: agent.color,
                icon: agent.icon,
                agentType: agent.agent_type,
                confidence: entry.confidence,
                isActive: agent.is_active,
              } : null;
            })
            .filter(Boolean) as TreeAgent[],
        })),
    }));
}

// ============================================================
// Main component
// ============================================================

export function AgentPipelineTree() {
  const queryClient = useQueryClient();

  // Data fetching (3 queries)
  const pipelineQuery = useQuery({
    queryKey: [QUERY_KEYS.PIPELINE_MAP],
    queryFn: () => api.getPipelineMap(),
  });

  const agentsQuery = useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => api.getAgents(),
  });

  const templateQuery = useQuery({
    queryKey: QUERY_KEYS.TEMPLATE('short_movie'),
    queryFn: () => api.getTemplate('short_movie'),
  });

  // Collapsible state -- all collapsed by default
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());

  const togglePhase = (phaseId: string) => {
    setExpandedPhases(prev => {
      const next = new Set(prev);
      if (next.has(phaseId)) next.delete(phaseId);
      else next.add(phaseId);
      return next;
    });
  };

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: ({ agentId, isActive }: { agentId: string; isActive: boolean }) =>
      api.updateAgent(agentId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.AGENTS] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PIPELINE_MAP] });
    },
  });

  const isLoading = pipelineQuery.isLoading || agentsQuery.isLoading || templateQuery.isLoading;

  const treeData = useMemo(() => {
    if (!pipelineQuery.data || !agentsQuery.data || !templateQuery.data) return [];
    return buildTreeData(pipelineQuery.data.entries, agentsQuery.data, templateQuery.data);
  }, [pipelineQuery.data, agentsQuery.data, templateQuery.data]);

  // Refs for Task 2 (full tree rendering with collapse/expand and toggle badges)
  void expandedPhases;
  void togglePhase;
  void toggleMutation;

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Network className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold text-foreground">Pipeline Map</h3>
      </div>
      {/* Scaffold -- Task 2 replaces this with full tree rendering */}
      {isLoading && <div className="animate-pulse bg-muted/40 rounded h-6 w-3/4" />}
      {!isLoading && treeData.length === 0 && (
        <div className="text-center py-6 text-muted-foreground">
          <Network className="h-7 w-7 mx-auto mb-2 opacity-30" />
          <p className="text-xs">Create agents to see how they map to your pipeline</p>
        </div>
      )}
      {treeData.map(phase => (
        <div key={phase.phase} className="text-sm">{phase.phaseName}: {phase.subsections.length} subsection(s)</div>
      ))}
    </div>
  );
}
