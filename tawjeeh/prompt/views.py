from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.management import call_command
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    UpdateView,
    View,
)
from django_filters.views import FilterView
from jinja2 import Template
from prompt.filters import DatasetFilter, TaskFilter
from prompt.forms import HFSyncForm, PromptCreateUpdateForm, PromptReviewForm
from prompt.models import Dataset, Prompt, PromptReviewAction, Task


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

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.object.dataset.pk},
        )

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.subset = request.GET.get("subset")
        self.split = request.GET.get("split")
        return super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["dataset_columns"] = self.dataset.get_columns_names()
        return context

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["dataset"] = self.dataset
        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        instance.save()
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
        return context

    def form_valid(self, form):
        instance = form.save(commit=False)
        success_message = "prompt updated successfully."
        instance.save()
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
        if not request.user.is_modirator:
            messages.error(
                request,
                "Only modirators can review prompts. Please contact admins for further dtails.",
            )
            return redirect(self.get_success_url())
        return super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
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


class PromptListView(ListView):
    model = Prompt
    # paginate_by = 10
    context_object_name = "all_prompts"
    template_name = "prompt/prompt_list.html"

    def get_queryset(self):
        # filter all prompts by dataset
        queryset = super().get_queryset()
        queryset = queryset.filter(dataset__pk=self.kwargs["dataset_pk"])
        if not self.request.user.is_modirator:
            queryset = queryset[:5]
        return queryset

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        return super().setup(request, *args, **kwargs)

    def get_context_data(self):
        context = super().get_context_data()
        context["dataset"] = self.dataset
        context["user_prompts"] = Prompt.objects.filter(
            created_by=self.request.user,
            dataset=self.dataset,
        )

        # get prompts that are available to review

        # Subquery to get the last review action for each prompt
        review_actions = PromptReviewAction.objects.filter(
            prompt=OuterRef("pk")
        ).order_by("-taken_on")

        # Annotate each prompt with the last review action's submitter_decision
        prompts_with_last_action = Prompt.objects.annotate(
            last_submitter_decision=Subquery(
                review_actions.values("submitter_decision")[:1]
            )
        ).filter(
            review_actions__isnull=False,
            dataset=self.dataset,
        )

        # Filter prompts where the last submitter_decision is None
        ready_to_review_prompts = prompts_with_last_action.filter(
            last_submitter_decision__isnull=True
        )
        context["prompts_to_review"] = ready_to_review_prompts
        return context


class UserPromptsListView(ListView):
    model = Prompt
    paginate_by = 10
    context_object_name = "prompts"
    template_name = "prompt/user_prompts_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(created_by=self.request.user)
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
    def get(self, request, dataset_pk, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=dataset_pk)
        split = request.GET.get("split")
        subset = request.GET.get("subset")
        sample_index = request.GET.get("sample_index")
        if not subset and len(dataset.subsets_with_splits) > 1:
            # select the first one by default
            subset = list(dataset.subsets_with_splits.keys())[0]
        if split:
            samples, all_samples_count = dataset.load_samples(
                split=split,
                subset=subset,
            )
            if sample_index is not None:
                try:
                    sample_index = int(sample_index)
                    sample = samples[sample_index]
                    return JsonResponse({"sample": sample}, safe=False)
                except (ValueError, IndexError):
                    return JsonResponse({"error": "Invalid sample index"}, status=400)
            return JsonResponse(
                {
                    "len_samples": all_samples_count,
                    "first_sample": samples[0],
                },
                safe=False,
            )
        details = dataset.get_huggingface_info(subset=subset)
        return render(
            request,
            "prompt/partials/dataset_details.html",
            {
                "subset": subset,
                "dataset": dataset,
                "dataset_info": details,
            },
        )


class ApplyTemplateView(LoginRequiredMixin, View):
    def apply_template(self, template_content, sample):
        template_content = template_content.replace("<br>", "\n")
        template = Template(template_content)
        answer_choices = self.request.POST.get("answer_choices", [])
        if answer_choices:
            answer_choices = answer_choices.split("||")
        sample["answer_choices"] = answer_choices
        rendered_sample = template.render(**sample)
        return rendered_sample

    def post(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        split = request.GET.get("split")
        subset = request.GET.get("subset")
        text_direction = request.GET.get("text_direction", "ltr")
        sample_index = int(request.POST.get("sample_index", 0))
        samples, all_samples_count = self.dataset.load_samples(
            split=split,
            subset=subset,
        )
        sample = samples[sample_index]
        template_content = request.POST.get("template", "")
        merge_error = ""
        rendered_sample = {}
        try:
            rendered_sample = self.apply_template(template_content, sample)
        except Exception as e:
            merge_error = str(e)

        return render(
            request,
            "prompt/partials/template_merge.html",
            {
                "merge_error": merge_error,
                "dataset": self.dataset,
                "sample_index": sample_index,
                "rendered_template": rendered_sample,
                "template_content": template_content,
                "max_samples": len(samples),
                "subset": subset,
                "split": split,
                "text_direction": text_direction,
            },
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
