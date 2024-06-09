from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View
from django_filters.views import FilterView
from jinja2 import Template
from prompt.filters import DatasetFilter, TaskFilter
from prompt.forms import PromptCreateForm
from prompt.models import Dataset, Prompt, Task


class TaskListView(FilterView, ListView):
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


class DatasetListView(FilterView, ListView):
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


class PromptCreateView(CreateView):
    model = Prompt
    form_class = PromptCreateForm
    template_name = "prompt/prompt_create.html"
    success_url = reverse_lazy("prompt:dataset_list")

    def setup(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        return super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.subset = request.GET.get("subset")
        self.split = request.GET.get("split")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        return context

    def form_valid(self, form):
        form.instance.dataset = self.dataset
        messages.success(self.request, "prompt saved successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, form.errors)
        return super().form_invalid(form)


class ApplyTemplateView(View):
    def post(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        split = request.GET.get("split")
        subset = request.GET.get("subset")
        sample_index = int(request.POST.get("sample_index", 0))
        sample = self.dataset.load_samples(
            split=split,
            subset=subset,
        )[sample_index]
        template_content = request.POST.get("template", "")
        template_content = template_content.replace("<br>", "\n")
        template = Template(template_content)
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
            },
        )


class DatasetDetailsView(View):
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
