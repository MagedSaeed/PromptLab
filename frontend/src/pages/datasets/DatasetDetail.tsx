import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from 'sonner';
import PageLayout from '@/components/layout/PageLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ExternalLink,
  RefreshCw,
  FileText,
  ChevronLeft,
  ChevronRight,
  Database,
} from 'lucide-react';
import type { DatasetDetail as DatasetDetailType } from '@/types';

interface SamplesResponse {
  samples: Record<string, unknown>[];
  split: string;
  config: string;
  total_samples: number;
}

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [selectedConfig, setSelectedConfig] = useState('');
  const [selectedSplit, setSelectedSplit] = useState('');
  const [samplePage, setSamplePage] = useState(0);
  const rowsPerPage = 10;

  const { data: dataset, isLoading, isError, error } = useQuery<DatasetDetailType>({
    queryKey: ['dataset', id],
    queryFn: async () => {
      const res = await api.get(`/datasets/${id}/`);
      return res.data;
    },
    enabled: !!id,
  });

  // Set default config/split when dataset loads
  useEffect(() => {
    if (dataset && !selectedConfig) {
      const configs = Object.keys(dataset.configs_with_splits || {});
      if (configs.length > 0) {
        const defaultCfg =
          dataset.default_subset && configs.includes(dataset.default_subset)
            ? dataset.default_subset
            : configs[0];
        setSelectedConfig(defaultCfg);
        const splits = dataset.configs_with_splits[defaultCfg] || [];
        if (splits.length > 0) {
          setSelectedSplit(splits[0]);
        }
      }
    }
  }, [dataset, selectedConfig]);

  const { data: samplesData, isLoading: samplesLoading } = useQuery<SamplesResponse>({
    queryKey: ['dataset-samples', id, selectedConfig, selectedSplit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedConfig) params.set('config', selectedConfig);
      if (selectedSplit) params.set('split', selectedSplit);
      if (selectedConfig) params.set('subset', selectedConfig);
      const res = await api.get(`/datasets/${id}/samples/?${params.toString()}`);
      return res.data;
    },
    enabled: !!id && !!selectedConfig && !!selectedSplit,
  });

  const resetCacheMutation = useMutation({
    mutationFn: () => api.post(`/datasets/${id}/reset-cache/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', id] });
      queryClient.invalidateQueries({ queryKey: ['dataset-samples', id] });
      toast.success('Cache reset successfully');
    },
    onError: () => {
      toast.error('Failed to reset cache');
    },
  });

  const configs = dataset ? Object.keys(dataset.configs_with_splits || {}) : [];
  const splits =
    dataset && selectedConfig
      ? dataset.configs_with_splits[selectedConfig] || []
      : [];
  const sampleList = samplesData?.samples || [];
  const totalSamples = samplesData?.total_samples ?? sampleList.length;
  const columns = sampleList.length > 0 ? Object.keys(sampleList[0]) : [];
  const paginatedSamples = sampleList.slice(
    samplePage * rowsPerPage,
    (samplePage + 1) * rowsPerPage
  );
  const totalPages = Math.ceil(sampleList.length / rowsPerPage);

  const handleConfigChange = (value: string) => {
    setSelectedConfig(value);
    const newSplits = dataset?.configs_with_splits[value] || [];
    setSelectedSplit(newSplits[0] || '');
    setSamplePage(0);
  };

  const handleSplitChange = (value: string) => {
    setSelectedSplit(value);
    setSamplePage(0);
  };

  // Loading state
  if (isLoading) {
    return (
      <PageLayout
        title=""
        breadcrumbs={[
          { label: 'Projects', href: '/app/projects' },
          { label: 'Datasets' },
          { label: 'Loading...' },
        ]}
      >
        <div className="space-y-6">
          <div className="space-y-3">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (isError || !dataset) {
    return (
      <PageLayout
        title="Error"
        breadcrumbs={[
          { label: 'Projects', href: '/app/projects' },
          { label: 'Error' },
        ]}
      >
        <Card className="border-destructive">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-destructive">
              {(error as Error)?.message || 'Failed to load dataset.'}
            </p>
          </CardContent>
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={dataset.name}
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        { label: 'Datasets' },
        { label: dataset.name },
      ]}
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => resetCacheMutation.mutate()}
            disabled={resetCacheMutation.isPending}
          >
            <RefreshCw
              className={`h-4 w-4 ${resetCacheMutation.isPending ? 'animate-spin' : ''}`}
            />
            {resetCacheMutation.isPending ? 'Resetting...' : 'Reset Cache'}
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to={`/app/datasets/${id}/prompts`}>
              <FileText className="h-4 w-4" />
              Browse Prompts
            </Link>
          </Button>
        </div>
      }
    >
      {/* Header Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-xl">{dataset.name}</CardTitle>
              <a
                href={dataset.huggingface_link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground font-mono hover:text-primary transition-colors"
              >
                {dataset.huggingface_name}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
            <Badge variant="secondary" className="text-sm">
              {dataset.prompt_count} prompts
            </Badge>
          </div>
          {dataset.description && (
            <CardDescription className="mt-2 text-sm">
              {dataset.description}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <Separator className="mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Tasks */}
            {dataset.tasks && dataset.tasks.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Tasks
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {dataset.tasks.map((task) => (
                    <Badge key={task.id} variant="outline">
                      {task.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Columns */}
            {dataset.columns_names && dataset.columns_names.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Columns
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {dataset.columns_names.map((col) => (
                    <Badge key={col} variant="secondary" className="font-mono text-xs">
                      {col}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Features */}
            {dataset.features && Object.keys(dataset.features).length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Features
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(dataset.features).map(([key, value]) => (
                    <Badge key={key} variant="secondary" className="font-mono text-xs">
                      {key}:{' '}
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Target Column */}
            {dataset.target_column && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Target Column
                </p>
                <Badge variant="default" className="font-mono text-xs">
                  {dataset.target_column}
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Config & Split Selectors */}
      {configs.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Data Explorer</CardTitle>
            <CardDescription>
              Select a configuration and split to browse sample data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Config / Subset
                </label>
                <Select value={selectedConfig} onValueChange={handleConfigChange}>
                  <SelectTrigger className="w-full sm:w-[220px]">
                    <SelectValue placeholder="Select config" />
                  </SelectTrigger>
                  <SelectContent>
                    {configs.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {splits.length > 0 && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Split
                  </label>
                  <Select value={selectedSplit} onValueChange={handleSplitChange}>
                    <SelectTrigger className="w-full sm:w-[180px]">
                      <SelectValue placeholder="Select split" />
                    </SelectTrigger>
                    <SelectContent>
                      {splits.map((s) => (
                        <SelectItem key={s} value={s}>
                          {s}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              {totalSamples > 0 && (
                <div className="flex items-end">
                  <p className="text-sm text-muted-foreground pb-2">
                    {totalSamples.toLocaleString()} total samples
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Samples Table */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Sample Data</CardTitle>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSamplePage((p) => Math.max(0, p - 1))}
                  disabled={samplePage <= 0 || samplesLoading}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm text-muted-foreground min-w-[80px] text-center">
                  {samplePage + 1} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setSamplePage((p) => Math.min(totalPages - 1, p + 1))
                  }
                  disabled={samplePage >= totalPages - 1 || samplesLoading}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {samplesLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="h-4 w-1/4" />
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-4 w-1/4" />
                  <Skeleton className="h-4 w-1/6" />
                </div>
              ))}
            </div>
          ) : paginatedSamples.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px] text-center text-xs">
                      #
                    </TableHead>
                    {columns.map((col) => (
                      <TableHead
                        key={col}
                        className="text-xs font-mono min-w-[120px] whitespace-nowrap"
                      >
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedSamples.map((sample, idx) => (
                    <TableRow key={samplePage * rowsPerPage + idx}>
                      <TableCell className="text-center text-xs text-muted-foreground">
                        {samplePage * rowsPerPage + idx + 1}
                      </TableCell>
                      {columns.map((col) => {
                        const value = sample[col];
                        const displayValue =
                          typeof value === 'object' && value !== null
                            ? JSON.stringify(value)
                            : String(value ?? '');
                        return (
                          <TableCell
                            key={col}
                            className="text-xs max-w-[300px] truncate"
                            title={displayValue}
                          >
                            {displayValue}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-12 text-center">
              <Database className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                {selectedConfig && selectedSplit
                  ? 'No samples available for the selected configuration.'
                  : 'Select a configuration and split to view samples.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
