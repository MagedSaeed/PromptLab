import { useState, useMemo } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ExternalLink, Search, Database } from 'lucide-react';
import type { Dataset, Task, PaginatedResponse, Project } from '@/types';

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useMemo(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function DatasetCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-3 w-1/2 mt-2" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-2/3 mb-4" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function DatasetList() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const search = useDebounce(searchInput, 300);
  const taskFilter = searchParams.get('task') || '';

  const { data: project } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const res = await api.get(`/projects/${projectId}/`);
      return res.data;
    },
    enabled: !!projectId,
  });

  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await api.get('/tasks/');
      const payload = res.data;
      return Array.isArray(payload) ? payload : payload.results ?? [];
    },
  });

  const { data, isLoading, isError, error } = useQuery<PaginatedResponse<Dataset>>({
    queryKey: ['datasets', projectId, { search, task: taskFilter }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (taskFilter) params.set('task', taskFilter);
      const res = await api.get(`/projects/${projectId}/datasets/?${params.toString()}`);
      return res.data;
    },
    enabled: !!projectId,
  });

  const handleTaskFilter = (value: string) => {
    setSearchParams((prev) => {
      if (value === 'all') {
        prev.delete('task');
      } else {
        prev.set('task', value);
      }
      return prev;
    });
  };

  return (
    <PageLayout
      title="Datasets"
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        { label: project?.name || 'Project', href: `/app/projects/${projectId}` },
        { label: 'Datasets' },
      ]}
    >
      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search datasets..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={taskFilter || 'all'} onValueChange={handleTaskFilter}>
          <SelectTrigger className="w-full sm:w-[220px]">
            <SelectValue placeholder="Filter by task" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Tasks</SelectItem>
            {tasks?.map((task) => (
              <SelectItem key={task.id} value={String(task.id)}>
                {task.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Error State */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-destructive">
              Failed to load datasets. {(error as Error)?.message || 'Please try again.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <DatasetCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Dataset Grid */}
      {data && (
        <>
          {data.results.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Database className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-sm font-medium">No datasets found</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {search
                    ? 'Try a different search term.'
                    : 'No datasets have been added to this project yet.'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.results.map((dataset) => (
                <Link
                  key={dataset.id}
                  to={`/app/datasets/${dataset.id}`}
                  className="group block"
                >
                  <Card className="h-full transition-all hover:shadow-md hover:border-primary/30">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <CardTitle className="text-base group-hover:text-primary transition-colors line-clamp-1">
                          {dataset.name}
                        </CardTitle>
                        <Badge variant="secondary" className="shrink-0">
                          {dataset.prompt_count} prompts
                        </Badge>
                      </div>
                      <a
                        href={dataset.huggingface_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-xs text-muted-foreground font-mono hover:text-primary transition-colors"
                      >
                        {dataset.huggingface_name}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </CardHeader>
                    <CardContent>
                      {dataset.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                          {dataset.description}
                        </p>
                      )}
                      {dataset.primary_task && (
                        <Badge variant="outline">{dataset.primary_task.name}</Badge>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
