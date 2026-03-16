import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Sparkles,
  Check,
  X,
  Loader2,
  Search,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Prompt, PaginatedResponse, DatasetDetail } from '@/types';

interface GeneratedPrompt {
  name: string;
  template: string;
  text_direction: 'ltr' | 'rtl';
  answer_choices: string;
  tags: string[];
}

type PromptStatus = 'pending' | 'saved' | 'rejected';

export default function MultiPromptCreate() {
  const { datasetId } = useParams<{ datasetId: string }>();

  // Step tracking
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [generatedPrompts, setGeneratedPrompts] = useState<GeneratedPrompt[]>([]);
  const [promptStatuses, setPromptStatuses] = useState<PromptStatus[]>([]);
  const [activeVariantTab, setActiveVariantTab] = useState('0');

  // Fetch dataset
  const { data: dataset } = useQuery<DatasetDetail>({
    queryKey: ['dataset-detail', datasetId],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  // Fetch existing prompts for step 1
  const { data: promptsData, isLoading: promptsLoading } = useQuery<
    PaginatedResponse<Prompt>
  >({
    queryKey: ['prompts-for-bulk', datasetId, searchQuery],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('tab', 'all');
      if (searchQuery) params.set('search', searchQuery);
      const res = await api.get(
        `/datasets/${datasetId}/prompts/?${params.toString()}`
      );
      return res.data;
    },
    enabled: !!datasetId && step === 1,
  });

  // Generate AI variants mutation
  const generateMutation = useMutation({
    mutationFn: async (basePromptId: number) => {
      const res = await api.post(
        `/datasets/${datasetId}/prompts/create-multiple/`,
        { base_prompt_id: basePromptId }
      );
      return res.data;
    },
    onSuccess: (data) => {
      const prompts: GeneratedPrompt[] = Array.isArray(data)
        ? data
        : data.prompts || data.results || [];
      setGeneratedPrompts(prompts);
      setPromptStatuses(prompts.map(() => 'pending' as PromptStatus));
      setActiveVariantTab('0');
      setStep(3);
      toast.success(`Generated ${prompts.length} prompt variants.`);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : 'Failed to generate variants.';
      toast.error(message);
    },
  });

  // Save generated prompt mutation
  const saveMutation = useMutation({
    mutationFn: async ({
      promptData,
      index,
    }: {
      promptData: GeneratedPrompt;
      index: number;
    }) => {
      const res = await api.post(
        `/datasets/${datasetId}/prompts/save-generated/`,
        {
          ...promptData,
          base_prompt: selectedPromptId,
        }
      );
      return { data: res.data, index };
    },
    onSuccess: ({ index }) => {
      setPromptStatuses((prev) => {
        const updated = [...prev];
        updated[index] = 'saved';
        return updated;
      });
      toast.success(`Prompt ${index + 1} saved successfully.`);
      navigateToNextUnsaved(index);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : 'Failed to save prompt.';
      toast.error(message);
    },
  });

  // Reject generated prompt mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ index }: { index: number }) => {
      const res = await api.post(
        `/datasets/${datasetId}/prompts/reject-generated/`,
        { index }
      );
      return { data: res.data, index };
    },
    onSuccess: ({ index }) => {
      setPromptStatuses((prev) => {
        const updated = [...prev];
        updated[index] = 'rejected';
        return updated;
      });
      toast.success(`Prompt ${index + 1} rejected.`);
      navigateToNextUnsaved(index);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : 'Failed to reject prompt.';
      toast.error(message);
    },
  });

  const navigateToNextUnsaved = (currentIndex: number) => {
    const nextIndex = promptStatuses.findIndex(
      (status, i) => i > currentIndex && status === 'pending'
    );
    if (nextIndex !== -1) {
      setActiveVariantTab(String(nextIndex));
    } else {
      // Try wrapping around
      const wrapIndex = promptStatuses.findIndex(
        (status, i) => i < currentIndex && status === 'pending'
      );
      if (wrapIndex !== -1) {
        setActiveVariantTab(String(wrapIndex));
      }
    }
  };

  const handleSelectBasePrompt = (promptId: number) => {
    setSelectedPromptId(promptId);
    setStep(2);
  };

  const handleGenerate = () => {
    if (selectedPromptId) {
      generateMutation.mutate(selectedPromptId);
    }
  };

  const selectedPrompt = promptsData?.results.find(
    (p) => p.id === selectedPromptId
  );

  return (
    <PageLayout
      title="Generate AI Prompts"
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
        { label: 'Generate AI Prompts' },
      ]}
    >
      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-8">
        {[
          { num: 1, label: 'Select Base Prompt' },
          { num: 2, label: 'Generate Variants' },
          { num: 3, label: 'Review & Save' },
        ].map((s, i) => (
          <div key={s.num} className="flex items-center gap-2">
            {i > 0 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
            <div
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${
                step === s.num
                  ? 'bg-primary text-primary-foreground'
                  : step > s.num
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                    : 'bg-muted text-muted-foreground'
              }`}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-xs">
                {step > s.num ? (
                  <Check className="h-3 w-3" />
                ) : (
                  s.num
                )}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Step 1: Select Base Prompt */}
      {step === 1 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Select a Base Prompt
              </CardTitle>
              <CardDescription>
                Choose an existing prompt to generate AI variants from.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search prompts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>

              {promptsLoading && (
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              )}

              {promptsData && promptsData.results.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-6">
                  No prompts found. Create a prompt first.
                </p>
              )}

              {promptsData && promptsData.results.length > 0 && (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {promptsData.results.map((prompt) => (
                    <button
                      key={prompt.id}
                      onClick={() => handleSelectBasePrompt(prompt.id)}
                      className={`w-full text-left rounded-lg border p-3 transition-colors hover:border-primary ${
                        selectedPromptId === prompt.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">
                          {prompt.name}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {prompt.created_by.username}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2 font-mono">
                        {prompt.template}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 2: Confirm and Generate */}
      {step === 2 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Generate AI Variants
              </CardTitle>
              <CardDescription>
                Review the selected base prompt and generate variants.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedPrompt && (
                <div className="rounded-md border bg-muted/50 p-4 space-y-2">
                  <p className="text-sm font-medium">
                    {selectedPrompt.name}
                  </p>
                  <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono">
                    {selectedPrompt.template}
                  </pre>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {selectedPrompt.tags.map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="text-xs"
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={() => setStep(1)}
                >
                  Back
                </Button>
                <Button
                  disabled={generateMutation.isPending}
                  onClick={handleGenerate}
                >
                  {generateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Generate Variants
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 3: Review generated prompts */}
      {step === 3 && generatedPrompts.length > 0 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Review Generated Prompts
              </CardTitle>
              <CardDescription>
                Review each generated variant. Save the ones you want to
                keep.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs
                value={activeVariantTab}
                onValueChange={setActiveVariantTab}
              >
                <TabsList className="mb-4">
                  {generatedPrompts.map((_, i) => (
                    <TabsTrigger
                      key={i}
                      value={String(i)}
                      className="relative"
                    >
                      Prompt {i + 1}
                      {promptStatuses[i] === 'saved' && (
                        <Check className="ml-1 h-3 w-3 text-green-600" />
                      )}
                      {promptStatuses[i] === 'rejected' && (
                        <X className="ml-1 h-3 w-3 text-red-500" />
                      )}
                    </TabsTrigger>
                  ))}
                </TabsList>

                {generatedPrompts.map((gp, i) => (
                  <TabsContent key={i} value={String(i)}>
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <p className="text-sm font-medium">Name</p>
                        <p className="text-sm rounded-md border bg-muted/50 p-3">
                          {gp.name}
                        </p>
                      </div>

                      <div className="space-y-2">
                        <p className="text-sm font-medium">Template</p>
                        <pre
                          className="text-sm rounded-md border bg-muted/50 p-3 whitespace-pre-wrap font-mono max-h-[300px] overflow-y-auto"
                          dir={gp.text_direction}
                        >
                          {gp.template}
                        </pre>
                      </div>

                      {gp.answer_choices && (
                        <div className="space-y-2">
                          <p className="text-sm font-medium">
                            Answer Choices
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {gp.answer_choices}
                          </p>
                        </div>
                      )}

                      {gp.tags && gp.tags.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-sm font-medium">Tags</p>
                          <div className="flex flex-wrap gap-1">
                            {gp.tags.map((tag) => (
                              <Badge
                                key={tag}
                                variant="secondary"
                                className="text-xs"
                              >
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      <Separator />

                      <div className="flex items-center gap-3">
                        {promptStatuses[i] === 'pending' ? (
                          <>
                            <Button
                              disabled={
                                saveMutation.isPending ||
                                rejectMutation.isPending
                              }
                              onClick={() =>
                                saveMutation.mutate({
                                  promptData: gp,
                                  index: i,
                                })
                              }
                            >
                              {saveMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Check className="h-4 w-4" />
                              )}
                              Save
                            </Button>
                            <Button
                              variant="outline"
                              disabled={
                                saveMutation.isPending ||
                                rejectMutation.isPending
                              }
                              onClick={() =>
                                rejectMutation.mutate({ index: i })
                              }
                            >
                              {rejectMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <X className="h-4 w-4" />
                              )}
                              Reject
                            </Button>
                          </>
                        ) : (
                          <Badge
                            variant={
                              promptStatuses[i] === 'saved'
                                ? 'default'
                                : 'secondary'
                            }
                            className={
                              promptStatuses[i] === 'saved'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                            }
                          >
                            {promptStatuses[i] === 'saved'
                              ? 'Saved'
                              : 'Rejected'}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>

          {/* Summary / Done */}
          {promptStatuses.every((s) => s !== 'pending') && (
            <Card>
              <CardContent className="py-6 text-center space-y-3">
                <p className="text-sm font-medium">
                  All prompts have been reviewed.
                </p>
                <p className="text-xs text-muted-foreground">
                  {promptStatuses.filter((s) => s === 'saved').length} saved,{' '}
                  {promptStatuses.filter((s) => s === 'rejected').length}{' '}
                  rejected
                </p>
                <Button asChild>
                  <Link to={`/app/datasets/${datasetId}/prompts`}>
                    Back to Prompts
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </PageLayout>
  );
}
