// frontend/src/App.tsx

import { BrowserRouter as Router, Routes, Route, useParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout/Layout';
import { ProjectList } from './components/Projects/ProjectList';
import { Editor } from './components/Editor/Editor';
import { BookManager } from './components/Books/BookManager';
import { ProjectWorkspace } from './components/Workspace/ProjectWorkspace';
import { SnippetManager } from './components/Snippets/SnippetManager';
// BreakdownPage retained for Phase 23 assets panel integration
// import { BreakdownPage } from './components/Breakdown/BreakdownPage';
import { BreakdownLayout } from './components/Breakdown/BreakdownLayout';
import { StoryboardView } from './components/Storyboard/StoryboardView';
import { ElementDetailPage } from './components/Breakdown/ElementDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1
    }
  }
});

function StoryboardViewRoute() {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return <StoryboardView projectId={projectId} />;
}

function ElementDetailRoute() {
  const { projectId, elementId } = useParams<{ projectId: string; elementId: string }>();
  if (!projectId || !elementId) return null;
  return <ElementDetailPage projectId={projectId} elementId={elementId} />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<ProjectList />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/:projectId" element={<Editor />} />
            <Route path="/projects/:projectId/breakdown/elements/:elementId" element={<ElementDetailRoute />} />
            <Route path="/projects/:projectId/breakdown" element={<BreakdownLayout />} />
            <Route path="/projects/:projectId/storyboard" element={<StoryboardViewRoute />} />
            <Route path="/projects/:projectId/:phase" element={<ProjectWorkspace />} />
            <Route path="/projects/:projectId/:phase/:subsectionKey" element={<ProjectWorkspace />} />
            <Route path="/projects/:projectId/:phase/:subsectionKey/:itemId" element={<ProjectWorkspace />} />
            <Route path="/books" element={<BookManager />} />
            <Route path="/snippets" element={<SnippetManager />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
