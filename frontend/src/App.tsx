// frontend/src/App.tsx

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout/Layout';
import { ProjectList } from './components/Projects/ProjectList';
import { Editor } from './components/Editor/Editor';
import { BookManager } from './components/Books/BookManager';
import { ProjectWorkspace } from './components/Workspace/ProjectWorkspace';
import { SnippetManager } from './components/Snippets/SnippetManager';
import { BreakdownPage } from './components/Breakdown/BreakdownPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1
    }
  }
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<ProjectList />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/:projectId" element={<Editor />} />
            <Route path="/projects/:projectId/breakdown" element={<BreakdownPage />} />
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
