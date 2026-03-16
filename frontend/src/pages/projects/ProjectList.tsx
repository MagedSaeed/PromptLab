import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Database, Users, FolderOpen } from 'lucide-react';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { Project, PaginatedResponse } from '@/types';

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

type SortOption = 'name' | '-created_on' | '-datasets_count';

function ProjectCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <Skeleton className="h-4 w-full mt-2" />
        <Skeleton className="h-4 w-2/3" />
      </CardHeader>
      <CardContent>
        <div className="flex gap-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-24" />
        </div>
      </CardContent>
      <CardFooter>
        <Skeleton className="h-3 w-32" />
      </CardFooter>
    </Card>
  );
}

function RoleBadge({ role }: { role: string | null }) {
  if (!role) return null;
  const variantMap: Record<string, 'default' | 'secondary' | 'outline'> = {
    owner: 'default',
    prompter: 'secondary',
    reviewer: 'outline',
  };
  return (
    <Badge variant={variantMap[role] || 'outline'}>
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </Badge>
  );
}

export default function ProjectList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const search = useDebounce(searchInput, 300);
  const sort = (searchParams.get('sort') as SortOption) || '-created_on';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading, isError, error } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects', { search, sort, page }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      params.set('ordering', sort);
      params.set('page', String(page));
      const res = await api.get(`/projects/?${params.toString()}`);
      return res.data;
    },
  });

  const handleSort = (newSort: SortOption) => {
    setSearchParams((prev) => {
      prev.set('sort', newSort);
      prev.delete('page');
      return prev;
    });
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams((prev) => {
      prev.set('page', String(newPage));
      return prev;
    });
  };

  const totalPages = data ? Math.ceil(data.count / 12) : 0;

  return (
    <PageLayout
      title="Projects"
      breadcrumbs={[{ label: 'Projects' }]}
      actions={
        <Button asChild>
          <Link to="/app/projects/new">
            <Plus className="h-4 w-4" />
            Create Project
          </Link>
        </Button>
      }
    >
      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search projects..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={sort} onValueChange={(val) => handleSort(val as SortOption)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="-created_on">Newest</SelectItem>
            <SelectItem value="name">Name (A-Z)</SelectItem>
            <SelectItem value="-datasets_count">Most Datasets</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Error State */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-destructive">
              Failed to load projects. {(error as Error)?.message || 'Please try again.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <ProjectCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Project Grid */}
      {data && (
        <>
          {data.results.length === 0 ? (
            <Card className="py-12">
              <CardContent className="flex flex-col items-center justify-center text-center">
                <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-base font-medium mb-1">No projects found</h3>
                <p className="text-sm text-muted-foreground">
                  {search ? 'Try a different search term.' : 'Create your first project to get started.'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {data.results.map((project) => (
                <Link key={project.id} to={`/app/projects/${project.id}`} className="group">
                  <Card className="h-full transition-all hover:shadow-md hover:border-primary/50">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-2">
                        <CardTitle className="text-lg group-hover:text-primary transition-colors truncate">
                          {project.name}
                        </CardTitle>
                        <RoleBadge role={project.user_role} />
                      </div>
                      {project.description && (
                        <CardDescription className="line-clamp-2">
                          {project.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Database className="h-3.5 w-3.5" />
                          {project.datasets_count} datasets
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Users className="h-3.5 w-3.5" />
                          {project.members_count} members
                        </span>
                      </div>
                    </CardContent>
                    <CardFooter className="pt-0">
                      <p className="text-xs text-muted-foreground">
                        Owner: {project.owner.username}
                      </p>
                    </CardFooter>
                  </Card>
                </Link>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground px-2">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page + 1)}
                disabled={!data.next}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
