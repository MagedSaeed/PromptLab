import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { RefreshCw, AlertTriangle } from 'lucide-react';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { Project, PaginatedResponse } from '@/types';

interface HFSyncFormData {
  sheet_id: string;
  sheet_name: string;
  link_column: string;
  task_column: string;
  target_column: string;
  is_single_classification_column: string;
  default_subset_column: string;
  subsets_column: string;
  clear_datasets: boolean;
  target_project: number | null;
}

const initialFormData: HFSyncFormData = {
  sheet_id: '',
  sheet_name: 'final-list',
  link_column: 'link',
  task_column: 'task_name',
  target_column: '',
  is_single_classification_column: '',
  default_subset_column: '',
  subsets_column: '',
  clear_datasets: false,
  target_project: null,
};

export default function HFSync() {
  const [formData, setFormData] = useState<HFSyncFormData>(initialFormData);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: projectsData } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects-all'],
    queryFn: async () => {
      const res = await api.get('/projects/?page_size=100');
      return res.data;
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (data: HFSyncFormData) => {
      const payload: Record<string, unknown> = { ...data };
      if (!data.target_project) {
        delete payload.target_project;
      }
      const res = await api.post('/hf-sync/', payload);
      return res.data;
    },
    onSuccess: (data) => {
      setMessage({
        type: 'success',
        text: data?.message || 'HuggingFace sync started successfully.',
      });
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: Record<string, unknown> }; message?: string };
      const detail =
        axiosErr.response?.data
          ? Object.values(axiosErr.response.data).flat().join(' ')
          : axiosErr.message || 'Sync failed. Please try again.';
      setMessage({ type: 'error', text: detail });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    syncMutation.mutate(formData);
  };

  const updateField = <K extends keyof HFSyncFormData>(key: K, value: HFSyncFormData[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <PageLayout
      title="HuggingFace Sync"
      breadcrumbs={[{ label: 'HF Sync' }]}
    >
      <div className="max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Sync Datasets from Google Sheets
            </CardTitle>
            <CardDescription>
              Import datasets from a Google Sheet that references HuggingFace datasets.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Sheet ID */}
              <div className="space-y-2">
                <Label htmlFor="sheet_id">Sheet ID *</Label>
                <Input
                  id="sheet_id"
                  value={formData.sheet_id}
                  onChange={(e) => updateField('sheet_id', e.target.value)}
                  placeholder="Google Sheets ID"
                  required
                />
              </div>

              {/* Sheet Name */}
              <div className="space-y-2">
                <Label htmlFor="sheet_name">Sheet Name</Label>
                <Input
                  id="sheet_name"
                  value={formData.sheet_name}
                  onChange={(e) => updateField('sheet_name', e.target.value)}
                  placeholder="final-list"
                />
              </div>

              {/* Column Mappings */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="link_column">Link Column</Label>
                  <Input
                    id="link_column"
                    value={formData.link_column}
                    onChange={(e) => updateField('link_column', e.target.value)}
                    placeholder="link"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="task_column">Task Column</Label>
                  <Input
                    id="task_column"
                    value={formData.task_column}
                    onChange={(e) => updateField('task_column', e.target.value)}
                    placeholder="task_name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="target_column">Target Column</Label>
                  <Input
                    id="target_column"
                    value={formData.target_column}
                    onChange={(e) => updateField('target_column', e.target.value)}
                    placeholder="target_column"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="is_single_classification_column">
                    Single Classification Column
                  </Label>
                  <Input
                    id="is_single_classification_column"
                    value={formData.is_single_classification_column}
                    onChange={(e) =>
                      updateField('is_single_classification_column', e.target.value)
                    }
                    placeholder="is_single_classification"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="default_subset_column">Default Subset Column</Label>
                  <Input
                    id="default_subset_column"
                    value={formData.default_subset_column}
                    onChange={(e) => updateField('default_subset_column', e.target.value)}
                    placeholder="default_subset"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="subsets_column">Subsets Column</Label>
                  <Input
                    id="subsets_column"
                    value={formData.subsets_column}
                    onChange={(e) => updateField('subsets_column', e.target.value)}
                    placeholder="subsets"
                  />
                </div>
              </div>

              {/* Target Project */}
              <div className="space-y-2">
                <Label htmlFor="target_project">Target Project</Label>
                <Select
                  value={formData.target_project?.toString() ?? ''}
                  onValueChange={(val) =>
                    updateField('target_project', val ? parseInt(val, 10) : null)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {projectsData?.results.map((project) => (
                      <SelectItem key={project.id} value={project.id.toString()}>
                        {project.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Clear Datasets */}
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label
                      htmlFor="clear_datasets"
                      className="text-sm font-medium flex items-center gap-2"
                    >
                      <AlertTriangle className="h-4 w-4 text-destructive" />
                      Clear Existing Datasets
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      This will delete all existing datasets before syncing. This action cannot be
                      undone.
                    </p>
                  </div>
                  <Switch
                    id="clear_datasets"
                    checked={formData.clear_datasets}
                    onCheckedChange={(checked) => updateField('clear_datasets', checked)}
                  />
                </div>
              </div>

              {/* Messages */}
              {message && (
                <div
                  className={`rounded-lg p-3 text-sm ${
                    message.type === 'success'
                      ? 'bg-green-50 text-green-800 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
                      : 'bg-destructive/10 text-destructive border border-destructive/30'
                  }`}
                >
                  {message.text}
                </div>
              )}

              {/* Submit */}
              <Button
                type="submit"
                className="w-full"
                disabled={syncMutation.isPending || !formData.sheet_id}
              >
                {syncMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    Start Sync
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
