import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import type { DatasetDetail, Project, Prompt, Task, TemplatePreview } from '@/types';

export default function PromptForm() {
  const { projectId, datasetId, promptId } = useParams<{
    projectId: string;
    datasetId: string;
    promptId: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = !!promptId;

  // Form state
  const [name, setName] = useState('');
  const [template, setTemplate] = useState('');
  const [textDirection, setTextDirection] = useState<'ltr' | 'rtl'>('ltr');
  const [answerChoices, setAnswerChoices] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [selectedTask, setSelectedTask] = useState<number | ''>('');
  const [selectedSubset, setSelectedSubset] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sampleIndex, setSampleIndex] = useState(0);
  const [showLLMDialog, setShowLLMDialog] = useState(false);

  // Preview state
  const [previewResult, setPreviewResult] = useState<TemplatePreview | null>(null);

  // Load project
  const { data: project } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/`)).data,
    enabled: !!projectId,
  });

  // Load dataset
  const { data: dataset } = useQuery<DatasetDetail>({
    queryKey: ['dataset-detail', datasetId],
    queryFn: async () => (await api.get(`/datasets/${datasetId}/`)).data,
    enabled: !!datasetId,
  });

  // Load tasks
  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks', projectId],
    queryFn: async () => {
      const res = await api.get(`/tasks/?project_pk=${projectId}`);
      return res.data.results || res.data;
    },
    enabled: !!projectId,
  });

  // Load existing prompt for edit
  const { data: existingPrompt, isLoading: isLoadingPrompt } = useQuery<Prompt>({
    queryKey: ['prompt', promptId],
    queryFn: async () => (await api.get(`/prompts/${promptId}/`)).data,
    enabled: isEdit,
  });

  // Load samples for sidebar
  const { data: samples } = useQuery({
    queryKey: ['dataset-samples', datasetId, selectedSubset],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedSubset) params.set('config', selectedSubset);
      const res = await api.get(`/datasets/${datasetId}/samples/?${params.toString()}`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  // Pre-populate form for edit
  useEffect(() => {
    if (existingPrompt) {
      setName(existingPrompt.name);
      setTemplate(existingPrompt.template);
      setTextDirection(existingPrompt.text_direction);
      setAnswerChoices(existingPrompt.answer_choices || '');
      setTagsInput(existingPrompt.tags.join(', '));
      setSelectedTask(existingPrompt.task || '');
      setSelectedSubset(existingPrompt.dataset_subset || '');
    }
  }, [existingPrompt]);

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/prompts/apply-template/`, {
        template,
        dataset_id: datasetId,
        subset: selectedSubset,
        sample_index: sampleIndex,
        answer_choices: answerChoices,
      });
      return res.data;
    },
    onSuccess: (data) => setPreviewResult(data),
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (status: string) => {
      const payload = {
        name: name.trim(),
        template,
        text_direction: textDirection,
        answer_choices: answerChoices,
        tags: tagsInput.split(',').map((t) => t.trim()).filter(Boolean),
        task: selectedTask || null,
        dataset: Number(datasetId),
        dataset_subset: selectedSubset,
        status,
      };
      if (isEdit) {
        return api.put(`/prompts/${promptId}/`, payload);
      }
      return api.post(`/datasets/${datasetId}/prompts/`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts', datasetId] });
      navigate(`/app/projects/${projectId}/datasets/${datasetId}/prompts`);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to save prompt.';
      setFormError(message);
    },
  });

  // LLM test mutation
  const llmTestMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/prompts/test-llm/`, {
        template,
        dataset_id: datasetId,
        subset: selectedSubset,
        sample_index: sampleIndex,
        answer_choices: answerChoices,
      });
      return res.data;
    },
  });

  const sampleList: Record<string, unknown>[] = samples?.samples || [];
  const currentSample = sampleList[sampleIndex] || null;
  const totalSamples = sampleList.length;

  const subsets = dataset ? (dataset.subsets ? dataset.subsets.split(',').map((s) => s.trim()).filter(Boolean) : Object.keys(dataset.configs_with_splits || {})) : [];

  if (isEdit && isLoadingPrompt) {
    return (
      <PageLayout
        title=""
        breadcrumbs={[
          { label: 'Projects', to: '/app/projects' },
          { label: project?.name || '...', to: `/app/projects/${projectId}` },
          { label: 'Loading...' },
        ]}
      >
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={isEdit ? 'Edit Prompt' : 'New Prompt'}
      breadcrumbs={[
        { label: 'Projects', to: '/app/projects' },
        { label: project?.name || '...', to: `/app/projects/${projectId}` },
        { label: dataset?.name || '...', to: `/app/projects/${projectId}/datasets/${datasetId}` },
        { label: 'Prompts', to: `/app/projects/${projectId}/datasets/${datasetId}/prompts` },
        { label: isEdit ? 'Edit' : 'New Prompt' },
      ]}
    >
      <div className="flex gap-6">
        {/* Left Panel - Editor */}
        <div className={`flex-1 space-y-6 ${sidebarOpen ? 'max-w-[60%]' : ''}`}>
          {/* Error */}
          {formError && (
            <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
              <p className="text-sm text-red-600 dark:text-red-400">{formError}</p>
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="prompt-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Prompt Name <span className="text-red-500">*</span>
            </label>
            <input
              id="prompt-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter prompt name"
            />
          </div>

          {/* Task and Subset Row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Task
              </label>
              <select
                value={selectedTask}
                onChange={(e) => setSelectedTask(e.target.value ? Number(e.target.value) : '')}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select task...</option>
                {tasks?.map((task) => (
                  <option key={task.id} value={task.id}>{task.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Dataset Subset
              </label>
              <select
                value={selectedSubset}
                onChange={(e) => setSelectedSubset(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Default</option>
                {subsets.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tags
            </label>
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Comma-separated tags, e.g. translation, AI generated"
            />
          </div>

          {/* Template Editor */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Template <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Direction:</span>
                <button
                  type="button"
                  onClick={() => setTextDirection(textDirection === 'ltr' ? 'rtl' : 'ltr')}
                  className={`rounded-md border px-2 py-1 text-xs font-medium transition-colors ${
                    textDirection === 'rtl'
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                      : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                  }`}
                >
                  {textDirection.toUpperCase()}
                </button>
              </div>
            </div>
            <textarea
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              dir={textDirection}
              rows={12}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
              placeholder="Write your prompt template using Jinja2 syntax. Use {{ column_name }} for dataset placeholders."
            />
            {dataset?.columns_names && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Available columns: {dataset.columns_names.map((c) => `{{ ${c} }}`).join(', ')}
              </p>
            )}
          </div>

          {/* Answer Choices */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Answer Choices
            </label>
            <input
              type="text"
              value={answerChoices}
              onChange={(e) => setAnswerChoices(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder='JSON: [{"value": "choice1"}, {"value": "choice2"}]'
            />
          </div>

          {/* Preview Section */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Preview</h3>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => previewMutation.mutate()}
                  disabled={!template || previewMutation.isPending}
                  className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                >
                  {previewMutation.isPending ? 'Rendering...' : 'Preview Template'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowLLMDialog(true);
                    llmTestMutation.mutate();
                  }}
                  disabled={!template}
                  className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
                >
                  Test with LLM
                </button>
              </div>
            </div>
            <div className="p-4">
              {previewResult ? (
                <div dir={textDirection} className="prose dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap text-sm bg-gray-50 dark:bg-gray-900 rounded-md p-4 font-sans">
                    {previewResult.rendered_template}
                  </pre>
                  {previewResult.processed_answer_choices?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Answer Choices:</p>
                      <div className="flex flex-wrap gap-1">
                        {previewResult.processed_answer_choices.map((choice, i) => (
                          <span key={i} className="rounded bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300">
                            {choice}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                  Click "Preview Template" to render with sample data.
                </p>
              )}
            </div>
          </div>

          {/* LLM Test Dialog */}
          {showLLMDialog && (
            <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">LLM Test Result</h4>
                <button
                  type="button"
                  onClick={() => setShowLLMDialog(false)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  &times;
                </button>
              </div>
              {llmTestMutation.isPending && (
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600" />
                  Running LLM test...
                </div>
              )}
              {llmTestMutation.data && (
                <pre className="whitespace-pre-wrap text-sm bg-white dark:bg-gray-800 rounded-md p-3 border border-gray-200 dark:border-gray-700">
                  {llmTestMutation.data.result?.content || llmTestMutation.data.error || 'No response'}
                </pre>
              )}
              {llmTestMutation.isError && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {(llmTestMutation.error as Error)?.message || 'LLM test failed.'}
                </p>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={() => saveMutation.mutate('draft')}
              disabled={saveMutation.isPending || !name.trim() || !template.trim()}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              {saveMutation.isPending ? 'Saving...' : 'Save as Draft'}
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate('submitted')}
              disabled={saveMutation.isPending || !name.trim() || !template.trim()}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {saveMutation.isPending ? 'Submitting...' : 'Submit for Review'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>

        {/* Right Sidebar - Dataset Samples */}
        <div className={`transition-all ${sidebarOpen ? 'w-[40%]' : 'w-10'}`}>
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="mb-2 rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            {sidebarOpen ? 'Hide Samples' : 'Show'}
          </button>

          {sidebarOpen && (
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 sticky top-4">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Dataset Sample {totalSamples > 0 && `(${sampleIndex + 1}/${totalSamples})`}
                </h3>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setSampleIndex(Math.max(0, sampleIndex - 1))}
                    disabled={sampleIndex <= 0}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-0.5 text-xs disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Prev
                  </button>
                  <button
                    type="button"
                    onClick={() => setSampleIndex(Math.min(totalSamples - 1, sampleIndex + 1))}
                    disabled={sampleIndex >= totalSamples - 1}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-0.5 text-xs disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Next
                  </button>
                </div>
              </div>
              <div className="p-4 max-h-[70vh] overflow-y-auto">
                {currentSample ? (
                  <dl className="space-y-3">
                    {Object.entries(currentSample).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 font-mono">
                          {key}
                        </dt>
                        <dd className="mt-0.5 text-sm text-gray-900 dark:text-white break-all">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                    No sample data available.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
