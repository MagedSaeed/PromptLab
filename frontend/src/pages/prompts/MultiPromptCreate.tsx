import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import type { Project, Dataset } from '@/types';

interface GeneratedPrompt {
  id?: number;
  name: string;
  template: string;
  answer_choices: string;
  status: 'pending' | 'saved' | 'rejected';
}

export default function MultiPromptCreate() {
  const { projectId, datasetId } = useParams<{ projectId: string; datasetId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState(0);
  const [prompts, setPrompts] = useState<GeneratedPrompt[]>([]);
  const [generated, setGenerated] = useState(false);

  const { data: project } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/`)).data,
    enabled: !!projectId,
  });

  const { data: dataset } = useQuery<Dataset>({
    queryKey: ['dataset', datasetId],
    queryFn: async () => (await api.get(`/datasets/${datasetId}/`)).data,
    enabled: !!datasetId,
  });

  // Generate prompts
  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/datasets/${datasetId}/prompts/create-multiple/`);
      return res.data;
    },
    onSuccess: (data) => {
      const generated: GeneratedPrompt[] = (data.prompts || data || []).map(
        (p: { name: string; template: string; answer_choices?: string }) => ({
          name: p.name,
          template: p.template,
          answer_choices: p.answer_choices || '',
          status: 'pending' as const,
        })
      );
      setPrompts(generated);
      setGenerated(true);
      setActiveTab(0);
    },
  });

  // Save individual prompt
  const saveMutation = useMutation({
    mutationFn: async (index: number) => {
      const prompt = prompts[index];
      const res = await api.post(`/datasets/${datasetId}/prompts/save-generated/`, {
        name: prompt.name,
        template: prompt.template,
        answer_choices: prompt.answer_choices,
      });
      return { index, data: res.data };
    },
    onSuccess: ({ index }) => {
      setPrompts((prev) =>
        prev.map((p, i) => (i === index ? { ...p, status: 'saved' } : p))
      );
      queryClient.invalidateQueries({ queryKey: ['prompts', datasetId] });
      // Navigate to next pending tab
      const nextPending = prompts.findIndex((p, i) => i > index && p.status === 'pending');
      if (nextPending !== -1) {
        setActiveTab(nextPending);
      }
    },
  });

  // Reject individual prompt
  const rejectMutation = useMutation({
    mutationFn: async (index: number) => {
      const prompt = prompts[index];
      await api.post(`/datasets/${datasetId}/prompts/reject-generated/`, {
        name: prompt.name,
      });
      return index;
    },
    onSuccess: (index) => {
      setPrompts((prev) =>
        prev.map((p, i) => (i === index ? { ...p, status: 'rejected' } : p))
      );
      // Navigate to next pending tab
      const nextPending = prompts.findIndex((p, i) => i > index && p.status === 'pending');
      if (nextPending !== -1) {
        setActiveTab(nextPending);
      }
    },
  });

  const allProcessed = prompts.length > 0 && prompts.every((p) => p.status !== 'pending');
  const currentPrompt = prompts[activeTab];

  const updatePromptField = (index: number, field: keyof GeneratedPrompt, value: string) => {
    setPrompts((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p))
    );
  };

  return (
    <PageLayout
      title="AI Prompt Generation"
      breadcrumbs={[
        { label: 'Projects', to: '/app/projects' },
        { label: project?.name || '...', to: `/app/projects/${projectId}` },
        { label: dataset?.name || '...', to: `/app/projects/${projectId}/datasets/${datasetId}` },
        { label: 'Prompts', to: `/app/projects/${projectId}/datasets/${datasetId}/prompts` },
        { label: 'AI Generate' },
      ]}
    >
      {/* Generate Button */}
      {!generated && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center">
          <svg className="mx-auto h-16 w-16 text-purple-400 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Generate Prompt Variants with AI
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
            AI will generate up to 5 prompt variants for the dataset "{dataset?.name}". You can review, edit, save, or reject each one.
          </p>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-6 py-3 text-sm font-medium text-white shadow-sm hover:bg-purple-500 disabled:opacity-50 transition-colors"
          >
            {generateMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Generating...
              </>
            ) : (
              'Generate Prompts'
            )}
          </button>
          {generateMutation.isError && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">
              {(generateMutation.error as Error)?.message || 'Generation failed.'}
            </p>
          )}
        </div>
      )}

      {/* Generated Prompts */}
      {generated && prompts.length > 0 && (
        <div>
          {/* Tab Bar */}
          <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
            <nav className="flex gap-1">
              {prompts.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => setActiveTab(index)}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                    activeTab === index
                      ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  Prompt {index + 1}
                  {prompt.status === 'saved' && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-green-500" />
                  )}
                  {prompt.status === 'rejected' && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-red-500" />
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Current Prompt Content */}
          {currentPrompt && (
            <div className="space-y-4">
              {/* Status Banner */}
              {currentPrompt.status !== 'pending' && (
                <div
                  className={`rounded-lg px-4 py-3 text-sm font-medium ${
                    currentPrompt.status === 'saved'
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
                  }`}
                >
                  {currentPrompt.status === 'saved' ? 'This prompt has been saved.' : 'This prompt has been rejected.'}
                </div>
              )}

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={currentPrompt.name}
                  onChange={(e) => updatePromptField(activeTab, 'name', e.target.value)}
                  disabled={currentPrompt.status !== 'pending'}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              {/* Template */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Template
                </label>
                <textarea
                  value={currentPrompt.template}
                  onChange={(e) => updatePromptField(activeTab, 'template', e.target.value)}
                  disabled={currentPrompt.status !== 'pending'}
                  rows={10}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed resize-y"
                />
              </div>

              {/* Answer Choices */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Answer Choices
                </label>
                <input
                  type="text"
                  value={currentPrompt.answer_choices}
                  onChange={(e) => updatePromptField(activeTab, 'answer_choices', e.target.value)}
                  disabled={currentPrompt.status !== 'pending'}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              {/* Actions */}
              {currentPrompt.status === 'pending' && (
                <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={() => saveMutation.mutate(activeTab)}
                    disabled={saveMutation.isPending}
                    className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-500 disabled:opacity-50 transition-colors"
                  >
                    {saveMutation.isPending ? 'Saving...' : 'Save Prompt'}
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(activeTab)}
                    disabled={rejectMutation.isPending}
                    className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-500 disabled:opacity-50 transition-colors"
                  >
                    {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Summary when all processed */}
          {allProcessed && (
            <div className="mt-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-6 text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">All Done</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                {prompts.filter((p) => p.status === 'saved').length} prompt(s) saved,{' '}
                {prompts.filter((p) => p.status === 'rejected').length} rejected.
              </p>
              <button
                onClick={() => navigate(`/app/projects/${projectId}/datasets/${datasetId}/prompts`)}
                className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-500 transition-colors"
              >
                Back to Prompts
              </button>
            </div>
          )}
        </div>
      )}
    </PageLayout>
  );
}
