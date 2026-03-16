import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import Navbar from '@/components/layout/Navbar';
import ProtectedRoute from '@/components/ProtectedRoute';

// Pages
import Home from '@/pages/Home';
import Login from '@/pages/Login';
import ProjectList from '@/pages/projects/ProjectList';
import ProjectDetail from '@/pages/projects/ProjectDetail';
import ProjectForm from '@/pages/projects/ProjectForm';
import DatasetList from '@/pages/datasets/DatasetList';
import DatasetDetail from '@/pages/datasets/DatasetDetail';
import PromptList from '@/pages/prompts/PromptList';
import PromptForm from '@/pages/prompts/PromptForm';
import PromptReview from '@/pages/prompts/PromptReview';
import MultiPromptCreate from '@/pages/prompts/MultiPromptCreate';
import UserPromptsList from '@/pages/prompts/UserPromptsList';
import UserDistributedDatasets from '@/pages/datasets/UserDistributedDatasets';
import TaskList from '@/pages/tasks/TaskList';
import HFSync from '@/pages/admin/HFSync';
import OpenRouterKey from '@/pages/settings/OpenRouterKey';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<Home />} />
      <Route path="/app/login" element={<Login />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/app/projects" element={<ProjectList />} />
        <Route path="/app/projects/new" element={<ProjectForm />} />
        <Route path="/app/projects/:id" element={<ProjectDetail />} />
        <Route path="/app/projects/:id/edit" element={<ProjectForm />} />
        <Route path="/app/projects/:id/tasks" element={<TaskList />} />
        <Route path="/app/projects/:projectId/datasets" element={<DatasetList />} />
        <Route path="/app/datasets/:id" element={<DatasetDetail />} />
        <Route path="/app/datasets/:datasetId/prompts" element={<PromptList />} />
        <Route path="/app/datasets/:datasetId/prompts/new" element={<PromptForm />} />
        <Route path="/app/datasets/:datasetId/prompts/new-bulk" element={<MultiPromptCreate />} />
        <Route path="/app/datasets/:datasetId/prompts/:id/edit" element={<PromptForm />} />
        <Route path="/app/datasets/:datasetId/prompts/:id/review" element={<PromptReview />} />
        <Route path="/app/my-prompts" element={<UserPromptsList />} />
        <Route path="/app/my-datasets" element={<UserDistributedDatasets />} />
        <Route path="/app/hf-sync" element={<HFSync />} />
        <Route path="/app/settings" element={<OpenRouterKey />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <div className="min-h-screen bg-background text-foreground">
              <Navbar />
              <AppRoutes />
            </div>
            <Toaster richColors position="top-right" />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
