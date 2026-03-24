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
import { LoginPage } from './components/Auth/LoginPage';
import { RegisterPage } from './components/Auth/RegisterPage';
import { ProtectedRoute } from './components/Auth/ProtectedRoute';
import { ProfilePage } from './components/Settings/ProfilePage';
import { ShowDetail } from './components/Shows/ShowDetail';

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

function ShowDetailRoute() {
  const { showId } = useParams<{ showId: string }>();
  if (!showId) return null;
  return <ShowDetail showId={showId} />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            {/* Public routes -- NO ProtectedRoute wrapper */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected routes -- require authentication */}
            <Route path="/" element={<ProtectedRoute><ProjectList /></ProtectedRoute>} />
            <Route path="/projects" element={<ProtectedRoute><ProjectList /></ProtectedRoute>} />
            <Route path="/projects/:projectId" element={<ProtectedRoute><Editor /></ProtectedRoute>} />
            <Route path="/projects/:projectId/breakdown/elements/:elementId" element={<ProtectedRoute><ElementDetailRoute /></ProtectedRoute>} />
            <Route path="/projects/:projectId/breakdown" element={<ProtectedRoute><BreakdownLayout /></ProtectedRoute>} />
            <Route path="/projects/:projectId/storyboard" element={<ProtectedRoute><StoryboardViewRoute /></ProtectedRoute>} />
            <Route path="/projects/:projectId/:phase" element={<ProtectedRoute><ProjectWorkspace /></ProtectedRoute>} />
            <Route path="/projects/:projectId/:phase/:subsectionKey" element={<ProtectedRoute><ProjectWorkspace /></ProtectedRoute>} />
            <Route path="/projects/:projectId/:phase/:subsectionKey/:itemId" element={<ProtectedRoute><ProjectWorkspace /></ProtectedRoute>} />
            <Route path="/books" element={<ProtectedRoute><BookManager /></ProtectedRoute>} />
            <Route path="/snippets" element={<ProtectedRoute><SnippetManager /></ProtectedRoute>} />
            <Route path="/settings/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            <Route path="/shows/:showId" element={<ProtectedRoute><ShowDetailRoute /></ProtectedRoute>} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
