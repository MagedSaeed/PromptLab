import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  AlignLeft,
  AlignRight,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Play,
  Send,
  Save,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import type { DatasetDetail, Task, Prompt, TemplatePreview } from '@/types';

interface OpenRouterModel {
  id: string;
  name: string;
}

export default function PromptForm() {
  const { datasetId, id } = useParams<{ datasetId: string; id: string }>();
  const navigate = useNavigate();
  const isEditMode = !!id;

  const [name, setName] = useState('');
  const [template, setTemplate] = useState('');
  const [textDirection, setTextDirection] = useState<'ltr' | 'rtl'>('ltr');
  const [answerChoices, setAnswerChoices] = useState('');
  const [tags, setTags] = useState('');
  const [taskId, setTaskId] = useState<string>('');
  const [datasetSubset, setDatasetSubset] = useState('');
  const [sampleIndex, setSampleIndex] = useState(0);
  const [selectedModel, setSelectedModel] = useState('');
  const [datasetInfoOpen, setDatasetInfoOpen] = useState(true);

  const { data: dataset, isLoading: datasetLoading } = useQuery<DatasetDetail>({
    queryKey: ['dataset-detail', datasetId],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  const { data: existingPrompt, isLoading: promptLoading } = useQuery<Prompt>({
    queryKey: ['prompt', datasetId, id],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/prompts/${id}/`);
      return res.data;
    },
    enabled: isEditMode,
  });

  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await api.get('/tasks/');
      return res.data.results || res.data;
    },
  });

  const { data: models } = useQuery<OpenRouterModel[]>({
    queryKey: ['openrouter-models'],
    queryFn: async () => {
      const res = await api.get('/openrouter/models/');
      return res.data;
    },
  });

  useEffect(() => {
    if (existingPrompt) {
      setName(existingPrompt.name);
      setTemplate(existingPrompt.template);
      setTextDirection(existingPrompt.text_direction);
      setAnswerChoices(
        existingPrompt.answer_choices_list?.join(', ') ||
          existingPrompt.answer_choices ||
          ''
      );
      setTags(existingPrompt.tags?.join(', ') || '');
      setTaskId(existingPrompt.task ? String(existingPrompt.task) : '');
      setDatasetSubset(existingPrompt.dataset_subset || '');
    }
  }, [existingPrompt]);

  useEffect(() => {
    if (dataset && !isEditMode && dataset.default_subset) {
      setDatasetSubset(dataset.default_subset);
    }
  }, [dataset, isEditMode]);

  const previewMutation = useMutation<
    TemplatePreview,
    Error,
    { testWithLlm?: boolean }
  >({
    mutationFn: async ({ testWithLlm = false }) => {
      const splits = dataset?.configs_with_splits;
      const subset = datasetSubset || dataset?.default_subset || '';
      const split =
        splits && subset && splits[subset] ? splits[subset][0] : '';

      const body: Record<string, unknown> = {
        template,
        answer_choices: answerChoices,
        sample_index: sampleIndex,
        subset,
        split,
        text_direction: textDirection,
      };

      if (testWithLlm && selectedModel) {
        body.test_with_llm = true;
        body.llm_model = selectedModel;
      }

      const res = await api.post(
        `/datasets/${datasetId}/prompts/apply-template/`,
        body
      );
      return res.data;
    },
  });

  const handlePreview = useCallback(
    (testWithLlm = false) => {
      if (!template.trim()) {
        toast.error('Please enter a template before previewing.');
        return;
      }
      previewMutation.mutate({ testWithLlm });
    },
    [template, previewMutation]
  );

  const saveMutation = useMutation({
    mutationFn: async (submitForReview: boolean) => {
      const payload = {
        name,
        template,
        text_direction: textDirection,
        answer_choices: answerChoices,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        task: taskId ? parseInt(taskId, 10) : null,
        dataset_subset: datasetSubset,
        submit_for_review: submitForReview,
      };

      if (isEditMode) {
        const res = await api.put(
          `/datasets/${datasetId}/prompts/${id}/`,
          payload
        );
        return res.data;
      }
      const res = await api.post(
        `/datasets/${datasetId}/prompts/`,
        payload
      );
      return res.data;
    },
    onSuccess: (_data, submitForReview) => {
      toast.success(
        submitForReview
          ? 'Prompt saved and submitted for review.'
          : isEditMode
            ? 'Prompt updated successfully.'
            : 'Prompt saved as draft.'
      );
      navigate(`/app/datasets/${datasetId}/prompts`);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : 'Failed to save prompt.';
      toast.error(message);
    },
  });

  const insertColumnIntoTemplate = (column: string) => {
    setTemplate((prev) => `${prev}{{ ${column} }}`);
  };

  const subsets = dataset?.configs_with_splits
    ? Object.keys(dataset.configs_with_splits)
    : [];

  if (datasetLoading || (isEditMode && promptLoading)) {
    return (
      <PageLayout
        title=""
        breadcrumbs={[
          { label: 'Projects', href: '/app/projects' },
          { label: '...' },
          { label: 'Loading...' },
        ]}
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={isEditMode ? 'Edit Prompt' : 'New Prompt'}
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        {
          label: dataset?.name || 'Dataset',
          href: `/app/datasets/${datasetId}`,
        },
        {
          label: 'Prompts',
          href: `/app/datasets/${datasetId}/prompts`,
        },
        { label: isEditMode ? 'Edit' : 'New' },
      ]}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COLUMN - Main Form */}
        <div className="lg:col-span-2 space-y-6">
          <div className="space-y-2">
            <Label htmlFor="prompt-name">Name *</Label>
            <Input
              id="prompt-name"
              placeholder="Enter a descriptive name for this prompt"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt-template">Template *</Label>
            {/* TODO: Replace with PromptEditor component */}
            <Textarea
              id="prompt-template"
              placeholder="Write your prompt template here. Use {{ column_name }} to insert dataset columns."
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="min-h-[200px] font-mono text-sm"
              dir={textDirection}
            />
          </div>

          <div className="space-y-2">
            <Label>Text Direction</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant={textDirection === 'ltr' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTextDirection('ltr')}
              >
                <AlignLeft className="h-4 w-4 mr-1" />
                LTR
              </Button>
              <Button
                type="button"
                variant={textDirection === 'rtl' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTextDirection('rtl')}
              >
                <AlignRight className="h-4 w-4 mr-1" />
                RTL
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="answer-choices">Answer Choices</Label>
            <Input
              id="answer-choices"
              placeholder="Enter comma-separated answer choices (e.g. Yes, No, Maybe)"
              value={answerChoices}
              onChange={(e) => setAnswerChoices(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Separate multiple choices with commas.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              placeholder="Enter comma-separated tags (e.g. classification, sentiment)"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Separate multiple tags with commas.
            </p>
          </div>

          <div className="space-y-2">
            <Label>Task</Label>
            <Select value={taskId} onValueChange={setTaskId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a task (optional)" />
              </SelectTrigger>
              <SelectContent>
                {tasks?.map((task) => (
                  <SelectItem key={task.id} value={String(task.id)}>
                    {task.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {subsets.length > 1 && (
            <div className="space-y-2">
              <Label>Dataset Subset</Label>
              <Select
                value={datasetSubset}
                onValueChange={setDatasetSubset}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select subset" />
                </SelectTrigger>
                <SelectContent>
                  {subsets.map((subset) => (
                    <SelectItem key={subset} value={subset}>
                      {subset}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <Separator />

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              disabled={
                saveMutation.isPending ||
                !name.trim() ||
                !template.trim()
              }
              onClick={() => saveMutation.mutate(false)}
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save as Draft
            </Button>
            <Button
              disabled={
                saveMutation.isPending ||
                !name.trim() ||
                !template.trim()
              }
              onClick={() => saveMutation.mutate(true)}
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Save &amp; Submit for Review
            </Button>
          </div>
        </div>

        {/* RIGHT COLUMN - Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              className="cursor-pointer select-none"
              onClick={() => setDatasetInfoOpen(!datasetInfoOpen)}
            >
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Dataset Info</CardTitle>
                {datasetInfoOpen ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            {datasetInfoOpen && dataset && (
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium">{dataset.name}</p>
                  <a
                    href={dataset.huggingface_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline inline-flex items-center gap-1 mt-1"
                  >
                    {dataset.huggingface_name}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <Separator />

                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    Available Columns
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {dataset.columns_names?.map((col) => (
                      <Badge
                        key={col}
                        variant="secondary"
                        className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors text-xs"
                        onClick={() => insertColumnIntoTemplate(col)}
                      >
                        {col}
                      </Badge>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Click a column to insert it into the template.
                  </p>
                </div>

                {subsets.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        Configs / Splits
                      </p>
                      <div className="text-xs text-muted-foreground space-y-1">
                        {Object.entries(
                          dataset.configs_with_splits || {}
                        ).map(([config, splits]) => (
                          <div key={config}>
                            <span className="font-medium text-foreground">
                              {config}
                            </span>
                            {': '}
                            {(splits as string[]).join(', ')}
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Template Preview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={
                  previewMutation.isPending || !template.trim()
                }
                onClick={() => handlePreview(false)}
              >
                {previewMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Preview Template
              </Button>

              {previewMutation.data && (
                <>
                  <div
                    className="rounded-md border bg-muted/50 p-3 text-sm whitespace-pre-wrap max-h-[300px] overflow-y-auto"
                    dir={textDirection}
                  >
                    {previewMutation.data.rendered_template}
                  </div>

                  <div className="flex items-center justify-between">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={sampleIndex <= 0}
                      onClick={() =>
                        setSampleIndex((prev) => prev - 1)
                      }
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Prev
                    </Button>
                    <span className="text-xs text-muted-foreground">
                      Sample {sampleIndex + 1} /{' '}
                      {previewMutation.data.max_samples}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={
                        sampleIndex >=
                        previewMutation.data.max_samples - 1
                      }
                      onClick={() =>
                        setSampleIndex((prev) => prev + 1)
                      }
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>

                  {previewMutation.data.processed_answer_choices &&
                    previewMutation.data.processed_answer_choices
                      .length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Answer Choices
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {previewMutation.data.processed_answer_choices.map(
                            (choice, i) => (
                              <Badge
                                key={i}
                                variant="outline"
                                className="text-xs"
                              >
                                {choice}
                              </Badge>
                            )
                          )}
                        </div>
                      </div>
                    )}
                </>
              )}

              <Separator />

              <div className="space-y-3">
                <p className="text-xs font-medium text-muted-foreground">
                  Test with LLM
                </p>
                <Select
                  value={selectedModel}
                  onValueChange={setSelectedModel}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {models?.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  disabled={
                    previewMutation.isPending ||
                    !template.trim() ||
                    !selectedModel
                  }
                  onClick={() => handlePreview(true)}
                >
                  {previewMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Test with LLM
                </Button>

                {previewMutation.data?.llm_result && (
                  <div className="space-y-2">
                    {previewMutation.data.llm_result.success ? (
                      <div className="rounded-md border bg-muted/50 p-3">
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          LLM Response (
                          {
                            previewMutation.data.llm_result.result
                              ?.model
                          }
                          )
                        </p>
                        <p
                          className="text-sm whitespace-pre-wrap"
                          dir={textDirection}
                        >
                          {
                            previewMutation.data.llm_result.result
                              ?.content
                          }
                        </p>
                        {previewMutation.data.llm_result.result
                          ?.usage && (
                          <p className="text-xs text-muted-foreground mt-2">
                            Tokens:{' '}
                            {
                              previewMutation.data.llm_result.result
                                .usage.total_tokens
                            }
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                        <p className="text-sm text-destructive">
                          {previewMutation.data.llm_result.error ||
                            'LLM request failed.'}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
