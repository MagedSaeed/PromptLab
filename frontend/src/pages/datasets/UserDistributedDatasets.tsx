import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';

interface DistributedDataset {
  id: number;
  project_id: number;
  project_name: string;
  task_name: string;
  dataset_id: number;
  dataset_name: string;
  status: string;
  prompts_count: number;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  };
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status.toLowerCase()] || styles.pending}`}>
      {label}
    </span>
  );
}

export default function UserDistributedDatasets() {
  const { user } = useAuth();

  const { data, isLoading, isError, error } = useQuery<DistributedDataset[]>({
    queryKey: ['user-distributed-datasets'],
    queryFn: async () => {
      const res = await api.get('/user/datasets/');
      return res.data.results || res.data;
    },
  });

  return (
    <PageLayout
      title="My Assigned Datasets"
      breadcrumbs={[{ label: 'My Datasets' }]}
    >
      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-center">
          <p className="text-sm text-red-600 dark:text-red-400">
            {(error as Error)?.message || 'Failed to load datasets.'}
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="min-w-full">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                {['Project', 'Task', 'Dataset', 'Status', 'Prompts', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-28" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12" /></td>
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
          {data.length === 0 ? (
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
              </svg>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">No datasets assigned</h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                You have not been assigned any datasets yet. Project owners can distribute datasets to members.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Project</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Task</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Dataset</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Prompts</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {data.map((item) => (
                    <tr key={`${item.project_id}-${item.dataset_id}-${item.task_name}`} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/projects/${item.project_id}`}
                          className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {item.project_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {item.task_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white font-medium">
                        {item.dataset_name}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                        {item.prompts_count}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/projects/${item.project_id}/datasets/${item.dataset_id}/prompts/new`}
                          className="inline-flex items-center rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500 transition-colors"
                        >
                          Create Prompt
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
