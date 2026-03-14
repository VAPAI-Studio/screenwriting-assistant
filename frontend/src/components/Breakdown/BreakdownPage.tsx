import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, ROUTES, BREAKDOWN_CATEGORIES } from '../../lib/constants';
import { PhaseNavigation } from '../Workspace/PhaseNavigation';
import { StalenessBar } from './StalenessBar';
import { CategoryTabs } from './CategoryTabs';

export function BreakdownPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useQuery<any>({
    queryKey: QUERY_KEYS.PROJECT_V2(projectId!),
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  const { data: templateConfig } = useQuery({
    queryKey: ['template', project?.template],
    queryFn: () => api.getTemplate(project!.template!),
    enabled: !!project?.template,
  });

  const { data: summary } = useQuery({
    queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId!),
    queryFn: () => api.getBreakdownSummary(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  const extractMutation = useMutation({
    mutationFn: () => api.triggerBreakdownExtraction(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId!) });
      BREAKDOWN_CATEGORIES.forEach(cat =>
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId!, cat.value) })
      );
    },
  });

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      <PhaseNavigation
        phases={templateConfig?.phases ?? []}
        currentPhase=""
        onPhaseChange={(phase) => navigate(ROUTES.PROJECT_WORKSPACE(projectId!, phase))}
        projectTitle={project?.title}
        onBreakdownClick={() => { /* already on breakdown page */ }}
        isBreakdownActive={true}
      />

      {summary?.is_stale && summary.total_elements > 0 && (
        <StalenessBar extractMutation={extractMutation} />
      )}

      <CategoryTabs
        projectId={projectId!}
        summary={summary}
        extractMutation={extractMutation}
      />
    </div>
  );
}
