import datasets
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import models
from django.db.models import OuterRef, Subquery
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)
from django_filters.views import FilterView
from jinja2 import Environment, StrictUndefined
from prompt.filters import DatasetFilter, TaskFilter
from prompt.forms import (
    HFSyncForm,
    LLMTestForm,
    ProjectForm,
    PromptCreateUpdateForm,
    PromptReviewForm,
)
from prompt.models import Dataset, Prompt, PromptingProject, PromptReviewAction, Task
from prompt.utils import (
    generate_ai_prompts,
    send_to_openrouter,
    translate_prompt_with_ai,
)


class TaskListView(LoginRequiredMixin, FilterView, ListView):
    model = Task
    paginate_by = 10
    ordering = "name"
    filterset_class = TaskFilter
    context_object_name = "tasks"
    template_name = "prompt/task_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        filterset = self.filterset_class(self.request.GET, queryset=queryset)
        filtered_qs = filterset.qs
        search_term = self.request.GET.get("name", "")
        if search_term:
            terms = list(filter(None, search_term.split()))
            for term in terms:
                filtered_qs |= queryset.filter(name__icontains=term)
        return filtered_qs

    def get_context_data(self, **kwargs):
        filtered_tasks = self.get_queryset()
        kwargs["object_list"] = filtered_tasks
        context = super().get_context_data(**kwargs)
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(
                self.request,
                "prompt/partials/task_list_table.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class DatasetListView(LoginRequiredMixin, FilterView, ListView):
    model = Dataset
    paginate_by = 10
    ordering = "name"
    filterset_class = DatasetFilter
    context_object_name = "datasets"
    template_name = "prompt/dataset_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        task_pk = self.request.GET.get("task_pk")
        self.task = None
        if task_pk:
            self.task = Task.objects.get(pk=task_pk)
            queryset = queryset.filter(tasks__pk=self.task.pk)
        filterset = self.filterset_class(self.request.GET, queryset=queryset)
        filtered_qs = filterset.qs
        search_term = self.request.GET.get("name", "")
        if search_term:
            terms = list(filter(None, search_term.split()))
            for term in terms:
                filtered_qs |= queryset.filter(name__icontains=term)
        return filtered_qs

    def get_context_data(self, **kwargs):
        filtered_datasets = self.get_queryset()
        kwargs["object_list"] = filtered_datasets
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(
                self.request,
                "prompt/partials/dataset_list_table.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class PromptCreateView(LoginRequiredMixin, CreateView):
    model = Prompt
    form_class = PromptCreateUpdateForm
    template_name = "prompt/prompt_create_update.html"

    def error_redirect(self, request, message):
        default_url = reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.kwargs["dataset_pk"]},
        )
        redirect_link = request.META.get("HTTP_REFERER", default_url)
        messages.error(request, message, extra_tags="danger")
        return redirect(redirect_link)

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.dataset.pk},
        )

    def delete_translated_prompt(self):
        session_key = f"ai_translated_prompts_{self.base_prompt_pk}"
        if session_key in self.request.session:
            self.request.session.pop(session_key)
        return True

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.subset = request.GET.get("subset")
        self.split = request.GET.get("split")
        self.action = request.GET.get("action")
        self.base_prompt_pk = request.GET.get("base_prompt_pk")
        self.session_key = None
        self.task = None
        task_pk = request.GET.get("task_pk")
        if task_pk:
            task_qs = Task.objects.filter(pk=task_pk)
            if task_qs.exists():
                task = task_qs.first()
                if self.dataset in task.datasets.all():
                    self.task = task
        return super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.action == "translate" and self.base_prompt_pk:
            if not request.user.is_moderator:
                return self.error_redirect(
                    request,
                    "This feature is for moderators only for the time being.",
                )
            try:
                self.base_prompt = Prompt.objects.get(pk=self.base_prompt_pk)
                self.session_key = f"ai_translated_prompts_{self.base_prompt_pk}"
            except Prompt.DoesNotExist:
                return self.error_redirect(
                    request=self.request,
                    message="Base prompt not found.",
                )
        elif self.action == "translate":
            return self.error_redirect(
                request=self.request,
                message="Base prompt not specified for translation.",
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get("submit") == "reject":
            self.delete_translated_prompt()
            messages.success(
                request=self.request,
                message="translated prompt rejected successfully",
                extra_tags="success",
            )
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def get_translated_prompt(self):
        if self.session_key not in self.request.session:
            translated_prompt = translate_prompt_with_ai(self.base_prompt.as_dict())
            self.request.session[self.session_key] = translated_prompt.as_dict()
        else:
            translated_prompt = self.request.session[self.session_key]
            translated_prompt["dataset"] = Dataset.objects.get(
                pk=translated_prompt.pop("dataset_pk")
            )
            translated_prompt.pop("dataset_name")
            translated_prompt.pop("task_name")
            task_pk = translated_prompt.pop("task_pk")
            if task_pk:
                translated_prompt["task"] = Task.objects.get(
                    pk=translated_prompt.pop("task_pk")
                )
            translated_prompt = Prompt(**translated_prompt)
        return translated_prompt

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["dataset"] = self.dataset
        kwargs["task"] = self.task
        if self.session_key:
            translated_prompt = self.get_translated_prompt()
            kwargs["instance"] = translated_prompt
            kwargs["initial"]["tags"] = "AI translated"  # should be comma separated
            kwargs["base_prompt"] = self.base_prompt
        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        instance.save()
        form.save_m2m()
        if self.session_key:
            self.request.session.pop(self.session_key)
        if self.request.POST.get("submit") == "submit_for_review":
            # create a submission action
            submission = PromptReviewAction(
                prompt=instance,
                submitter=self.request.user,
                prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
            )
            submission.save()
        messages.success(self.request, "prompt saved successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, form.errors, extra_tags="danger")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["dataset_columns"] = self.dataset.get_columns_names()
        if self.session_key:
            context["add_rejection_button"] = True
        context["task"] = self.task
        return context


class MultiplePromptsCreateView(PromptCreateView):
    template_name = "prompt/multiple_prompts_create.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not request.user.is_moderator:
            return self.error_redirect(
                request,
                "This feature is for moderators only for the time being.",
            )
        self.prompt_index = 0
        try:
            self.prompt_index = int(request.GET.get("prompt_index", 0))
        except ValueError:
            pass
        self.base_prompt_pk = request.GET.get("base_prompt_pk")
        if not self.base_prompt_pk:
            return self.error_redirect(
                request,
                "A seed prompt is required to generate AI prompts.",
            )
        try:
            self.base_prompt = get_object_or_404(
                Prompt,
                pk=self.base_prompt_pk,
                dataset=self.dataset,
            )
        except Http404:
            return self.error_redirect(
                request,
                "The specified seed prompt does not exist or does not belong to this dataset.",
            )
        if not self.base_prompt.is_approved:
            return self.error_redirect(
                request,
                "The prompt needs to approved first.",
            )

    def dispatch(self, request, *args, **kwargs):
        setup_result = self.setup(request, *args, **kwargs)
        if isinstance(setup_result, HttpResponseRedirect):
            return setup_result
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["prompt_index"] = self.prompt_index
        context["ai_prompts_count"] = len(self.get_ai_prompts())
        context["base_prompt"] = self.base_prompt
        context["add_rejection_button"] = True
        return context

    def reject_generated_prompt(self):
        ai_prompts = self.get_ai_prompts()
        if 0 <= self.prompt_index < len(ai_prompts):
            del ai_prompts[self.prompt_index]
            session_key = f"ai_generated_prompts_{self.base_prompt_pk}"
            self.request.session[session_key] = [
                prompt.as_dict() for prompt in ai_prompts
            ]
            if not ai_prompts:
                del self.request.session[session_key]
        return ai_prompts

    def post(self, request, *args, **kwargs):
        if request.POST.get("submit") == "reject":
            self.reject_generated_prompt()
            messages.success(
                request=self.request,
                message="prompt rejected successfully",
                extra_tags="success",
            )
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ai_prompts = self.get_ai_prompts()
        if 0 <= self.prompt_index < len(ai_prompts):
            instance = ai_prompts[self.prompt_index]
            kwargs["instance"] = instance
            kwargs["initial"]["tags"] = "AI generated"  # should be comma separated
            kwargs["base_prompt"] = self.base_prompt
        return kwargs

    def get_ai_prompts(self):
        # this code can be uncommented for debugging
        # if f"ai_generated_prompts_{self.base_prompt_pk}" in self.request.session:
        #     self.request.session.pop(f"ai_generated_prompts_{self.base_prompt_pk}")
        session_key = f"ai_generated_prompts_{self.base_prompt_pk}"
        if (
            session_key not in self.request.session
            and self.request.POST.get("submit") != "reject"
        ):
            ai_prompts = generate_ai_prompts(self.base_prompt.as_dict())
            self.request.session[session_key] = [
                prompt.as_dict() for prompt in ai_prompts
            ]
        else:
            prompt_dicts = self.request.session.get(session_key, [])
            ai_prompts = []
            for prompt_dict in prompt_dicts:
                prompt = {k: v for k, v in prompt_dict.items()}
                prompt["dataset"] = Dataset.objects.get(pk=prompt.pop("dataset_pk"))
                prompt.pop("dataset_name")
                prompt.pop("task_name")
                task_pk = prompt.pop("task_pk")
                if task_pk:
                    prompt["task"] = Task.objects.get(pk=prompt.pop("task_pk"))
                ai_prompts.append(prompt)
            ai_prompts = [Prompt(**prompt) for prompt in ai_prompts]
        return ai_prompts

    def form_valid(self, form):
        response = super().form_valid(form)
        ai_prompts = self.reject_generated_prompt()
        if not ai_prompts:
            messages.success(
                self.request,
                "All AI-generated prompts have been saved.",
            )
            return redirect(
                "prompt:prompt_list",
                dataset_pk=self.object.dataset.pk,
            )
        return response

    def get_success_url(self):
        ai_prompts = self.get_ai_prompts()
        if ai_prompts:
            return (
                reverse_lazy(
                    "prompt:prompt_create_multiple",
                    kwargs={"dataset_pk": self.dataset.pk},
                )
                + f"?base_prompt_pk={self.base_prompt_pk}&prompt_index={min(self.prompt_index, len(ai_prompts) - 1)}"
            )
        else:
            return reverse_lazy(
                "prompt:prompt_list",
                kwargs={"dataset_pk": self.dataset.pk},
            )


class PromptUpdateView(LoginRequiredMixin, UpdateView):
    model = Prompt
    form_class = PromptCreateUpdateForm
    template_name = "prompt/prompt_create_update.html"
    context_object_name = "prompt"

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.dataset.pk},
        )

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.subset = request.GET.get("subset")
        self.split = request.GET.get("split")
        self.task = None
        task_pk = request.GET.get("task_pk")
        if task_pk:
            task_qs = Task.objects.filter(pk=task_pk)
            if task_qs.exists():
                task = task_qs.first()
                if self.dataset in task.datasets.all():
                    self.task = task
        return super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        user = request.user
        prompt = self.get_object()
        if prompt.created_by != user:
            messages.error(
                self.request,
                "You are not allowed to update this prompt.",
                extra_tags="danger",
            )
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.updateable:
            messages.error(
                self.request,
                "prompt cannot be updated after submission.",
                extra_tags="danger",
            )
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["dataset_columns"] = self.dataset.get_columns_names()
        if self.object.dataset_subset:
            context["subset"] = self.object.dataset_subset
        context["task"] = self.task
        return context

    def form_valid(self, form):
        instance = form.save(commit=False)
        success_message = "prompt updated successfully."
        instance.save()
        form.save_m2m()
        if self.request.POST.get("submit") == "submit_for_review":
            # create a submission action
            submission = PromptReviewAction(
                prompt=instance,
                submitter=self.request.user,
                prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
            )
            submission.save()
        messages.success(self.request, success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, form.errors, extra_tags="danger")
        return super().form_invalid(form)


class PromptReviewView(LoginRequiredMixin, CreateView):
    model = PromptReviewAction
    form_class = PromptReviewForm
    template_name = "prompt/prompt_review.html"

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.dataset.pk},
        )

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.prompt = get_object_or_404(Prompt, pk=kwargs["prompt_pk"])
        self.task = None
        task_pk = request.GET.get("task_pk")
        if task_pk:
            task_qs = Task.objects.filter(pk=task_pk)
            if task_qs.exists():
                task = task_qs.first()
                if self.dataset in task.datasets.all():
                    self.task = task
        return super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.prompt.is_approved and not request.user.is_moderator:
            messages.error(
                request,
                "Only reviewers can review prompts.",
                extra_tags="danger",
            )
            return redirect(self.get_success_url())
        if self.prompt.updateable:
            messages.error(
                request,
                "The prompt is still under design and not submitted yet.",
                extra_tags="danger",
            )
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["dataset_columns"] = self.dataset.get_columns_names()
        context["task"] = self.task
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        kwargs["prompt"] = self.prompt
        kwargs["reviewer"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Review action added successfully")
        return super().form_valid(form)


class PromptDeleteView(LoginRequiredMixin, DeleteView):
    model = Prompt

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.dataset.pk},
        )

    def get(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        prompt = self.get_object()
        if not prompt.updateable:
            messages.error(
                request,
                "prompt cannot be deleted after submission.",
                extra_tags="danger",
            )
            return redirect(self.get_success_url())
        return super().delete(request, *args, **kwargs)


class PromptListView(LoginRequiredMixin, ListView):
    model = Prompt
    # paginate_by = 10
    context_object_name = "all_prompts"
    template_name = "prompt/prompt_list.html"

    def get_queryset(self):
        # filter all prompts by dataset
        queryset = super().get_queryset()
        queryset = queryset.filter(dataset__pk=self.kwargs["dataset_pk"])
        # filter out draft prompts
        queryset = queryset.filter(review_actions__isnull=False).distinct()
        if self.task:
            queryset = queryset.filter(task=self.task)
        if not self.request.user.is_moderator:
            queryset = list(filter(lambda prompt: prompt.is_approved, queryset))
            queryset = queryset[:5]
        return queryset

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.task = None
        task_pk = request.GET.get("task_pk", None)
        if task_pk:
            task_qs = Task.objects.filter(pk=task_pk)
            if task_qs.exists():
                task = task_qs.first()
                if self.dataset in task.datasets.all():
                    self.task = task
        return super().setup(request, *args, **kwargs)

    def get_context_data(self):
        context = super().get_context_data()
        context["dataset"] = self.dataset
        context["user_prompts"] = Prompt.objects.filter(
            created_by=self.request.user,
            dataset=self.dataset,
        )
        if self.task:
            context["user_prompts"] = context["user_prompts"].filter(task=self.task)
        context["task"] = self.task

        # get prompts that are available to review

        # Subquery to get the latest PromptReviewAction for each Prompt
        latest_actions = PromptReviewAction.objects.filter(
            prompt=OuterRef("pk")
        ).order_by("-taken_on")

        # Main query to get the Prompts ready for review
        prompts_ready_for_review = Prompt.objects.annotate(
            latest_status=Subquery(latest_actions.values("prompt_status")[:1]),
            latest_decision=Subquery(latest_actions.values("submitter_decision")[:1]),
        ).filter(
            dataset=self.dataset,
            latest_decision__isnull=True,
            latest_status=PromptReviewAction.PromptStatus.SUBMITTED,
        )
        if self.task:
            prompts_ready_for_review = prompts_ready_for_review.filter(task=self.task)
        context["prompts_to_review"] = prompts_ready_for_review
        return context


class UserPromptsListView(LoginRequiredMixin, ListView):
    model = Prompt
    paginate_by = 10
    context_object_name = "prompts"
    template_name = "prompt/user_prompts_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_moderator:
            if self.request.GET.get("show_all_prompts"):
                return queryset
        queryset = queryset.filter(created_by=self.request.user)
        status_order_map = {
            "RETURNED_FOR_MODIFICATION": 0,
            "DRAFT": 1,
            "SUBMITTED": 2,
            "APPROVED": 3,
        }
        queryset = sorted(queryset, key=lambda p: status_order_map[p.status])
        return queryset

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(
                self.request,
                "prompt/partials/user_prompts_list_table.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class DatasetDetailsView(LoginRequiredMixin, View):
    def remap_labels(self, sample, dataset):
        """
        remap the labels to their class names
        """
        features = dataset.get_features()
        for c in sample:
            if features.get(c) and "names" in features[c]:
                label_to_name = {i: name for i, name in enumerate(features[c]["names"])}
                sample[c] = str(sample[c]) + "<<" + label_to_name[sample[c]] + ">>"
        return sample

    def get(self, request, dataset_pk, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=dataset_pk)
        split = request.GET.get("split")
        subset = request.GET.get("subset")
        sample_index = request.GET.get("sample_index")
        if not subset:
            # select the first one by default
            subset = list(dataset.get_configs_details().keys())[0]
        if split:
            config_details = dataset.get_configs_details()[subset]
            samples = config_details[split]["samples"]

            samples = datasets.Dataset.from_dict(samples)
            all_samples_count = config_details[split]["all_samples_count"]
            if sample_index is not None:
                try:
                    sample_index = int(sample_index)
                    sample = samples[sample_index]
                    sample = self.remap_labels(sample, dataset)
                    return JsonResponse({"sample": sample}, safe=False)
                except (ValueError, IndexError):
                    return JsonResponse({"error": "Invalid sample index"}, status=400)

            first_sample = self.remap_labels(samples[0], dataset)

            return JsonResponse(
                {
                    "len_samples": all_samples_count,
                    "max_browse_samples": len(samples),
                    "first_sample": first_sample,
                },
                safe=False,
            )
        return render(
            request,
            "prompt/partials/dataset_details.html",
            {
                "subset": subset,
                "dataset": dataset,
            },
        )


class ApplyTemplateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])

        context = {"dataset": self.dataset}

        subset, split, context = self._get_dataset_config(request, context)
        if "merge_error" in context:
            return self._render_response(request, context)

        template_content = request.POST.get("template", "")
        if not template_content:
            context["merge_error"] = "No template content provided."
            return self._render_response(request, context)

        sample_index = int(request.POST.get("sample_index", 0))
        text_direction = request.GET.get("text_direction", "ltr")
        is_llm_test = request.POST.get("test_with_llm") == "true"

        answer_choices = self._parse_answer_choices(
            request.POST.get("answer_choices", "")
        )

        sample, context = self._get_dataset_sample(subset, split, sample_index, context)
        if "merge_error" in context:
            return self._render_response(request, context)

        context = self._process_template(
            template_content,
            sample,
            answer_choices,
            is_llm_test,
            request,
            context,
        )

        context.update(
            {
                "sample_index": sample_index,
                "template_content": template_content,
                "subset": subset,
                "split": split,
                "text_direction": text_direction,
                "processed_answer_choices": answer_choices,
                "request": request,
                "llm_form": LLMTestForm(user=request.user),
            }
        )

        return self._render_response(request, context)

    def _get_dataset_config(self, request, context):
        # Get subset with fallbacks
        subset = request.GET.get("subset")
        if not subset:
            if self.dataset.default_subset:
                subset = self.dataset.default_subset
            else:
                configs = self.dataset.get_configs_details()
                if configs:
                    subset = next(iter(configs.keys()))
                else:
                    context["merge_error"] = "No dataset subsets available."
                    return None, None, context

        # Get split with fallbacks
        split = request.GET.get("split")
        if not split and subset:
            configs = self.dataset.get_configs_details()
            if configs and subset in configs and configs[subset]:
                split = next(iter(configs[subset].keys()))

        if not split:
            context["merge_error"] = "No split specified."

        return subset, split, context

    def _parse_answer_choices(self, raw_answer_choices):
        """Parse answer choices from various formats."""
        if not raw_answer_choices:
            return []

        if "||" in raw_answer_choices:
            return raw_answer_choices.split("||")
        elif "," in raw_answer_choices:
            return raw_answer_choices.split(",")
        else:
            return [raw_answer_choices]

    def _get_dataset_sample(self, subset, split, sample_index, context):
        """Get the specified dataset sample."""
        try:
            config_details = self.dataset.get_configs_details()[subset]
            samples = config_details[split]["samples"]
            samples_dataset = datasets.Dataset.from_dict(samples)
            sample = samples_dataset[sample_index]
            context["max_samples"] = len(samples_dataset)
            return sample, context
        except (KeyError, IndexError) as e:
            context["merge_error"] = f"Error accessing dataset sample: {str(e)}."
            return None, context

    def _process_template(
        self,
        template_content,
        sample,
        answer_choices,
        is_llm_test,
        request,
        context,
    ):
        try:
            # Apply template to sample
            rendered_sample = self._apply_template(
                template_content,
                sample,
                answer_choices,
            )
            context["rendered_template"] = rendered_sample

            # Check if rendering was successful
            if not isinstance(rendered_sample, str) or not rendered_sample.startswith(
                '<span class = "text-danger">'
            ):
                # Create plain version for LLM if needed
                plain_template = self._create_plain_template(
                    template_content,
                    sample,
                    answer_choices,
                )
                context["plain_template"] = plain_template

                # Process LLM test if requested
                if is_llm_test and plain_template:
                    context = self._process_llm_test(request, plain_template, context)
        except Exception as e:
            context["merge_error"] = f"Error rendering template: {str(e)}"

        return context

    def _apply_template(self, template_content, sample, answer_choices):
        """Apply HTML formatting to template and validate it."""
        # Format the template for HTML display
        html_template = template_content.replace("<br>", "\n")
        html_template = html_template.replace("{{", '<span class = "text-success"> {{')
        html_template = html_template.replace("}}", "}} </span>")

        # Create a copy of the sample with answer choices
        sample_with_choices = sample.copy()
        sample_with_choices["answer_choices"] = answer_choices

        # Validate and render the template
        return self._validate_template(
            template_content, html_template, sample_with_choices
        )

    def _validate_template(self, original_template, html_template, sample):
        if "|||" not in original_template:
            return '<span class = "text-danger"> no ||| dividor </span>'

        try:
            env = Environment(undefined=StrictUndefined)

            # Create template objects
            original_template_obj = env.from_string(original_template)
            html_template_obj = env.from_string(html_template)

            # Render the HTML template
            rendered_template = html_template_obj.render(**sample)
            answer_choices = sample.get("answer_choices", [])

            # Validate answer choices if provided
            if answer_choices:
                rendered_original = original_template_obj.render(**sample)
                answers = rendered_original.split("|||")[-1].strip()

                for answer in answers.split(","):
                    if answer.strip() not in answer_choices:
                        return f'<span class = "text-danger"> The output: {answer} is not a subset of {answer_choices}</span>'

            return rendered_template
        except Exception as e:
            return f'<span class = "text-danger"> Error in template: {str(e)}</span>'

    def _create_plain_template(self, template_content, sample, answer_choices):
        """Create a plain (non-HTML) version of the rendered template."""
        try:
            env = Environment(undefined=StrictUndefined)
            template = env.from_string(template_content)

            # Prepare sample with answer choices
            sample_for_rendering = sample.copy()
            sample_for_rendering["answer_choices"] = answer_choices

            # Render the plain template
            return template.render(**sample_for_rendering)
        except Exception:
            return None

    def _process_llm_test(self, request, plain_template, context):
        """Process LLM testing if requested."""
        model_id = request.POST.get("model")
        if model_id and request.user.openrouter_api_key:
            try:
                # Send to LLM service
                llm_result = send_to_openrouter(
                    plain_template,
                    model_id,
                    request.user.openrouter_api_key,
                )
                context["llm_result"] = llm_result
            except Exception as e:
                context["merge_error"] = f"Error processing LLM request: {str(e)}"

        return context

    def _render_response(self, request, context):
        """Render the response template with context."""
        return render(
            request,
            "prompt/partials/template_merge.html",
            context,
        )


class HFSynchView(LoginRequiredMixin, FormView):
    form_class = HFSyncForm
    template_name = "prompt/hf_sync.html"
    success_url = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(
                request,
                "You do not have permission to access this page.",
                extra_tags="danger",
            )
            return redirect("core:home")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            call_command("sync_with_hf", **data)
        except Exception as e:
            messages.error(self.request, str(e), extra_tags="danger")
            return super().form_invalid(form)
        messages.success(self.request, "HF datasets synchronized successfully")
        return super().form_valid(form)


class DatasetResetCacheView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        dataset.reset_cache()
        messages.success(request, "Dataset cache reset successfully")
        return redirect("prompt:prompt_list", dataset_pk=dataset.pk)


class UserDistributedDatasetsView(LoginRequiredMixin, ListView):
    template_name = "prompt/user_distributed_datasets_list.html"
    context_object_name = "assignments"
    paginate_by = 10  # Adjust this number as needed

    def get_queryset(self):
        user_projects = PromptingProject.objects.filter(prompters=self.request.user)
        assignments = []
        for project in user_projects:
            if self.request.user.username in project.dataset_assignments:
                for task, dataset_info in project.dataset_assignments[
                    self.request.user.username
                ].items():
                    dataset = Dataset.objects.get(name=dataset_info["dataset_name"])
                    has_prompts = Prompt.objects.filter(
                        dataset=dataset,
                        created_by=self.request.user,
                        dataset__prompting_projects__in=[project],
                    ).exists()
                    prompts_count = 0
                    if has_prompts:
                        prompts_query = Prompt.objects.filter(
                            dataset=dataset,
                            created_by=self.request.user,
                            dataset__prompting_projects__in=[project],
                        )
                        last_prompt = prompts_query.last()
                        prompts_count = prompts_query.count()

                    assignments.append(
                        {
                            "project": project,
                            "task": task,
                            "dataset_name": dataset_info["dataset_name"],
                            "dataset_pk": dataset.pk,
                            "status": last_prompt.status if has_prompts else "Pending",
                            "last_prompt": last_prompt if has_prompts else None,
                            "prompts_count": prompts_count,
                        }
                    )
        return assignments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(self.object_list, self.paginate_by)
        page = self.request.GET.get("page")
        assignments = paginator.get_page(page)
        context["assignments"] = assignments
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = PromptingProject
    form_class = ProjectForm
    template_name = "prompt/project_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("prompt:project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(
            self.request, f"Project '{form.instance.name}' created successfully!"
        )
        return super().form_valid(form)


class ProjectListView(LoginRequiredMixin, ListView):
    model = PromptingProject
    template_name = "prompt/project_list.html"
    context_object_name = "projects"
    paginate_by = 9  # Show 9 projects per page (3 columns x 3 rows)

    def get_queryset(self):
        # Show projects where user is owner or prompter
        user = self.request.user
        queryset = PromptingProject.objects.filter(
            models.Q(owner=user) | models.Q(prompters=user)
        ).distinct()

        # Handle search
        search_query = self.request.GET.get("search", "")
        if search_query:
            queryset = queryset.filter(
                models.Q(name__icontains=search_query)
                | models.Q(description__icontains=search_query)
            ).distinct()

        # Sort options
        sort_by = self.request.GET.get("sort", "name")
        if sort_by == "name":
            queryset = queryset.order_by("name")
        elif sort_by == "newest":
            queryset = queryset.order_by(
                "-id"
            )  # Assuming id increases with newer projects
        elif sort_by == "datasets":
            # Using annotation to count related datasets
            from django.db.models import Count

            queryset = queryset.annotate(dataset_count=Count("datasets")).order_by(
                "-dataset_count"
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass search and sort parameters to maintain state
        context["search_query"] = self.request.GET.get("search", "")
        context["current_sort"] = self.request.GET.get("sort", "name")
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = PromptingProject
    template_name = "prompt/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()

        # Calculate prompt count for statistics
        prompt_count = (
            Prompt.objects.filter(dataset__in=project.datasets.all()).distinct().count()
        )
        context["prompt_count"] = prompt_count

        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user has access to this project
        project = self.get_object()
        user = request.user

        if (
            user == project.owner
            or user in project.prompters.all()
            or user.is_superuser
        ):
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You don't have access to this project.")
        return redirect("prompt:project_list")


class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = PromptingProject
    form_class = ProjectForm
    template_name = "prompt/project_update.html"

    def test_func(self):
        project = self.get_object()
        return self.request.user == project.owner or self.request.user.is_superuser

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("prompt:project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Project '{form.instance.name}' updated successfully!",
        )
        return super().form_valid(form)


class ProjectDistributeView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        project = get_object_or_404(PromptingProject, pk=self.kwargs["pk"])
        return self.request.user == project.owner or self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(PromptingProject, pk=self.kwargs["pk"])

        try:
            result = project.distribute_datasets()
            messages.success(request, result)
        except Exception as e:
            messages.error(request, f"Error distributing datasets: {str(e)}")

        return redirect("prompt:project_detail", pk=project.pk)
