// frontend/src/components/Storyboard/StoryboardView.tsx

import { useEffect } from 'react';
import { Film } from 'lucide-react';

interface StoryboardViewProps {
  projectId: string;
}

export function StoryboardView({ projectId: _projectId }: StoryboardViewProps) {
  // Apply storyboard CSS theme — remove on unmount
  useEffect(() => {
    document.documentElement.classList.add('storyboard-mode');
    return () => {
      document.documentElement.classList.remove('storyboard-mode');
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[60vh] gap-4 text-muted-foreground">
      <Film className="h-12 w-12 opacity-30" />
      <p className="text-lg font-medium">Storyboard coming soon</p>
      <p className="text-sm opacity-60">Shot frames and visual planning will appear here.</p>
    </div>
  );
}
