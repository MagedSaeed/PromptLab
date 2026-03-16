import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import type { Prompt, Project, Dataset, ReviewAction } from '@/types';

function ReviewHistoryItem({ action }: { action: ReviewAction }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {action.submitter.username}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(action.taken_on).toLocaleString()}
        </span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            action.submitter_decision === 'approve'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
              : action.submitter_decision === 'return'
                ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
          }`}
        >
          {action.submitter_decision_display || action.prompt_status}
        </span>
      </div>
      {action.submitter_comment && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 bg-gray-50 dark:bg-gray-900 rounded-md p-3">
          {action.submitter_comment}
        </p>
      )}
    </div>
  );
}

export default function PromptReview() {
  const { projectId, datasetId, promptId } = useParams<{
    projectId: string;
    datasetId: string;
    promptId: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [decision, setDecision] = useState<'approve' | 'return'>('approve');
  const [comment, setComment] = useState('');
  const [editedTemplate, setEditedTemplate] = useState('');
  const [editedName, setEditedName] = useState('');
  const [editedAnswerChoices, setEditedAnswerChoices] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

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

  const { data: prompt, isLoading, isError, error } = useQuery<Prompt>({
    queryKey: ['prompt', promptId],
    queryFn: async () => (await api.get(`/prompts/${promptId}/`)).data,
    enabled: !!promptId,
  });

  // Initialize editable fields once prompt loads
  if (prompt && !initialized) {
    setEditedName(prompt.name);
    setEditedTemplate(prompt.template);
    setEditedAnswerChoices(prompt.answer_choices || '');
    setInitialized(true);
  }

  const submitReviewMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/prompts/${promptId}/review/`, {
        decision,
        comment: comment.trim(),
        modifications: {
          name: editedName,
          template: editedTemplate,
          answer_choices: editedAnswerChoices,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt', promptId] });
      queryClient.invalidateQueries({ queryKey: ['prompts', datasetId] });
      navigate(`/app/projects/${projectId}/datasets/${datasetId}/prompts`);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to submit review.';
      setFormError(message);
    },
  });

  const handleSubmit = () => {
    setFormError(null);
    if (decision === 'return' && !comment.trim()) {
      setFormError('A comment is required when returning a prompt for modification.');
      return;
    }
    submitReviewMutation.mutate();
  };

  if (isLoading) {
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
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </PageLayout>
    );
  }

  if (isError || !prompt) {
    return (
      <PageLayout
        title="Error"
        breadcrumbs={[
          { label: 'Projects', to: '/app/projects' },
          { label: project?.name || '...', to: `/app/projects/${projectId}` },
          { label: 'Error' },
        ]}
      >
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-center">
          <p className="text-sm text-red-600 dark:text-red-400">
            {(error as Error)?.message || 'Failed to load prompt.'}
          </p>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={`Review: ${prompt.name}`}
      breadcrumbs={[
        { label: 'Projects', to: '/app/projects' },
        { label: project?.name || '...', to: `/app/projects/${projectId}` },
        { label: dataset?.name || '...', to: `/app/projects/${projectId}/datasets/${datasetId}` },
        { label: 'Prompts', to: `/app/projects/${projectId}/datasets/${datasetId}/prompts` },
        { label: 'Review' },
      ]}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Prompt Fields */}
        <div className="lg:col-span-2 space-y-6">
          {/* Error */}
          {formError && (
            <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
              <p className="text-sm text-red-600 dark:text-red-400">{formError}</p>
            </div>
          )}

          {/* Prompt Info */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">Created by:</span>{' '}
                <span className="font-medium text-gray-900 dark:text-white">{prompt.created_by.username}</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Status:</span>{' '}
                <span className="font-medium text-gray-900 dark:text-white">{prompt.status}</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Dataset:</span>{' '}
                <span className="font-medium text-gray-900 dark:text-white">{prompt.dataset_name}</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Task:</span>{' '}
                <span className="font-medium text-gray-900 dark:text-white">{prompt.task_name || '--'}</span>
              </div>
            </div>
          </div>

          {/* Editable Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Prompt Name
            </label>
            <input
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Editable Template */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Template
            </label>
            <textarea
              value={editedTemplate}
              onChange={(e) => setEditedTemplate(e.target.value)}
              dir={prompt.text_direction}
              rows={10}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
            />
          </div>

          {/* Answer Choices */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Answer Choices
            </label>
            <input
              type="text"
              value={editedAnswerChoices}
              onChange={(e) => setEditedAnswerChoices(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Tags */}
          {prompt.tags.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tags
              </label>
              <div className="flex flex-wrap gap-1">
                {prompt.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-gray-100 dark:bg-gray-700 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Review Decision */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
              Review Decision
            </h3>

            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="decision"
                  value="approve"
                  checked={decision === 'approve'}
                  onChange={() => setDecision('approve')}
                  className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300"
                />
                <span className="text-sm font-medium text-green-700 dark:text-green-400">Approve</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="decision"
                  value="return"
                  checked={decision === 'return'}
                  onChange={() => setDecision('return')}
                  className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
                />
                <span className="text-sm font-medium text-orange-700 dark:text-orange-400">Return for Modification</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Comment {decision === 'return' && <span className="text-red-500">*</span>}
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={4}
                placeholder={decision === 'return' ? 'Explain what needs to be modified...' : 'Optional comment...'}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitReviewMutation.isPending}
                className={`rounded-lg px-6 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50 transition-colors ${
                  decision === 'approve'
                    ? 'bg-green-600 hover:bg-green-500'
                    : 'bg-orange-600 hover:bg-orange-500'
                }`}
              >
                {submitReviewMutation.isPending
                  ? 'Submitting...'
                  : decision === 'approve'
                    ? 'Approve Prompt'
                    : 'Return for Modification'}
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
        </div>

        {/* Sidebar - Review History */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
            Review History
          </h3>
          {prompt.review_actions && prompt.review_actions.length > 0 ? (
            <div className="space-y-3">
              {prompt.review_actions.map((action) => (
                <ReviewHistoryItem key={action.id} action={action} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">No review history yet.</p>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
