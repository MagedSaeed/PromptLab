from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View
from django_filters.views import FilterView
from jinja2 import Template
from prompt.filters import DatasetFilter, TaskFilter
from prompt.forms import PromptCreateUpdateForm
from prompt.models import Dataset, Prompt, Task


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
        if self.request.POST.get("submit") == "submit_for_review":
            instance.status = Prompt.PromptStatus.SUBMITTED
        instance.save()
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

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != Prompt.PromptStatus.DRAFT:
            messages.error(
                self.request,
                "prompt cannot be updated while being reviewed.",
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
        if self.request.POST.get("submit") == "submit_for_review":
            instance.status = Prompt.PromptStatus.SUBMITTED
            success_message = "prompt submitted for review successfully."
        instance.save()
        messages.success(self.request, success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, form.errors, extra_tags="danger")
        return super().form_invalid(form)


class PromptDeleteView(LoginRequiredMixin, DeleteView):
    model = Prompt

    def get_success_url(self):
        return reverse_lazy(
            "prompt:prompt_list",
            kwargs={"dataset_pk": self.object.dataset.pk},
        )

    def get(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        return self.delete(request, *args, **kwargs)


class PromptListView(ListView):
    model = Prompt
    paginate_by = 10
    context_object_name = "prompts"
    template_name = "prompt/prompt_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(dataset__pk=self.kwargs["dataset_pk"])
        return queryset

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        return super().setup(request, *args, **kwargs)

    def get_context_data(self):
        context = super().get_context_data()
        context["dataset"] = self.dataset
        return context


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
            samples = dataset.load_samples(split=split, subset=subset)
            if sample_index is not None:
                try:
                    sample_index = int(sample_index)
                    sample = samples[sample_index]
                    return JsonResponse({"sample": sample}, safe=False)
                except (ValueError, IndexError):
                    return JsonResponse({"error": "Invalid sample index"}, status=400)
            return JsonResponse(
                {
                    "len_samples": dataset.get_huggingface_info(subset=subset)[
                        "full_info"
                    ]
                    .splits[split]
                    .num_examples,
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
    def post(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        split = request.GET.get("split")
        subset = request.GET.get("subset")
        text_direction = request.GET.get("text_direction", "ltr")
        sample_index = int(request.POST.get("sample_index", 0))
        sample = self.dataset.load_samples(
            split=split,
            subset=subset,
        )[sample_index]
        template_content = request.POST.get("template", "")
        template_content = template_content.replace("<br>", "\n")
        template = Template(template_content)
        answer_choices = request.POST.get("answer_choices", [])
        if answer_choices:
            answer_choices = answer_choices.split("||")
        sample["answer_choices"] = answer_choices
        rendered_sample = template.render(**sample)
        return render(
            request,
            "prompt/partials/template_merge.html",
            {
                "dataset": self.dataset,
                "sample_index": sample_index,
                "rendered_template": rendered_sample,
                "template_content": template_content,
                "max_samples": min(10_000, len(self.dataset.load_samples())),
                "subset": subset,
                "split": split,
                "text_direction": text_direction,
            },
        )
