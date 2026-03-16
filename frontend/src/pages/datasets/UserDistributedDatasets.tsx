import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
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
import { ChevronLeft, ChevronRight, Database } from 'lucide-react';

interface UserDataset {
  id: number;
  name: string;
  huggingface_name: string;
  project_id: number;
  project_name: string;
  prompt_count: number;
}

interface PaginatedUserDatasets {
  count: number;
  next: string | null;
  previous: string | null;
  results: UserDataset[];
}

export default function UserDistributedDatasets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading, isError, error } = useQuery<PaginatedUserDatasets>({
    queryKey: ['user-datasets', page],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      const res = await api.get(`/user/datasets/?${params.toString()}`);
      return res.data;
    },
  });

  const handlePageChange = (newPage: number) => {
    setSearchParams({ page: String(newPage) });
  };

  const totalPages = data ? Math.ceil(data.count / 20) : 0;

  return (
    <PageLayout
      title="My Datasets"
      breadcrumbs={[{ label: 'My Datasets' }]}
    >
      {isError && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">
              {(error as Error)?.message || 'Failed to load datasets.'}
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
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </Card>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <Database className="h-10 w-10 text-muted-foreground mx-auto" />
            <p className="text-sm text-muted-foreground">
              No datasets have been assigned to you yet.
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[280px]">Dataset Name</TableHead>
                <TableHead>Project</TableHead>
                <TableHead className="text-right">Prompts</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.results.map((ds) => (
                <TableRow key={ds.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/app/datasets/${ds.id}`}
                      className="hover:text-primary transition-colors"
                    >
                      {ds.name}
                    </Link>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      {ds.huggingface_name}
                    </p>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <Link
                      to={`/app/projects/${ds.project_id}`}
                      className="hover:text-primary transition-colors"
                    >
                      {ds.project_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {ds.prompt_count}
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
