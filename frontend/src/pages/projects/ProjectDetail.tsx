import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Copy, Check, Eye, EyeOff, Plus, Trash2, Pencil, Shuffle,
  Database, Users, ClipboardList, AlertTriangle, Download, Heart,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import type { ProjectDetail as ProjectDetailType, DatasetValidation } from '@/types';

// ---------------------------------------------------------------------------
// AddDatasetDialog
// ---------------------------------------------------------------------------

interface AddDatasetDialogProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function AddDatasetDialog({ projectId, open, onOpenChange }: AddDatasetDialogProps) {
  const queryClient = useQueryClient();
  const [datasetPath, setDatasetPath] = useState('');
  const [validation, setValidation] = useState<DatasetValidation | null>(null);
  const [validating, setValidating] = useState(false);

  // Form fields populated after validation
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [defaultSubset, setDefaultSubset] = useState('');
  const [isSingleClassification, setIsSingleClassification] = useState(false);
  const [downloadOnlyDefault, setDownloadOnlyDefault] = useState(false);

  const resetForm = () => {
    setDatasetPath('');
    setValidation(null);
    setValidating(false);
    setName('');
    setDescription('');
    setTargetColumn('');
    setDefaultSubset('');
    setIsSingleClassification(false);
    setDownloadOnlyDefault(false);
  };

  const handleValidate = async () => {
    if (!datasetPath.trim()) return;
    setValidating(true);
    setValidation(null);
    try {
      const res = await api.post('/dataset/validate/', { dataset_path: datasetPath.trim() });
      const data: DatasetValidation = res.data;
      setValidation(data);
      if (data.valid) {
        setName(data.name || '');
        setDescription(data.description || '');
      }
    } catch (err) {
      setValidation({ valid: false, error: (err as Error)?.message || 'Validation failed.' });
    } finally {
      setValidating(false);
    }
  };

  const addMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/projects/${projectId}/datasets/add/`, {
        huggingface_name: datasetPath.trim(),
        name: name.trim(),
        description: description.trim(),
        target_column: targetColumn.trim(),
        default_subset: defaultSubset.trim(),
        is_single_classification: isSingleClassification,
        download_only_the_default_subset: downloadOnlyDefault,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      toast.success('Dataset added successfully.');
      resetForm();
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to add dataset.';
      toast.error(message);
    },
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(val) => {
        if (!val) resetForm();
        onOpenChange(val);
      }}
    >
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Dataset</DialogTitle>
          <DialogDescription>
            Enter a HuggingFace dataset path to validate and add it to this project.
          </DialogDescription>
        </DialogHeader>

        {/* Dataset path + validate */}
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="dataset-path">HuggingFace Dataset Path</Label>
            <div className="flex gap-2">
              <Input
                id="dataset-path"
                placeholder="e.g. squad, glue, arbml/watan_2004"
                value={datasetPath}
                onChange={(e) => setDatasetPath(e.target.value)}
                onBlur={() => {
                  if (datasetPath.trim() && !validation) handleValidate();
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleValidate}
                disabled={!datasetPath.trim() || validating}
              >
                {validating ? 'Validating...' : 'Validate'}
              </Button>
            </div>
          </div>

          {/* Validation results */}
          {validation && !validation.valid && (
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  {validation.error || 'Dataset is not valid.'}
                </p>
              </CardContent>
            </Card>
          )}

          {validation && validation.valid && (
            <>
              <Card>
                <CardContent className="pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{validation.name}</span>
                    <Badge variant="secondary">Valid</Badge>
                  </div>
                  {validation.description && (
                    <p className="text-sm text-muted-foreground line-clamp-3">{validation.description}</p>
                  )}
                  <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                    {validation.downloads != null && (
                      <span className="flex items-center gap-1">
                        <Download className="h-3.5 w-3.5" />
                        {validation.downloads.toLocaleString()} downloads
                      </span>
                    )}
                    {validation.likes != null && (
                      <span className="flex items-center gap-1">
                        <Heart className="h-3.5 w-3.5" />
                        {validation.likes.toLocaleString()} likes
                      </span>
                    )}
                  </div>
                  {validation.configs && validation.configs.length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Configs: </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {validation.configs.map((c) => (
                          <Badge key={c} variant="outline" className="text-xs">
                            {c}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {validation.size_warning && (
                    <p className="text-sm text-amber-600 dark:text-amber-400 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      {validation.size_warning}
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Additional fields */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="ds-name">Name</Label>
                  <Input
                    id="ds-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ds-description">Description</Label>
                  <Textarea
                    id="ds-description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ds-target">Target Column</Label>
                    <Input
                      id="ds-target"
                      value={targetColumn}
                      onChange={(e) => setTargetColumn(e.target.value)}
                      placeholder="e.g. label"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ds-subset">Default Subset</Label>
                    {validation.configs && validation.configs.length > 0 ? (
                      <Select value={defaultSubset} onValueChange={setDefaultSubset}>
                        <SelectTrigger id="ds-subset">
                          <SelectValue placeholder="Select subset" />
                        </SelectTrigger>
                        <SelectContent>
                          {validation.configs.map((c) => (
                            <SelectItem key={c} value={c}>{c}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        id="ds-subset"
                        value={defaultSubset}
                        onChange={(e) => setDefaultSubset(e.target.value)}
                        placeholder="e.g. default"
                      />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <Switch
                      id="ds-single-class"
                      checked={isSingleClassification}
                      onCheckedChange={setIsSingleClassification}
                    />
                    <Label htmlFor="ds-single-class" className="cursor-pointer">
                      Single classification
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      id="ds-download-default"
                      checked={downloadOnlyDefault}
                      onCheckedChange={setDownloadOnlyDefault}
                    />
                    <Label htmlFor="ds-download-default" className="cursor-pointer">
                      Download only default subset
                    </Label>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => { resetForm(); onOpenChange(false); }}>
            Cancel
          </Button>
          <Button
            onClick={() => addMutation.mutate()}
            disabled={!validation?.valid || addMutation.isPending}
          >
            {addMutation.isPending ? 'Adding...' : 'Add Dataset'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Confirmation Dialog
// ---------------------------------------------------------------------------

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  variant?: 'default' | 'destructive';
  loading?: boolean;
  onConfirm: () => void;
}

function ConfirmDialog({
  open, onOpenChange, title, description, confirmLabel = 'Confirm',
  variant = 'default', loading, onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant={variant} onClick={onConfirm} disabled={loading}>
            {loading ? 'Processing...' : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

function StatCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ElementType }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [secretVisible, setSecretVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showAddDataset, setShowAddDataset] = useState(false);
  const [showDistributeConfirm, setShowDistributeConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const { data: project, isLoading, isError, error } = useQuery<ProjectDetailType>({
    queryKey: ['project', id],
    queryFn: async () => {
      const res = await api.get(`/projects/${id}/`);
      return res.data;
    },
    enabled: !!id,
  });

  const distributeMutation = useMutation({
    mutationFn: () => api.post(`/projects/${id}/distribute/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      toast.success('Datasets distributed successfully.');
      setShowDistributeConfirm(false);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Distribution failed.';
      toast.error(message);
      setShowDistributeConfirm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/projects/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project deleted.');
      navigate('/app/projects');
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to delete project.';
      toast.error(message);
      setShowDeleteConfirm(false);
    },
  });

  const removeDatasetMutation = useMutation({
    mutationFn: (datasetId: number) => api.delete(`/projects/${id}/datasets/${datasetId}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      toast.success('Dataset removed from project.');
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to remove dataset.';
      toast.error(message);
    },
  });

  const copySecretKey = () => {
    if (project?.secret_key) {
      navigator.clipboard.writeText(project.secret_key);
      setCopied(true);
      toast.success('Secret key copied to clipboard.');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isOwner = project && user && project.owner.id === user.id;

  if (isLoading) {
    return (
      <PageLayout title="" breadcrumbs={[{ label: 'Projects', href: '/app/projects' }, { label: 'Loading...' }]}>
        <div className="space-y-6">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </PageLayout>
    );
  }

  if (isError || !project) {
    return (
      <PageLayout title="Error" breadcrumbs={[{ label: 'Projects', href: '/app/projects' }, { label: 'Error' }]}>
        <Card className="border-destructive">
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-destructive">
              {(error as Error)?.message || 'Failed to load project.'}
            </p>
          </CardContent>
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={project.name}
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        { label: project.name },
      ]}
      actions={
        isOwner ? (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDistributeConfirm(true)}
            >
              <Shuffle className="h-4 w-4" />
              Distribute
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to={`/app/projects/${id}/edit`}>
                <Pencil className="h-4 w-4" />
                Edit
              </Link>
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          </div>
        ) : null
      }
    >
      {/* Description */}
      {project.description && (
        <p className="text-muted-foreground mb-6">{project.description}</p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard label="Datasets" value={project.datasets_count} icon={Database} />
        <StatCard label="Members" value={project.members_count} icon={Users} />
        <StatCard label="Min Prompts / Prompter" value={project.minimum_prompts_per_prompter} icon={ClipboardList} />
      </div>

      {/* Secret Key */}
      {isOwner && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <Label className="mb-2 block">Project Secret Key</Label>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-md bg-muted px-3 py-2 text-sm font-mono truncate">
                {secretVisible ? project.secret_key : '\u2022'.repeat(36)}
              </code>
              <Button variant="outline" size="icon" onClick={() => setSecretVisible(!secretVisible)}>
                {secretVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button variant="outline" size="icon" onClick={copySecretKey}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="datasets">
        <TabsList>
          <TabsTrigger value="datasets">
            <Database className="h-4 w-4 mr-1.5" />
            Datasets
          </TabsTrigger>
          <TabsTrigger value="members">
            <Users className="h-4 w-4 mr-1.5" />
            Members
          </TabsTrigger>
          <TabsTrigger value="assignments">
            <ClipboardList className="h-4 w-4 mr-1.5" />
            Assignments
          </TabsTrigger>
        </TabsList>

        {/* Datasets Tab */}
        <TabsContent value="datasets" className="mt-6">
          <div className="mb-4 flex justify-between items-center">
            <h3 className="text-sm font-medium text-muted-foreground">
              {project.datasets.length} dataset{project.datasets.length !== 1 ? 's' : ''}
            </h3>
            {isOwner && (
              <Button size="sm" onClick={() => setShowAddDataset(true)}>
                <Plus className="h-4 w-4" />
                Add Dataset
              </Button>
            )}
          </div>

          {project.datasets.length === 0 ? (
            <Card className="py-8">
              <CardContent className="flex flex-col items-center text-center">
                <Database className="h-10 w-10 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">No datasets in this project yet.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {project.datasets.map((dataset) => (
                <Card key={dataset.id} className="group relative transition-all hover:shadow-md hover:border-primary/50">
                  <Link to={`/app/datasets/${dataset.id}`} className="block">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base group-hover:text-primary transition-colors truncate">
                        {dataset.name}
                      </CardTitle>
                      <CardDescription className="font-mono text-xs truncate">
                        {dataset.huggingface_name}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        {dataset.primary_task && (
                          <Badge variant="secondary" className="text-xs">
                            {dataset.primary_task.name}
                          </Badge>
                        )}
                        <span>{dataset.prompt_count} prompts</span>
                      </div>
                    </CardContent>
                  </Link>
                  {isOwner && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-3 right-3 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        removeDatasetMutation.mutate(dataset.id);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Members Tab */}
        <TabsContent value="members" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Prompters */}
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Prompters ({project.prompters.length})
              </h3>
              {project.prompters.length === 0 ? (
                <Card className="py-6">
                  <CardContent className="text-center">
                    <p className="text-sm text-muted-foreground">No prompters assigned.</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2">
                  {project.prompters.map((u) => (
                    <Card key={u.id}>
                      <CardContent className="flex items-center gap-3 py-3 px-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{u.username}</p>
                          <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            {/* Reviewers */}
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Reviewers ({project.reviewers.length})
              </h3>
              {project.reviewers.length === 0 ? (
                <Card className="py-6">
                  <CardContent className="text-center">
                    <p className="text-sm text-muted-foreground">No reviewers assigned.</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2">
                  {project.reviewers.map((u) => (
                    <Card key={u.id}>
                      <CardContent className="flex items-center gap-3 py-3 px-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-sm font-medium text-green-700 dark:text-green-300">
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{u.username}</p>
                          <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Assignments Tab */}
        <TabsContent value="assignments" className="mt-6">
          {Object.keys(project.dataset_assignments || {}).length === 0 ? (
            <Card className="py-8">
              <CardContent className="flex flex-col items-center text-center">
                <ClipboardList className="h-10 w-10 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">
                  No dataset assignments yet.{' '}
                  {isOwner ? 'Click "Distribute" to assign datasets to members.' : ''}
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Task</TableHead>
                    <TableHead>Dataset</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(project.dataset_assignments).flatMap(([username, tasks]) =>
                    Object.entries(tasks).map(([taskName, info]) => (
                      <TableRow key={`${username}-${taskName}`}>
                        <TableCell className="font-medium">{username}</TableCell>
                        <TableCell>{taskName}</TableCell>
                        <TableCell>{info.dataset_name}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <AddDatasetDialog
        projectId={id!}
        open={showAddDataset}
        onOpenChange={setShowAddDataset}
      />

      <ConfirmDialog
        open={showDistributeConfirm}
        onOpenChange={setShowDistributeConfirm}
        title="Distribute Datasets"
        description="This will automatically assign datasets to all project prompters. Any existing assignments may be updated. Continue?"
        confirmLabel="Distribute"
        loading={distributeMutation.isPending}
        onConfirm={() => distributeMutation.mutate()}
      />

      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Project"
        description="Are you sure you want to delete this project? This action cannot be undone. All associated data will be permanently removed."
        confirmLabel="Delete Project"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </PageLayout>
  );
}
