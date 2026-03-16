import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import PageLayout from '@/components/layout/PageLayout';
import StatusBadge from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/components/ui/card';
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
  Check,
  RotateCcw,
  Send,
  Loader2,
  Clock,
  User,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Prompt, Task, ReviewAction, DatasetDetail } from '@/types';

export default function PromptReview() {
  const { datasetId, id } = useParams<{ datasetId: string; id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [template, setTemplate] = useState('');
  const [textDirection, setTextDirection] = useState<'ltr' | 'rtl'>('ltr');
  const [answerChoices, setAnswerChoices] = useState('');
  const [tags, setTags] = useState('');
  const [taskId, setTaskId] = useState<string>('');
  const [datasetSubset, setDatasetSubset] = useState('');
  const [decision, setDecision] = useState<string>('');
  const [comment, setComment] = useState('');

  const { data: prompt, isLoading: promptLoading } = useQuery<Prompt>({
    queryKey: ['prompt-review', datasetId, id],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/prompts/${id}/`);
      return res.data;
    },
    enabled: !!datasetId && !!id,
  });

  const { data: dataset } = useQuery<DatasetDetail>({
    queryKey: ['dataset-detail', datasetId],
    queryFn: async () => {
      const res = await api.get(`/datasets/${datasetId}/`);
      return res.data;
    },
    enabled: !!datasetId,
  });

  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await api.get('/tasks/');
      return res.data.results || res.data;
    },
  });

  useEffect(() => {
    if (prompt) {
      setName(prompt.name);
      setTemplate(prompt.template);
      setTextDirection(prompt.text_direction);
      setAnswerChoices(
        prompt.answer_choices_list?.join(', ') || prompt.answer_choices || ''
      );
      setTags(prompt.tags?.join(', ') || '');
      setTaskId(prompt.task ? String(prompt.task) : '');
      setDatasetSubset(prompt.dataset_subset || '');
    }
  }, [prompt]);

  const subsets = dataset?.configs_with_splits
    ? Object.keys(dataset.configs_with_splits)
    : [];

  const reviewMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        submitter_decision: decision,
        submitter_comment: comment,
        name,
        template,
        text_direction: textDirection,
        answer_choices: answerChoices,
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
        task: taskId ? parseInt(taskId, 10) : null,
        dataset_subset: datasetSubset,
      };
      const res = await api.post(
        `/datasets/${datasetId}/prompts/${id}/review/`,
        payload
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success('Review submitted successfully.');
      queryClient.invalidateQueries({ queryKey: ['prompt-review', datasetId, id] });
      queryClient.invalidateQueries({ queryKey: ['prompts', datasetId] });
      navigate(`/app/datasets/${datasetId}/prompts`);
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Failed to submit review.';
      toast.error(message);
    },
  });

  const handleSubmitReview = () => {
    if (!decision) {
      toast.error('Please select a decision.');
      return;
    }
    if (decision === 'return' && !comment.trim()) {
      toast.error('Please provide a comment when returning for modification.');
      return;
    }
    reviewMutation.mutate();
  };

  if (promptLoading) {
    return (
      <PageLayout
        title=""
        breadcrumbs={[
          { label: 'Projects', href: '/app/projects' },
          { label: '...' },
          { label: 'Loading...' },
        ]}
      >
        <div className="space-y-4 max-w-4xl">
          <Skeleton className="h-10 w-1/2" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </PageLayout>
    );
  }

  if (!prompt) {
    return (
      <PageLayout
        title="Error"
        breadcrumbs={[
          { label: 'Projects', href: '/app/projects' },
          { label: 'Error' },
        ]}
      >
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">Prompt not found.</p>
          </CardContent>
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title="Review Prompt"
      breadcrumbs={[
        { label: 'Projects', href: '/app/projects' },
        { label: dataset?.name || 'Dataset', href: `/app/datasets/${datasetId}` },
        { label: 'Prompts', href: `/app/datasets/${datasetId}/prompts` },
        { label: 'Review' },
      ]}
    >
      <div className="max-w-4xl space-y-6">
        {/* Prompt Info Header */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{prompt.name}</CardTitle>
                <CardDescription className="mt-1">
                  Created by {prompt.created_by.username} on{' '}
                  {new Date(prompt.created_on).toLocaleDateString()}
                </CardDescription>
              </div>
              <StatusBadge status={prompt.status} />
            </div>
          </CardHeader>
        </Card>

        {/* Editable Fields */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Prompt Details</CardTitle>
            <CardDescription>
              You can modify these fields as part of the review.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="review-name">Name</Label>
              <Input
                id="review-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="review-template">Template</Label>
              <Textarea
                id="review-template"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                className="min-h-[180px] font-mono text-sm"
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
              <Label htmlFor="review-answer-choices">Answer Choices</Label>
              <Input
                id="review-answer-choices"
                value={answerChoices}
                onChange={(e) => setAnswerChoices(e.target.value)}
                placeholder="Comma-separated answer choices"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="review-tags">Tags</Label>
              <Input
                id="review-tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Comma-separated tags"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Task</Label>
                <Select value={taskId} onValueChange={setTaskId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select task" />
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
                  <Select value={datasetSubset} onValueChange={setDatasetSubset}>
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
            </div>
          </CardContent>
        </Card>

        {/* Review Decision */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Review Decision</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-3">
              <Label>Decision *</Label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  type="button"
                  variant={decision === 'approve' ? 'default' : 'outline'}
                  className={
                    decision === 'approve'
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : ''
                  }
                  onClick={() => setDecision('approve')}
                >
                  <Check className="h-4 w-4" />
                  Approve
                </Button>
                <Button
                  type="button"
                  variant={decision === 'return' ? 'default' : 'outline'}
                  className={
                    decision === 'return'
                      ? 'bg-orange-600 hover:bg-orange-700 text-white'
                      : ''
                  }
                  onClick={() => setDecision('return')}
                >
                  <RotateCcw className="h-4 w-4" />
                  Return for Modification
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="review-comment">
                Comment{decision === 'return' ? ' *' : ''}
              </Label>
              <Textarea
                id="review-comment"
                placeholder={
                  decision === 'return'
                    ? 'Explain what needs to be modified (required)...'
                    : 'Optional review comment...'
                }
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="min-h-[100px]"
              />
            </div>

            <Button
              disabled={reviewMutation.isPending || !decision}
              onClick={handleSubmitReview}
              className="w-full sm:w-auto"
            >
              {reviewMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Submit Review
            </Button>
          </CardContent>
        </Card>

        {/* Review History */}
        {prompt.review_actions && prompt.review_actions.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Review History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {prompt.review_actions.map((action: ReviewAction) => (
                  <div key={action.id} className="flex gap-3 text-sm">
                    <div className="flex-shrink-0 mt-0.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                        {action.submitter_decision === 'approve' ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : action.submitter_decision === 'return' ? (
                          <RotateCcw className="h-4 w-4 text-orange-600" />
                        ) : (
                          <User className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">
                          {action.submitter.username}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {action.submitter_decision_display}
                        </Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(action.taken_on).toLocaleString()}
                        </span>
                      </div>
                      {action.submitter_comment && (
                        <p className="text-muted-foreground mt-1">
                          {action.submitter_comment}
                        </p>
                      )}
                      {action.prompt_status && (
                        <div className="mt-1">
                          <StatusBadge status={action.prompt_status} />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </PageLayout>
  );
}
