export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_moderator?: boolean;
  masked_openrouter_api_key: string | null;
}

export interface Task {
  id: number;
  name: string;
  prompt_count: number;
}

export interface Dataset {
  id: number;
  name: string;
  huggingface_name: string;
  description: string;
  primary_task: Task | null;
  prompt_count: number;
  huggingface_link: string;
  is_single_classification: boolean;
  target_column: string;
}

export interface DatasetDetail extends Dataset {
  tasks: Task[];
  configs_details: Record<string, Record<string, { all_samples_count: number; samples: Record<string, unknown[]> }>>;
  features: Record<string, unknown>;
  columns_names: string[];
  subsets: string;
  default_subset: string;
  download_only_the_default_subset: boolean;
  configs_with_splits: Record<string, string[]>;
}

export interface Prompt {
  id: number;
  name: string;
  template: string;
  text_direction: 'ltr' | 'rtl';
  dataset: number;
  dataset_name: string;
  dataset_huggingface_name: string;
  dataset_subset: string;
  created_by: { id: number; username: string; email: string };
  created_on: string;
  last_updated_on: string;
  tags: string[];
  task: number | null;
  task_name: string | null;
  status: string;
  answer_choices: string;
  answer_choices_list: string[];
  updateable: boolean;
  reviewable: boolean;
  is_approved: boolean;
  base_prompt: number | null;
  review_actions?: ReviewAction[];
}

export interface ReviewAction {
  id: number;
  submitter: { id: number; username: string; email: string };
  prompt_status: string;
  submitter_comment: string | null;
  submitter_decision: string | null;
  submitter_decision_display: string;
  prompt_before_submitter_modifications: Record<string, unknown> | null;
  taken_on: string;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  owner: { id: number; username: string; email: string };
  datasets_count: number;
  members_count: number;
  user_role: 'owner' | 'prompter' | 'reviewer' | null;
  minimum_prompts_per_prompter: number;
}

export interface ProjectDetail extends Project {
  prompters: User[];
  reviewers: User[];
  datasets: Dataset[];
  dataset_assignments: Record<string, Record<string, { dataset_name: string }>>;
  secret_key: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LLMResult {
  success: boolean;
  result?: {
    content: string;
    model: string;
    usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
    finish_reason: string;
  };
  error?: string;
}

export interface DatasetValidation {
  valid: boolean;
  name?: string;
  huggingface_name?: string;
  description?: string;
  tags?: string[];
  downloads?: number;
  likes?: number;
  configs?: string[];
  size_warning?: string;
  error?: string;
}

export interface TemplatePreview {
  rendered_template: string;
  plain_template: string;
  sample_index: number;
  max_samples: number;
  processed_answer_choices: string[];
  llm_result?: LLMResult;
}
