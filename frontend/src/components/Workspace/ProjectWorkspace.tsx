import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { PhaseNavigation } from './PhaseNavigation';
import { SubsectionSidebar } from './SubsectionSidebar';
import { ContentArea } from './ContentArea';
import { SidebarChat } from '../Shared/SidebarChat';
import type { PhaseConfig, SubsectionConfig } from '../../types/template';

export function ProjectWorkspace() {
  const { projectId, phase, subsectionKey, itemId } = useParams<{
    projectId: string;
    phase?: string;
    subsectionKey?: string;
    itemId?: string;
  }>();
  const navigate = useNavigate();

  const [selectedPhase, setSelectedPhase] = useState<string>(phase || 'idea');
  const [selectedSubsection, setSelectedSubsection] = useState<string>(subsectionKey || '');

  const { data: project, isLoading: projectLoading } = useQuery<any>({
    queryKey: ['project-v2', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  const { data: templateConfig, isLoading: templateLoading } = useQuery({
    queryKey: ['template', project?.template],
    queryFn: () => api.getTemplate(project!.template!),
    enabled: !!project?.template,
  });

  const currentPhase: PhaseConfig | undefined = templateConfig?.phases?.find(
    (p: PhaseConfig) => p.id === selectedPhase
  );

  const currentSubsection: SubsectionConfig | undefined = currentPhase?.subsections?.find(
    (s: SubsectionConfig) => s.key === selectedSubsection
  );

  useEffect(() => {
    if (currentPhase && currentPhase.subsections.length > 0 && !selectedSubsection) {
      setSelectedSubsection(currentPhase.subsections[0].key);
    }
  }, [currentPhase, selectedSubsection]);

  useEffect(() => {
    if (phase && phase !== selectedPhase) setSelectedPhase(phase);
    if (subsectionKey && subsectionKey !== selectedSubsection) setSelectedSubsection(subsectionKey);
  }, [phase, subsectionKey]);

  const handlePhaseChange = (phaseId: string) => {
    setSelectedPhase(phaseId);
    setSelectedSubsection('');
    navigate(`/projects/${projectId}/${phaseId}`);
  };

  const handleSubsectionChange = (key: string) => {
    setSelectedSubsection(key);
    navigate(`/projects/${projectId}/${selectedPhase}/${key}`);
  };

  if (projectLoading || templateLoading) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <div className="flex flex-col items-center gap-3 animate-fade-up">
          <Loader2 className="h-6 w-6 animate-spin text-amber-500/60" />
          <span className="text-sm text-muted-foreground">Loading workspace...</span>
        </div>
      </div>
    );
  }

  if (!project || !templateConfig) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <div className="text-center animate-fade-in">
          <p className="text-foreground font-medium mb-1">Project not found</p>
          <p className="text-sm text-muted-foreground">This project may have been deleted.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-56px)]">
      {/* Phase Navigation */}
      <PhaseNavigation
        phases={templateConfig.phases}
        currentPhase={selectedPhase}
        onPhaseChange={handlePhaseChange}
        projectTitle={project.title}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Subsection Sidebar */}
        {currentPhase && (
          <SubsectionSidebar
            subsections={currentPhase.subsections}
            currentSubsection={selectedSubsection}
            onSubsectionChange={handleSubsectionChange}
          />
        )}

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto bg-background">
          {currentSubsection && projectId ? (
            <ContentArea
              subsection={currentSubsection}
              projectId={projectId}
              phase={selectedPhase}
              templateConfig={templateConfig}
              itemId={itemId}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-muted-foreground text-sm">Select a section to get started</p>
            </div>
          )}
        </div>

        {/* Chat Sidebar — always visible */}
        {projectId && selectedSubsection && (
          <SidebarChat
            projectId={projectId}
            phase={selectedPhase}
            subsectionKey={selectedSubsection}
            contextItemId={itemId}
          />
        )}
      </div>
    </div>
  );
}
