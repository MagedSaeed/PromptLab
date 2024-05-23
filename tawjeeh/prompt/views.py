from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import CreateView, ListView, View
from django_filters.views import FilterView
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

    def get(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs["dataset_pk"])
        self.subset = request.GET.get("subset")
        self.split = request.GET.get("split")
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["dataset"] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        return context


class DatasetDetailsView(View):
    def get(self, request, dataset_pk, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=dataset_pk)
        split = request.GET.get("split")
        sample_index = request.GET.get("sample_index")

        if split:
            samples = dataset.load_samples(split_name=split)

            if sample_index is not None:
                try:
                    sample_index = int(sample_index)
                    sample = samples[sample_index]
                    return JsonResponse({"sample": sample}, safe=False)
                except (ValueError, IndexError):
                    return JsonResponse({"error": "Invalid sample index"}, status=400)

            return JsonResponse(
                {
                    "len_samples": dataset.huggingface_info["full_info"]
                    .splits[split]
                    .num_examples
                },
                safe=False,
            )

        details = dataset.huggingface_info
        return render(
            request,
            "prompt/partials/dataset_details.html",
            {"dataset_info": details, "dataset": dataset},
        )
