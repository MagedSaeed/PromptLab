import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import StatusBadge from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Sparkles, Eye, Pencil, ClipboardCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Prompt, PaginatedResponse, Dataset } from '@/types';

type PromptTab = 'mine' | 'submitted' | 'all';

const TAB_LABELS: Record<PromptTab, string> = {
  mine: 'My Prompts',
  submitted: 'Submitted for Review',
  all: 'All Prompts',
};

export default function PromptList() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = (searchParams.get('tab') as PromptTab) || 'mine';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data: dataset } = useQuery<Dataset>({
    queryKey: ['dataset', datasetId],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  const { data, isLoading, isError, error } = useQuery<PaginatedResponse<Prompt>>({
    queryKey: ['prompts', datasetId, activeTab, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('tab', activeTab);
      params.set('page', String(page));
      const res = await api.get(`/datasets/${datasetId}/prompts/?${params.toString()}`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value, page: '1' });
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams({ tab: activeTab, page: String(newPage) });
  };

  const totalPages = data ? Math.ceil(data.count / 20) : 0;

  return (
    <PageLayout
      title="Prompts"
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        { label: dataset?.name || 'Dataset', href: `/app/datasets/${datasetId}` },
        { label: 'Prompts' },
      ]}
      actions={
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to={`/app/datasets/${datasetId}/prompts/new-bulk`}>
              <Sparkles className="h-4 w-4" />
              Generate with AI
            </Link>
          </Button>
          <Button asChild>
            <Link to={`/app/datasets/${datasetId}/prompts/new`}>
              <Plus className="h-4 w-4" />
              Create Prompt
            </Link>
          </Button>
        </div>
      }
    >
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="mb-6">
          {(Object.entries(TAB_LABELS) as [PromptTab, string][]).map(([key, label]) => (
            <TabsTrigger key={key} value={key}>
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {(Object.keys(TAB_LABELS) as PromptTab[]).map((tab) => (
          <TabsContent key={tab} value={tab}>
            {isError && (
              <Card>
                <CardContent className="py-8 text-center">
                  <p className="text-sm text-destructive">
                    {(error as Error)?.message || 'Failed to load prompts.'}
                  </p>
                </CardContent>
              </Card>
            )}

            {isLoading && (
              <Card>
                <div className="p-4 space-y-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-5 w-20" />
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-8 w-20 ml-auto" />
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {data && data.results.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-sm text-muted-foreground">No prompts found in this tab.</p>
                </CardContent>
              </Card>
            )}

            {data && data.results.length > 0 && (
              <Card>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[280px]">Name</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created By</TableHead>
                      <TableHead>Tags</TableHead>
                      <TableHead>Created On</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.results.map((prompt) => (
                      <TableRow key={prompt.id}>
                        <TableCell className="font-medium">
                          <Link
                            to={`/app/datasets/${datasetId}/prompts/${prompt.id}/edit`}
                            className="hover:text-primary transition-colors"
                          >
                            {prompt.name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={prompt.status} />
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {prompt.created_by.username}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {prompt.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {prompt.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{prompt.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(prompt.created_on).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/app/datasets/${datasetId}/prompts/${prompt.id}/edit`}>
                                <Eye className="h-4 w-4" />
                                <span className="sr-only">View</span>
                              </Link>
                            </Button>
                            {prompt.updateable && (
                              <Button variant="ghost" size="sm" asChild>
                                <Link to={`/app/datasets/${datasetId}/prompts/${prompt.id}/edit`}>
                                  <Pencil className="h-4 w-4" />
                                  <span className="sr-only">Edit</span>
                                </Link>
                              </Button>
                            )}
                            {prompt.reviewable && (
                              <Button variant="ghost" size="sm" asChild>
                                <Link to={`/app/datasets/${datasetId}/prompts/${prompt.id}/review`}>
                                  <ClipboardCheck className="h-4 w-4" />
                                  <span className="sr-only">Review</span>
                                </Link>
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-sm text-muted-foreground">
            Showing page {page} of {totalPages} ({data.count} total)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.previous}
              onClick={() => handlePageChange(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.next}
              onClick={() => handlePageChange(page + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
