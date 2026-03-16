import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import type { PaginatedResponse } from '@/types';

interface UserPrompt {
  id: number;
  name: string;
  dataset_name: string;
  dataset_id: number;
  project_name: string;
  project_id: number;
  status: string;
  created_on: string;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    submitted: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    returned: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  };
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status.toLowerCase()] || styles.draft}`}>
      {label}
    </span>
  );
}

export default function UserPromptsList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading, isError, error } = useQuery<PaginatedResponse<UserPrompt>>({
    queryKey: ['user-prompts', page],
    queryFn: async () => {
      const res = await api.get(`/user/prompts/?page=${page}`);
      return res.data;
    },
  });

  const handlePageChange = (newPage: number) => {
    setSearchParams((prev) => {
      prev.set('page', String(newPage));
      return prev;
    });
  };

  const totalPages = data ? Math.ceil(data.count / 20) : 0;

  return (
    <PageLayout
      title="My Prompts"
      breadcrumbs={[{ label: 'My Prompts' }]}
    >
      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-center">
          <p className="text-sm text-red-600 dark:text-red-400">
            {(error as Error)?.message || 'Failed to load prompts.'}
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="min-w-full">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                {['Prompt', 'Dataset', 'Project', 'Status', 'Created'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-40" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-28" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Table */}
      {data && (
        <>
          {data.results.length === 0 ? (
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931z" />
              </svg>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">No prompts yet</h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                You have not created any prompts across your projects.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Prompt</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Dataset</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Project</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Created</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {data.results.map((prompt) => (
                    <tr key={prompt.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/projects/${prompt.project_id}/datasets/${prompt.dataset_id}/prompts/${prompt.id}/edit`}
                          className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {prompt.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {prompt.dataset_name}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/projects/${prompt.project_id}`}
                          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {prompt.project_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={prompt.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {new Date(prompt.created_on).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={!data.next}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
