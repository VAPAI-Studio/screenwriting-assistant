import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, ERROR_MESSAGES } from '../../lib/constants';
import { Button } from '../UI/Button';
import { ProjectCard } from './ProjectCard';
import { CreateProjectModal } from './CreateProjectModal';

export function ProjectList() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: projects, isLoading, isError, error } = useQuery({
    queryKey: [QUERY_KEYS.PROJECTS],
    queryFn: api.getProjects
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS] });
    },
  });

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this project? This cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-3 animate-fade-up">
          <Loader2 className="h-6 w-6 animate-spin text-amber-500/60" />
          <span className="text-sm text-muted-foreground">Loading projects...</span>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center animate-fade-in">
        <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
          <span className="text-destructive text-lg">!</span>
        </div>
        <p className="text-foreground font-medium mb-1">{ERROR_MESSAGES.GENERIC}</p>
        <p className="text-sm text-muted-foreground mb-5 max-w-sm">
          {error instanceof Error ? error.message : ERROR_MESSAGES.NETWORK}
        </p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-10 animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between mb-10">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
            Projects
          </h1>
          <p className="mt-2 text-muted-foreground">
            Your screenwriting workspace
          </p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Project
        </Button>
      </div>

      {projects?.length === 0 ? (
        <div className="text-center py-20 animate-fade-up">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/5 border border-amber-500/10 mb-6">
            <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7 text-amber-500/50" stroke="currentColor" strokeWidth="1.5">
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3 className="font-display text-xl font-semibold mb-2">Start your first screenplay</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Choose a template to guide your creative process with AI-powered tools
          </p>
          <Button onClick={() => setIsCreateModalOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Create Project
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects?.map((project: any, index: number) => {
            const isTemplate = !!(project as any).template;
            const href = isTemplate
              ? `/projects/${project.id}/${(project as any).current_phase || 'idea'}`
              : `/projects/${project.id}`;
            return (
              <Link
                key={project.id}
                to={href}
                className="animate-fade-up"
                style={{ animationDelay: `${index * 60}ms`, animationFillMode: 'both' }}
              >
                <ProjectCard project={project} onDelete={handleDelete} />
              </Link>
            );
          })}
        </div>
      )}

      <CreateProjectModal
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
      />
    </div>
  );
}
