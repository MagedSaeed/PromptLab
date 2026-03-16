import json
import logging

import datasets
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from jinja2 import Environment, StrictUndefined
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from prompt.models import Dataset, Prompt, PromptingProject, PromptReviewAction, Task
from prompt.permissions import IsProjectMember, IsProjectOwner, IsProjectReviewer
from prompt.serializers import (
    ApplyTemplateSerializer,
    DatasetDetailSerializer,
    DatasetListSerializer,
    HFDatasetAddSerializer,
    HFSyncSerializer,
    LLMTestSerializer,
    ProjectCreateUpdateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    PromptCreateUpdateSerializer,
    PromptDetailSerializer,
    PromptListSerializer,
    PromptReviewActionSerializer,
    PromptReviewSerializer,
    TaskSerializer,
)
from prompt.utils import (
    collect_dataset_configs_details,
    generate_ai_prompts,
    get_split_samples,
    send_to_openrouter,
    translate_prompt_with_ai,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------------------------------------------------------------------
# 1. ProjectViewSet
# ---------------------------------------------------------------------------
class ProjectViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for prompting projects.

    list:   GET  /api/projects/
    create: POST /api/projects/
    read:   GET  /api/projects/<id>/
    update: PUT  /api/projects/<id>/
    delete: DELETE /api/projects/<id>/
    distribute: POST /api/projects/<id>/distribute/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectCreateUpdateSerializer
        return ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = PromptingProject.objects.filter(
            Q(owner=user) | Q(prompters=user) | Q(reviewers=user)
        ).distinct()

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        sort_by = self.request.query_params.get("sort", "name")
        if sort_by == "newest":
            queryset = queryset.order_by("-id")
        elif sort_by == "datasets":
            queryset = queryset.annotate(dataset_count=Count("datasets")).order_by(
                "-dataset_count"
            )
        else:
            queryset = queryset.order_by("name")

        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_object(self):
        obj = get_object_or_404(PromptingProject, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only the project owner can update this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Handle prompters M2M
        if "prompters" in request.data:
            prompter_ids = request.data["prompters"]
            project.prompters.set(User.objects.filter(pk__in=prompter_ids))

        # Handle reviewers M2M
        if "reviewers" in request.data:
            reviewer_ids = request.data["reviewers"]
            project.reviewers.set(User.objects.filter(pk__in=reviewer_ids))

        # Handle removing datasets
        remove_datasets = request.data.get("remove_datasets", [])
        if remove_datasets:
            datasets_to_remove = Dataset.objects.filter(
                pk__in=remove_datasets, project=project
            )
            for ds in datasets_to_remove:
                project.remove_dataset(ds)

        return Response(ProjectDetailSerializer(project).data)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only the project owner can delete this project."},
                status=status.HTTP_403_FORBIDDEN,
            )
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="distribute")
    def distribute(self, request, pk=None):
        project = self.get_object()
        if project.owner != request.user and not request.user.is_superuser:
            return Response(
                {"detail": "Only the project owner can distribute datasets."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = project.distribute_datasets()
            return Response({"detail": result})
        except Exception as e:
            return Response(
                {"detail": f"Error distributing datasets: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# 2. DatasetViewSet
# ---------------------------------------------------------------------------
class DatasetViewSet(viewsets.ModelViewSet):
    """
    Dataset management within projects.

    list:       GET    /api/projects/<project_pk>/datasets/
    retrieve:   GET    /api/datasets/<id>/
    add:        POST   /api/projects/<project_pk>/datasets/add/
    remove:     DELETE /api/projects/<project_pk>/datasets/<id>/remove/
    samples:    GET    /api/datasets/<id>/samples/
    reset_cache: POST  /api/datasets/<id>/reset-cache/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "list":
            return DatasetListSerializer
        return DatasetDetailSerializer

    def get_queryset(self):
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            project = get_object_or_404(PromptingProject, pk=project_pk)
            queryset = Dataset.objects.filter(project=project)

            search = self.request.query_params.get("search", "").strip()
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search)
                    | Q(huggingface_name__icontains=search)
                )

            task_pk = self.request.query_params.get("task_pk")
            if task_pk:
                queryset = queryset.filter(tasks__pk=task_pk)

            return queryset.distinct()
        return Dataset.objects.all()

    def retrieve(self, request, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=kwargs["pk"])
        serializer = DatasetDetailSerializer(dataset)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="add",
        url_name="add_hf_dataset",
    )
    def add_hf_dataset(self, request, project_pk=None):
        """Create a dataset from HuggingFace and add it to the project."""
        project = get_object_or_404(PromptingProject, pk=project_pk)
        if not project.is_member(request.user):
            return Response(
                {"detail": "You are not a member of this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = HFDatasetAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dataset_path = data["dataset_path"]

        # Validate the HF dataset path exists
        try:
            api_url = f"https://huggingface.co/api/datasets/{dataset_path}"
            headers = {"User-Agent": "PromptLab-Dataset-Validator/1.0"}
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 404:
                return Response(
                    {"detail": "Dataset not found on HuggingFace Hub."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Unable to validate dataset on HuggingFace Hub."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            hf_data = resp.json()

            # Check size < 1GB
            size_limit = 1024**3
            if "siblings" in hf_data:
                total_size = sum(
                    s.get("size", 0) for s in hf_data.get("siblings", [])
                )
                if total_size > size_limit:
                    return Response(
                        {
                            "detail": f"Dataset too large: {total_size / (1024**3):.1f} GB (max 1.0 GB)."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except requests.RequestException as e:
            return Response(
                {"detail": f"Error connecting to HuggingFace Hub: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Create the Dataset object
        dataset = Dataset.objects.create(
            name=data.get("name") or dataset_path.split("/")[-1],
            huggingface_name=dataset_path,
            description=data.get("description", ""),
            project=project,
            target_column=data.get("target_column", ""),
            default_subset=data.get("default_subset", ""),
            subsets=data.get("subsets", ""),
            is_single_classification=data.get("is_single_classification", False),
            download_only_the_default_subset=data.get(
                "download_only_the_default_subset", False
            ),
        )

        # Handle tasks (comma-separated string)
        tasks_str = data.get("tasks", "")
        if tasks_str:
            task_names = [t.strip() for t in tasks_str.split(",") if t.strip()]
            for task_name in task_names:
                task, _ = Task.objects.get_or_create(name=task_name)
                dataset.tasks.add(task)

        return Response(
            DatasetDetailSerializer(dataset).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="remove",
        url_name="remove_dataset",
    )
    def remove(self, request, project_pk=None, pk=None):
        """Remove a dataset from a project."""
        project = get_object_or_404(PromptingProject, pk=project_pk)
        dataset = get_object_or_404(Dataset, pk=pk, project=project)

        if project.owner != request.user and not request.user.is_superuser:
            return Response(
                {"detail": "Only the project owner can remove datasets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        project.remove_dataset(dataset)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="samples")
    def samples(self, request, pk=None, **kwargs):
        """Get dataset samples for a specific config/split."""
        dataset = get_object_or_404(Dataset, pk=pk)

        config = request.query_params.get("config")
        split = request.query_params.get("split")
        sample_index = request.query_params.get("sample_index")

        configs_details = dataset.get_configs_details()

        if not config:
            config = next(iter(configs_details.keys()), None)
        if not config or config not in configs_details:
            return Response(
                {"detail": "Invalid or missing config."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config_detail = configs_details[config]

        if not split:
            split = next(iter(config_detail.keys()), None)
        if not split or split not in config_detail:
            return Response(
                {"detail": "Invalid or missing split."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        samples_data = config_detail[split]["samples"]
        all_samples_count = config_detail[split]["all_samples_count"]
        samples_dataset = datasets.Dataset.from_dict(samples_data)

        if sample_index is not None:
            try:
                idx = int(sample_index)
                sample = samples_dataset[idx]
                return Response({"sample": sample})
            except (ValueError, IndexError):
                return Response(
                    {"detail": "Invalid sample index."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        first_sample = samples_dataset[0] if len(samples_dataset) > 0 else {}
        return Response(
            {
                "all_samples_count": all_samples_count,
                "max_browse_samples": len(samples_dataset),
                "first_sample": first_sample,
                "configs": list(configs_details.keys()),
                "splits": list(config_detail.keys()),
            }
        )

    @action(detail=True, methods=["post"], url_path="reset-cache")
    def reset_cache(self, request, pk=None, **kwargs):
        """Reset cached metadata for a dataset."""
        dataset = get_object_or_404(Dataset, pk=pk)
        dataset.reset_cache()
        return Response({"detail": "Dataset cache reset successfully."})


# ---------------------------------------------------------------------------
# 3. PromptViewSet
# ---------------------------------------------------------------------------
class PromptViewSet(viewsets.ModelViewSet):
    """
    Prompt management within datasets.

    list:            GET    /api/datasets/<dataset_pk>/prompts/
    create:          POST   /api/datasets/<dataset_pk>/prompts/
    retrieve:        GET    /api/datasets/<dataset_pk>/prompts/<id>/
    update:          PUT    /api/datasets/<dataset_pk>/prompts/<id>/
    destroy:         DELETE /api/datasets/<dataset_pk>/prompts/<id>/
    review:          POST   /api/datasets/<dataset_pk>/prompts/<id>/review/
    review_history:  GET    /api/datasets/<dataset_pk>/prompts/<id>/review-history/
    create_multiple: POST   /api/datasets/<dataset_pk>/prompts/create-multiple/
    save_generated:  POST   /api/datasets/<dataset_pk>/prompts/save-generated/
    reject_generated: POST  /api/datasets/<dataset_pk>/prompts/reject-generated/
    translate:       POST   /api/datasets/<dataset_pk>/prompts/<id>/translate/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "list":
            return PromptListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PromptCreateUpdateSerializer
        if self.action == "review":
            return PromptReviewSerializer
        return PromptDetailSerializer

    def _get_dataset(self):
        return get_object_or_404(Dataset, pk=self.kwargs["dataset_pk"])

    def get_queryset(self):
        dataset = self._get_dataset()
        queryset = Prompt.objects.filter(dataset=dataset)

        tab = self.request.query_params.get("tab", "all")
        if tab == "mine":
            queryset = queryset.filter(created_by=self.request.user)
        elif tab == "submitted":
            queryset = Prompt.with_status_annotations(queryset).filter(
                calculated_status=PromptReviewAction.PromptStatus.SUBMITTED
            )
        else:
            # "all" tab — annotate for ordering/filtering
            queryset = Prompt.with_status_annotations(queryset)

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(template__icontains=search)
            )

        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        dataset = self._get_dataset()
        if dataset.project and not dataset.project.is_member(request.user):
            return Response(
                {"detail": "You are not a member of this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.save(created_by=request.user, dataset=dataset)

        # Create review action
        submit = request.data.get("submit", False)
        if submit:
            PromptReviewAction.objects.create(
                prompt=prompt,
                submitter=request.user,
                prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
            )
        else:
            PromptReviewAction.objects.create(
                prompt=prompt,
                submitter=request.user,
                prompt_status=PromptReviewAction.PromptStatus.DRAFT,
            )

        return Response(
            PromptDetailSerializer(prompt).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        prompt = get_object_or_404(Prompt, pk=kwargs["pk"])
        data = PromptDetailSerializer(prompt).data
        data["review_history"] = PromptReviewActionSerializer(
            prompt.review_actions.order_by("-taken_on"), many=True
        ).data
        return Response(data)

    def update(self, request, *args, **kwargs):
        prompt = get_object_or_404(Prompt, pk=kwargs["pk"])
        if not prompt.updateable:
            return Response(
                {"detail": "Prompt cannot be updated after submission."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(prompt, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.save()

        submit = request.data.get("submit", False)
        if submit:
            PromptReviewAction.objects.create(
                prompt=prompt,
                submitter=request.user,
                prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
            )

        return Response(PromptDetailSerializer(prompt).data)

    def destroy(self, request, *args, **kwargs):
        prompt = get_object_or_404(Prompt, pk=kwargs["pk"])
        if prompt.created_by != request.user:
            return Response(
                {"detail": "Only the prompt creator can delete this prompt."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not prompt.updateable:
            return Response(
                {"detail": "Prompt cannot be deleted after submission."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prompt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, dataset_pk=None, pk=None):
        """Submit a review for a prompt (reviewer only)."""
        dataset = self._get_dataset()
        prompt = get_object_or_404(Prompt, pk=pk, dataset=dataset)

        if request.user not in dataset.project.reviewers.all():
            return Response(
                {"detail": "Only reviewers can review prompts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not prompt.reviewable:
            return Response(
                {"detail": "This prompt is not available for review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PromptReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Track modifications: compare prompt fields before/after
        prompt_fields = ["name", "template", "answer_choices", "text_direction"]
        modifications = {}
        for field in prompt_fields:
            if field in request.data:
                old_value = getattr(prompt, field)
                new_value = request.data[field]
                if str(old_value) != str(new_value):
                    modifications[field] = str(old_value)
                    setattr(prompt, field, new_value)

        if modifications:
            prompt.save()

        review_action = PromptReviewAction.objects.create(
            prompt=prompt,
            submitter=request.user,
            prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
            submitter_decision=data.get("submitter_decision", ""),
            submitter_comment=data.get("submitter_comment", ""),
            prompt_before_submitter_modifications=modifications or None,
        )

        return Response(
            PromptReviewActionSerializer(review_action).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="review-history")
    def review_history(self, request, dataset_pk=None, pk=None):
        """List review actions for a prompt."""
        prompt = get_object_or_404(Prompt, pk=pk)
        actions = prompt.review_actions.order_by("-taken_on")
        serializer = PromptReviewActionSerializer(actions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="create-multiple")
    def create_multiple(self, request, dataset_pk=None):
        """
        Generate AI prompt variants from a base prompt.
        Returns unsaved prompt data and stores them in the session.
        """
        dataset = self._get_dataset()
        base_prompt_pk = request.data.get("base_prompt_pk")
        if not base_prompt_pk:
            return Response(
                {"detail": "base_prompt_pk is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_prompt = get_object_or_404(Prompt, pk=base_prompt_pk, dataset=dataset)
        if not base_prompt.is_approved:
            return Response(
                {"detail": "The base prompt must be approved first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ai_prompts = generate_ai_prompts(base_prompt.as_dict())
            prompt_dicts = [p.as_dict() for p in ai_prompts]
            session_key = f"ai_generated_prompts_{base_prompt_pk}"
            request.session[session_key] = prompt_dicts
            return Response(
                {
                    "generated_prompts": prompt_dicts,
                    "count": len(prompt_dicts),
                    "base_prompt_pk": base_prompt_pk,
                }
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Error generating AI prompts")
            return Response(
                {"detail": f"Unexpected error generating AI prompts: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="save-generated")
    def save_generated(self, request, dataset_pk=None):
        """Save one AI-generated prompt from the session."""
        dataset = self._get_dataset()
        base_prompt_pk = request.data.get("base_prompt_pk")
        index = request.data.get("index")
        prompt_data = request.data.get("prompt_data")

        if base_prompt_pk is None or index is None:
            return Response(
                {"detail": "base_prompt_pk and index are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_key = f"ai_generated_prompts_{base_prompt_pk}"
        ai_prompts = request.session.get(session_key, [])

        try:
            index = int(index)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid index."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if index < 0 or index >= len(ai_prompts):
            return Response(
                {"detail": "Index out of range."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use either explicit prompt_data or the session-stored data
        source = prompt_data if prompt_data else ai_prompts[index]

        base_prompt = get_object_or_404(Prompt, pk=base_prompt_pk)

        prompt = Prompt.objects.create(
            name=source.get("name", ""),
            template=source.get("template", ""),
            dataset=dataset,
            dataset_subset=source.get("dataset_subset", ""),
            text_direction=source.get("text_direction", "ltr"),
            answer_choices=source.get("answer_choices", ""),
            created_by=request.user,
            base_prompt=base_prompt,
        )
        prompt.tags.add("AI generated")

        # Create a draft review action
        PromptReviewAction.objects.create(
            prompt=prompt,
            submitter=request.user,
            prompt_status=PromptReviewAction.PromptStatus.DRAFT,
        )

        # Remove from session
        del ai_prompts[index]
        if ai_prompts:
            request.session[session_key] = ai_prompts
        else:
            request.session.pop(session_key, None)

        return Response(
            PromptDetailSerializer(prompt).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="reject-generated")
    def reject_generated(self, request, dataset_pk=None):
        """Remove an AI-generated prompt from the session by index."""
        base_prompt_pk = request.data.get("base_prompt_pk")
        index = request.data.get("index")

        if base_prompt_pk is None or index is None:
            return Response(
                {"detail": "base_prompt_pk and index are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_key = f"ai_generated_prompts_{base_prompt_pk}"
        ai_prompts = request.session.get(session_key, [])

        try:
            index = int(index)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid index."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if 0 <= index < len(ai_prompts):
            del ai_prompts[index]
            if ai_prompts:
                request.session[session_key] = ai_prompts
            else:
                request.session.pop(session_key, None)
            return Response({"detail": "Prompt rejected.", "remaining": len(ai_prompts)})

        return Response(
            {"detail": "Index out of range."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="translate")
    def translate(self, request, dataset_pk=None, pk=None):
        """Translate a prompt using AI."""
        prompt = get_object_or_404(Prompt, pk=pk)
        try:
            translated = translate_prompt_with_ai(prompt.as_dict())
            return Response(translated.as_dict())
        except Exception as e:
            logger.exception("Error translating prompt")
            return Response(
                {"detail": f"Error translating prompt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# 4. ApplyTemplateView
# ---------------------------------------------------------------------------
class ApplyTemplateView(APIView):
    """
    POST /api/datasets/<dataset_pk>/prompts/apply-template/

    Render a Jinja2 prompt template against a dataset sample.
    Optionally test with an LLM via OpenRouter.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, dataset_pk=None):
        dataset = get_object_or_404(Dataset, pk=dataset_pk)

        template_content = request.data.get("template", "")
        if not template_content:
            return Response(
                {"detail": "No template content provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_index = int(request.data.get("sample_index", 0))
        test_with_llm = request.data.get("test_with_llm", False)
        model_id = request.data.get("model", "")
        text_direction = request.data.get("text_direction", "ltr")
        raw_answer_choices = request.data.get("answer_choices", "")

        # Resolve subset/split from configs_details
        configs_details = dataset.get_configs_details()
        subset = request.data.get("subset") or dataset.default_subset
        if not subset:
            subset = next(iter(configs_details.keys()), None)

        if not subset or subset not in configs_details:
            return Response(
                {"detail": "No valid dataset subset available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        split = request.data.get("split")
        if not split:
            split = next(iter(configs_details[subset].keys()), None)

        if not split or split not in configs_details[subset]:
            return Response(
                {"detail": "No valid split available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse answer choices
        answer_choices = self._parse_answer_choices(raw_answer_choices)

        # Get sample
        try:
            config_detail = configs_details[subset]
            samples_data = config_detail[split]["samples"]
            samples_dataset = datasets.Dataset.from_dict(samples_data)
            sample = samples_dataset[sample_index]
            max_samples = len(samples_dataset)
        except (KeyError, IndexError) as e:
            return Response(
                {"detail": f"Error accessing dataset sample: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Render template with Jinja2
        try:
            env = Environment(undefined=StrictUndefined)
            sample_with_choices = sample.copy()
            sample_with_choices["answer_choices"] = answer_choices

            # Validate "|||" divider
            if "|||" not in template_content:
                return Response(
                    {
                        "detail": 'Template must contain a "|||" divider.',
                        "rendered_template": None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            template_obj = env.from_string(template_content)
            rendered_template = template_obj.render(**sample_with_choices)

            # Create a plain version
            plain_template = rendered_template

        except Exception as e:
            return Response(
                {"detail": f"Error rendering template: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate answer choices against rendered output
        if answer_choices:
            answers_part = rendered_template.split("|||")[-1].strip()
            for answer in answers_part.split(","):
                answer = answer.strip()
                if answer and answer not in answer_choices:
                    return Response(
                        {
                            "detail": f"Output '{answer}' is not a subset of {answer_choices}.",
                            "rendered_template": rendered_template,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        response_data = {
            "rendered_template": rendered_template,
            "plain_template": plain_template,
            "sample_index": sample_index,
            "max_samples": max_samples,
            "processed_answer_choices": answer_choices,
        }

        # LLM test
        if test_with_llm and model_id:
            api_key = getattr(request.user, "openrouter_api_key", None)
            if not api_key:
                response_data["llm_result"] = {
                    "success": False,
                    "error": "No OpenRouter API key configured.",
                }
            else:
                prompt_text = plain_template.split("|||")[0].strip()
                llm_result = send_to_openrouter(prompt_text, model_id, api_key)
                response_data["llm_result"] = llm_result

        return Response(response_data)

    @staticmethod
    def _parse_answer_choices(raw):
        if not raw:
            return []
        if "||" in raw:
            return [c.strip() for c in raw.split("||") if c.strip()]
        elif "," in raw:
            return [c.strip() for c in raw.split(",") if c.strip()]
        return [raw.strip()] if raw.strip() else []


# ---------------------------------------------------------------------------
# 5. TaskViewSet
# ---------------------------------------------------------------------------
class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:   GET /api/tasks/
    search: GET /api/tasks/search/
    """

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = Task.objects.all()

        project_pk = self.request.query_params.get("project_pk")
        if project_pk:
            queryset = queryset.filter(
                datasets__project__pk=project_pk
            ).distinct()

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by("name")

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """Search tasks by name."""
        query = request.query_params.get("q", "").strip()
        if not query:
            tasks = Task.objects.all()[:20]
        else:
            tasks = Task.objects.filter(name__icontains=query)[:20]

        results = [
            {"id": t.id, "name": t.name, "text": t.name} for t in tasks
        ]
        return Response({"results": results})


# ---------------------------------------------------------------------------
# 6. UserPromptsView
# ---------------------------------------------------------------------------
class UserPromptsView(APIView):
    """
    GET /api/user/prompts/
    List the current user's prompts across all projects, with status annotations.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Prompt.objects.filter(
            created_by=request.user,
            dataset__isnull=False,
        )
        queryset = Prompt.with_status_annotations(queryset)

        # Order by status priority
        status_order = {
            "RETURNED_FOR_MODIFICATION": 0,
            "DRAFT": 1,
            "SUBMITTED": 2,
            "APPROVED": 3,
        }
        prompts = sorted(
            queryset,
            key=lambda p: status_order.get(
                getattr(p, "calculated_status", "DRAFT"), 1
            ),
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(prompts, request)
        serializer = PromptListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# 7. UserDistributedDatasetsView
# ---------------------------------------------------------------------------
class UserDistributedDatasetsView(APIView):
    """
    GET /api/user/datasets/
    List datasets assigned to the current user across all projects.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_projects = PromptingProject.objects.filter(prompters__in=[user])
        assignments = []

        for project in user_projects:
            if not project.dataset_assignments:
                continue
            if user.username not in project.dataset_assignments:
                continue

            for task, dataset_info in project.dataset_assignments[user.username].items():
                project_datasets = Dataset.objects.filter(
                    name=dataset_info["dataset_name"],
                    project=project,
                )
                if not project_datasets.exists():
                    continue

                for ds in project_datasets:
                    prompts_qs = Prompt.objects.filter(
                        dataset=ds,
                        created_by=user,
                        dataset__project=project,
                    )
                    has_prompts = prompts_qs.exists()
                    last_prompt = prompts_qs.last() if has_prompts else None

                    assignments.append(
                        {
                            "project_id": project.pk,
                            "project_name": project.name,
                            "task": task,
                            "dataset_name": dataset_info["dataset_name"],
                            "dataset_pk": ds.pk,
                            "status": last_prompt.status if has_prompts else "Pending",
                            "last_prompt_pk": last_prompt.pk if last_prompt else None,
                            "prompts_count": prompts_qs.count(),
                        }
                    )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(assignments, request)
        return paginator.get_paginated_response(page)


# ---------------------------------------------------------------------------
# 8. HFSyncView
# ---------------------------------------------------------------------------
class HFSyncView(APIView):
    """
    POST /api/hf-sync/
    Admin-only. Trigger sync_with_hf management command.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = HFSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            call_command("sync_with_hf", **data)
            return Response({"detail": "HF datasets synchronized successfully."})
        except Exception as e:
            logger.exception("HF sync failed")
            return Response(
                {"detail": f"Error during HF sync: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# 9. DatasetValidationView
# ---------------------------------------------------------------------------
class DatasetValidationView(APIView):
    """
    POST /api/dataset/validate/
    Validate a HuggingFace dataset path without downloading data.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        dataset_path = request.data.get("dataset_path", "").strip()
        if not dataset_path:
            return Response(
                {"valid": False, "error": "Dataset path is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self._validate_with_hub_api(dataset_path)
            if result:
                return Response(result)
            return Response(
                {"valid": False, "error": "Unable to validate dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"valid": False, "error": f"Error validating dataset: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _validate_with_hub_api(self, dataset_path):
        api_url = f"https://huggingface.co/api/datasets/{dataset_path}"
        headers = {"User-Agent": "PromptLab-Dataset-Validator/1.0"}
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 404:
            return {"valid": False, "error": "Dataset not found on HuggingFace Hub."}
        if response.status_code != 200:
            return None

        data = response.json()

        dataset_info = {
            "valid": True,
            "name": dataset_path.split("/")[-1],
            "huggingface_name": dataset_path,
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "downloads": data.get("downloads", 0),
            "likes": data.get("likes", 0),
            "configs": [],
            "size_warning": None,
            "size_info": None,
        }

        # Extract size info
        size_info = self._extract_size_info(data)
        if size_info:
            dataset_info["size_info"] = size_info

            size_error = self._check_size_limit(size_info)
            if size_error:
                return {"valid": False, "error": size_error}

            dataset_info["size_warning"] = self._generate_size_warning(size_info)

        # Get configs
        try:
            configs = datasets.get_dataset_config_names(
                dataset_path, trust_remote_code=True
            )
            dataset_info["configs"] = configs
        except Exception:
            dataset_info["configs"] = ["default"]

        return dataset_info

    @staticmethod
    def _check_size_limit(size_info):
        if not size_info:
            return None

        size_limit_bytes = 1024**3  # 1 GB

        if "dataset_size" in size_info:
            if size_info["dataset_size"] > size_limit_bytes:
                size_gb = size_info["dataset_size"] / (1024**3)
                return f"Dataset too large: {size_gb:.1f} GB (maximum allowed: 1.0 GB)"

        if "download_size" in size_info:
            if size_info["download_size"] > size_limit_bytes:
                size_gb = size_info["download_size"] / (1024**3)
                return f"Download size too large: {size_gb:.1f} GB (maximum allowed: 1.0 GB)"

        if "total_file_size" in size_info:
            if size_info["total_file_size"] > size_limit_bytes:
                size_gb = size_info["total_file_size"] / (1024**3)
                return (
                    f"Repository size too large: {size_gb:.1f} GB (maximum allowed: 1.0 GB)"
                )

        return None

    @staticmethod
    def _extract_size_info(hub_data):
        try:
            size_info = {}

            if "cardData" in hub_data:
                card_data = hub_data["cardData"]
                if "dataset_info" in card_data:
                    ds_info = card_data["dataset_info"]
                    if isinstance(ds_info, list) and len(ds_info) > 0:
                        ds_info = ds_info[0]
                    if "dataset_size" in ds_info:
                        size_info["dataset_size"] = ds_info["dataset_size"]
                    if "download_size" in ds_info:
                        size_info["download_size"] = ds_info["download_size"]
                    if "num_examples" in ds_info:
                        size_info["num_examples"] = ds_info["num_examples"]

            if "siblings" in hub_data:
                total_size = sum(s.get("size", 0) for s in hub_data["siblings"])
                if total_size > 0:
                    size_info["total_file_size"] = total_size

            return size_info if size_info else None
        except Exception:
            return None

    @staticmethod
    def _generate_size_warning(size_info):
        if not size_info:
            return None

        warnings = []

        if "dataset_size" in size_info:
            size_gb = size_info["dataset_size"] / (1024**3)
            if size_gb > 10:
                warnings.append(f"Large dataset: {size_gb:.1f} GB")
            elif size_gb > 1:
                warnings.append(f"Dataset size: {size_gb:.1f} GB")

        if "download_size" in size_info:
            dl_gb = size_info["download_size"] / (1024**3)
            if dl_gb > 5:
                warnings.append(f"Large download: {dl_gb:.1f} GB")

        if "total_file_size" in size_info:
            total_gb = size_info["total_file_size"] / (1024**3)
            if total_gb > 5:
                warnings.append(f"Repository size: {total_gb:.1f} GB")

        if "num_examples" in size_info:
            num = size_info["num_examples"]
            total_examples = sum(num.values()) if isinstance(num, dict) else num
            if total_examples > 10_000_000:
                warnings.append(f"Large dataset: {total_examples:,} examples")
            elif total_examples > 1_000_000:
                warnings.append(f"Dataset: {total_examples:,} examples")

        return " | ".join(warnings) if warnings else None


# ---------------------------------------------------------------------------
# 10. LLMTestView
# ---------------------------------------------------------------------------
class LLMTestView(APIView):
    """
    POST /api/openrouter/test/
    Send a prompt to OpenRouter for LLM testing.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LLMTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        model_id = data["model"]
        prompt_text = data["prompt_text"]
        api_key = data.get("api_key") or getattr(
            request.user, "openrouter_api_key", None
        )

        if not api_key:
            return Response(
                {"detail": "No OpenRouter API key provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = send_to_openrouter(prompt_text, model_id, api_key)
        return Response(result)


# ---------------------------------------------------------------------------
# 11. LLMModelsView
# ---------------------------------------------------------------------------
class LLMModelsView(APIView):
    """
    GET /api/openrouter/models/
    Fetch available models from OpenRouter API. Cached for 1 hour.
    """

    permission_classes = [IsAuthenticated]

    CACHE_KEY = "openrouter_models_list"
    CACHE_TIMEOUT = 3600  # 1 hour

    def get(self, request):
        api_key = getattr(request.user, "openrouter_api_key", None)
        if not api_key:
            return Response(
                {"detail": "No OpenRouter API key configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cached = cache.get(self.CACHE_KEY)
        if cached:
            return Response(cached)

        try:
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "PromptLab/1.0",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            cache.set(self.CACHE_KEY, data, self.CACHE_TIMEOUT)
            return Response(data)
        except requests.RequestException as e:
            return Response(
                {"detail": f"Error fetching models from OpenRouter: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


# ---------------------------------------------------------------------------
# 12. OpenRouterKeyView
# ---------------------------------------------------------------------------
class OpenRouterKeyView(APIView):
    """
    PUT    /api/openrouter/api-key/  - save API key
    DELETE /api/openrouter/api-key/  - delete API key
    """

    permission_classes = [IsAuthenticated]

    def put(self, request):
        api_key = request.data.get("api_key", "").strip()

        if not api_key:
            return Response(
                {"detail": "API key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not api_key.startswith("sk-or-"):
            return Response(
                {"detail": "Invalid API key format. Must start with 'sk-or-'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(api_key) < 20:
            return Response(
                {"detail": "API key is too short. Must be at least 20 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.openrouter_api_key = api_key
        request.user.save(update_fields=["openrouter_api_key"])
        return Response(
            {
                "detail": "API key saved successfully.",
                "masked_key": request.user.masked_openrouter_api_key,
            }
        )

    def delete(self, request):
        request.user.openrouter_api_key = None
        request.user.save(update_fields=["openrouter_api_key"])
        return Response({"detail": "API key deleted successfully."})
