import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import StatusBadge from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronLeft, ChevronRight, FileText } from 'lucide-react';
import type { Prompt, PaginatedResponse } from '@/types';

export default function UserPromptsList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading, isError, error } = useQuery<PaginatedResponse<Prompt>>({
    queryKey: ['user-prompts', page],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      const res = await api.get(`/user/prompts/?${params.toString()}`);
      return res.data;
    },
  });

  const handlePageChange = (newPage: number) => {
    setSearchParams({ page: String(newPage) });
  };

  const totalPages = data ? Math.ceil(data.count / 20) : 0;

  return (
    <PageLayout
      title="My Prompts"
      breadcrumbs={[{ label: 'My Prompts' }]}
    >
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
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        </Card>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <FileText className="h-10 w-10 text-muted-foreground mx-auto" />
            <p className="text-sm text-muted-foreground">
              You have not created any prompts yet.
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[280px]">Name</TableHead>
                <TableHead>Dataset</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created On</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.results.map((prompt) => (
                <TableRow key={prompt.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/app/datasets/${prompt.dataset}/prompts/${prompt.id}/edit`}
                      className="hover:text-primary transition-colors"
                    >
                      {prompt.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {prompt.dataset_name || prompt.dataset_huggingface_name}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={prompt.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {new Date(prompt.created_on).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

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
