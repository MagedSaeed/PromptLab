import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { X } from 'lucide-react';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import type { ProjectDetail, User } from '@/types';

export default function ProjectForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = !!id;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [minPrompts, setMinPrompts] = useState(1);
  const [prompterSearch, setPrompterSearch] = useState('');
  const [reviewerSearch, setReviewerSearch] = useState('');
  const [selectedPrompters, setSelectedPrompters] = useState<User[]>([]);
  const [selectedReviewers, setSelectedReviewers] = useState<User[]>([]);

  // Load existing project for edit mode
  const { data: existingProject, isLoading: isLoadingProject } = useQuery<ProjectDetail>({
    queryKey: ['project', id],
    queryFn: async () => {
      const res = await api.get(`/projects/${id}/`);
      return res.data;
    },
    enabled: isEdit,
  });

  // Search users for multi-select
  const { data: prompterResults } = useQuery<User[]>({
    queryKey: ['users', 'prompters', prompterSearch],
    queryFn: async () => {
      const res = await api.get(`/users/?search=${prompterSearch}`);
      return res.data.results || res.data;
    },
    enabled: prompterSearch.length >= 2,
  });

  const { data: reviewerResults } = useQuery<User[]>({
    queryKey: ['users', 'reviewers', reviewerSearch],
    queryFn: async () => {
      const res = await api.get(`/users/?search=${reviewerSearch}`);
      return res.data.results || res.data;
    },
    enabled: reviewerSearch.length >= 2,
  });

  // Pre-populate for edit mode
  useEffect(() => {
    if (existingProject) {
      setName(existingProject.name);
      setDescription(existingProject.description || '');
      setMinPrompts(existingProject.minimum_prompts_per_prompter);
      setSelectedPrompters(existingProject.prompters);
      setSelectedReviewers(existingProject.reviewers);
    }
  }, [existingProject]);

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (isEdit) {
        return api.put(`/projects/${id}/`, payload);
      }
      return api.post('/projects/', payload);
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      if (isEdit) {
        queryClient.invalidateQueries({ queryKey: ['project', id] });
      }
      const projectId = isEdit ? id : res.data.id;
      toast.success(isEdit ? 'Project updated successfully.' : 'Project created successfully.');
      navigate(`/app/projects/${projectId}`);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to save project.';
      toast.error(message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast.error('Project name is required.');
      return;
    }

    saveMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      minimum_prompts_per_prompter: minPrompts,
      prompter_ids: selectedPrompters.map((u) => u.id),
      reviewer_ids: selectedReviewers.map((u) => u.id),
    });
  };

  const addPrompter = (u: User) => {
    if (!selectedPrompters.find((p) => p.id === u.id)) {
      setSelectedPrompters([...selectedPrompters, u]);
    }
    setPrompterSearch('');
  };

  const removePrompter = (userId: number) => {
    setSelectedPrompters(selectedPrompters.filter((p) => p.id !== userId));
  };

  const addReviewer = (u: User) => {
    if (!selectedReviewers.find((r) => r.id === u.id)) {
      setSelectedReviewers([...selectedReviewers, u]);
    }
    setReviewerSearch('');
  };

  const removeReviewer = (userId: number) => {
    setSelectedReviewers(selectedReviewers.filter((r) => r.id !== userId));
  };

  if (isEdit && isLoadingProject) {
    return (
      <PageLayout
        title=""
        breadcrumbs={[{ label: 'Projects', href: '/app/projects' }, { label: 'Loading...' }]}
      >
        <div className="max-w-2xl space-y-6">
          <Skeleton className="h-10 w-1/2" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-10 w-1/4" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={isEdit ? 'Edit Project' : 'New Project'}
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        ...(isEdit && existingProject
          ? [{ label: existingProject.name, href: `/app/projects/${id}` }]
          : []),
        { label: isEdit ? 'Edit' : 'New Project' },
      ]}
    >
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        {/* Name */}
        <div className="space-y-2">
          <Label htmlFor="name">
            Project Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Enter project name"
          />
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Describe the project purpose and goals"
          />
        </div>

        {/* Minimum Prompts */}
        <div className="space-y-2">
          <Label htmlFor="minPrompts">Minimum Prompts per Prompter</Label>
          <Input
            id="minPrompts"
            type="number"
            min={0}
            value={minPrompts}
            onChange={(e) => setMinPrompts(parseInt(e.target.value, 10) || 0)}
            className="w-32"
          />
        </div>

        {/* Prompters */}
        <div className="space-y-2">
          <Label>Prompters</Label>
          {selectedPrompters.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {selectedPrompters.map((u) => (
                <Badge key={u.id} variant="secondary" className="gap-1 pr-1">
                  {u.username}
                  <button
                    type="button"
                    onClick={() => removePrompter(u.id)}
                    className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
          <div className="relative">
            <Input
              type="text"
              value={prompterSearch}
              onChange={(e) => setPrompterSearch(e.target.value)}
              placeholder="Search users to add as prompters..."
            />
            {prompterResults && prompterResults.length > 0 && prompterSearch.length >= 2 && (
              <Card className="absolute z-10 mt-1 w-full max-h-40 overflow-y-auto">
                <CardContent className="p-1">
                  {prompterResults
                    .filter((u) => !selectedPrompters.find((p) => p.id === u.id))
                    .map((u) => (
                      <button
                        key={u.id}
                        type="button"
                        onClick={() => addPrompter(u)}
                        className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                      >
                        {u.username}{' '}
                        <span className="text-muted-foreground">({u.email})</span>
                      </button>
                    ))}
                  {prompterResults.filter((u) => !selectedPrompters.find((p) => p.id === u.id)).length === 0 && (
                    <p className="px-3 py-2 text-sm text-muted-foreground">No matching users found.</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Reviewers */}
        <div className="space-y-2">
          <Label>Reviewers</Label>
          {selectedReviewers.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {selectedReviewers.map((u) => (
                <Badge key={u.id} variant="secondary" className="gap-1 pr-1">
                  {u.username}
                  <button
                    type="button"
                    onClick={() => removeReviewer(u.id)}
                    className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
          <div className="relative">
            <Input
              type="text"
              value={reviewerSearch}
              onChange={(e) => setReviewerSearch(e.target.value)}
              placeholder="Search users to add as reviewers..."
            />
            {reviewerResults && reviewerResults.length > 0 && reviewerSearch.length >= 2 && (
              <Card className="absolute z-10 mt-1 w-full max-h-40 overflow-y-auto">
                <CardContent className="p-1">
                  {reviewerResults
                    .filter((u) => !selectedReviewers.find((r) => r.id === u.id))
                    .map((u) => (
                      <button
                        key={u.id}
                        type="button"
                        onClick={() => addReviewer(u)}
                        className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                      >
                        {u.username}{' '}
                        <span className="text-muted-foreground">({u.email})</span>
                      </button>
                    ))}
                  {reviewerResults.filter((u) => !selectedReviewers.find((r) => r.id === u.id)).length === 0 && (
                    <p className="px-3 py-2 text-sm text-muted-foreground">No matching users found.</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-4 border-t">
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending
              ? 'Saving...'
              : isEdit
                ? 'Update Project'
                : 'Create Project'}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
