import datasets
from api.permissions import HasProjectSecretKey
from api.serializers import PromptCreateSerializer, PromptListSerializer
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from prompt.models import Dataset, Prompt, PromptingProject, Task
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response


class PromptCreateView(CreateAPIView):
    serializer_class = PromptCreateSerializer
    permission_classes = [HasProjectSecretKey]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save()


class PromptListView(ListAPIView):
    serializer_class = PromptListSerializer
    permission_classes = [HasProjectSecretKey]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "template", "tags__name"]
    ordering_fields = ["name", "created_on"]
    ordering = ["-created_on"]  # default ordering

    def get_queryset(self):
        project_secret_key = self.request.query_params.get("project_secret_key")
        if not project_secret_key:
            return Prompt.objects.none()

        # Get project and dataset IDs in one efficient query
        try:
            # Cache this result if project_secret_key doesn't change often
            dataset_ids = PromptingProject.objects.get(
                secret_key=project_secret_key
            ).datasets.values_list("id", flat=True)
        except PromptingProject.DoesNotExist:
            return Prompt.objects.none()

        # Build optimized queryset
        return (
            Prompt.objects.filter(dataset_id__in=dataset_ids)
            .select_related("dataset", "task", "created_by")
            .prefetch_related("tags")
            .only(
                # Only fields actually used in your serializer
                "id",
                "tags",
                "name",
                "template",
                "text_direction",
                "dataset_subset",
                "answer_choices",
                # "dataset__name",
                "dataset__huggingface_name",
                "task__name",
                "created_by__username",
            )
        )


class DatasetCreateAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """API endpoint for creating datasets from HuggingFace"""

    MAX_DATASET_SIZE_GB = 1.0

    def test_func(self):
        return self.request.user == self.project.owner

    def setup(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            PromptingProject,
            pk=kwargs.get("project_pk"),
        )
        return super().setup(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            # Extract form data
            dataset_path = request.POST.get("dataset_path", "").strip()
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            task_names = request.POST.get("tasks", "").strip()

            # Extract new dataset attributes
            target_column = request.POST.get("target_column", "").strip()
            default_subset = request.POST.get("default_subset", "").strip()
            subsets = request.POST.get("subsets", "").strip()
            is_single_classification = (
                request.POST.get("is_single_classification", "").lower() == "true"
            )
            download_only_default = (
                request.POST.get("download_only_the_default_subset", "").lower()
                == "true"
            )

            if not all([dataset_path, name]):
                return JsonResponse(
                    {"success": False, "error": "Dataset path and name are required"}
                )

            if download_only_default and not default_subset:
                print("download only is:", download_only_default)
                print("default subset is:", default_subset)
                return JsonResponse(
                    {
                        "success": False,
                        "error": "If download_only_the_default_subset is true, default_subset must also be provided",
                    }
                )

            if Dataset.objects.filter(
                huggingface_name=dataset_path,
                project=self.project,
            ).exists():
                return JsonResponse(
                    {"success": False, "error": "Dataset already there in the project"}
                )

            # Get dataset info and check size
            try:
                dataset_info = datasets.get_dataset_infos(dataset_path)
                first_config = next(iter(dataset_info.values()))

                # Check size from dataset_info
                if hasattr(first_config, "dataset_size") and first_config.dataset_size:
                    size_gb = first_config.dataset_size / (1024**3)
                    if size_gb > self.MAX_DATASET_SIZE_GB:
                        return JsonResponse(
                            {
                                "success": False,
                                "error": f"Dataset size {size_gb:.2f}GB exceeds {self.MAX_DATASET_SIZE_GB}GB limit",
                            }
                        )

            except Exception:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Could not access dataset on HuggingFace Hub",
                    }
                )

            # Create dataset with new attributes
            dataset_data = {
                "name": name,
                "project": self.project,
                "huggingface_name": dataset_path,
                "description": description or first_config.description or "",
                "is_single_classification": is_single_classification,
                "download_only_the_default_subset": download_only_default,
            }

            # Add optional fields only if they have values
            if target_column:
                dataset_data["target_column"] = target_column

            if default_subset:
                dataset_data["default_subset"] = default_subset

            if subsets:
                dataset_data["subsets"] = subsets

            dataset = Dataset.objects.create(**dataset_data)

            # Add tasks
            if task_names:
                tasks = [
                    Task.objects.get_or_create(name=t.strip())[0]
                    for t in task_names.split(",")
                    if t.strip()
                ]
                dataset.tasks.set(tasks)

            return JsonResponse(
                {
                    "success": True,
                    "dataset": {
                        "id": dataset.id,
                        "name": dataset.name,
                        "huggingface_name": dataset.huggingface_name,
                        "description": dataset.description,
                        "target_column": dataset.target_column,
                        "default_subset": dataset.default_subset,
                        "subsets": dataset.subsets,
                        "is_single_classification": dataset.is_single_classification,
                        "download_only_the_default_subset": dataset.download_only_the_default_subset,
                    },
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Error creating dataset: {str(e)}"}
            )
