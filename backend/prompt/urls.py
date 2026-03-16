from django.urls import include, path
from rest_framework.routers import DefaultRouter

from prompt.views import (
    ApplyTemplateView,
    DatasetValidationView,
    DatasetViewSet,
    HFSyncView,
    LLMModelsView,
    LLMTestView,
    OpenRouterKeyView,
    ProjectViewSet,
    PromptViewSet,
    TaskViewSet,
    UserDistributedDatasetsView,
    UserPromptsView,
)

app_name = "prompt"

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    # Router-based endpoints
    path("", include(router.urls)),
    # Project-scoped dataset endpoints
    path(
        "projects/<int:project_pk>/datasets/",
        DatasetViewSet.as_view({"get": "list"}),
        name="project_dataset_list",
    ),
    path(
        "projects/<int:project_pk>/datasets/add/",
        DatasetViewSet.as_view({"post": "add_hf_dataset"}),
        name="project_dataset_add",
    ),
    path(
        "projects/<int:project_pk>/datasets/<int:pk>/remove/",
        DatasetViewSet.as_view({"delete": "remove"}),
        name="project_dataset_remove",
    ),
    # Dataset detail endpoints
    path(
        "datasets/<int:pk>/",
        DatasetViewSet.as_view({"get": "retrieve"}),
        name="dataset_detail",
    ),
    path(
        "datasets/<int:pk>/samples/",
        DatasetViewSet.as_view({"get": "samples"}),
        name="dataset_samples",
    ),
    path(
        "datasets/<int:pk>/reset-cache/",
        DatasetViewSet.as_view({"post": "reset_cache"}),
        name="dataset_reset_cache",
    ),
    # Dataset-scoped prompt endpoints
    path(
        "datasets/<int:dataset_pk>/prompts/",
        PromptViewSet.as_view({"get": "list", "post": "create"}),
        name="prompt_list",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/create-multiple/",
        PromptViewSet.as_view({"post": "create_multiple"}),
        name="prompt_create_multiple",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/save-generated/",
        PromptViewSet.as_view({"post": "save_generated"}),
        name="prompt_save_generated",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/reject-generated/",
        PromptViewSet.as_view({"post": "reject_generated"}),
        name="prompt_reject_generated",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/apply-template/",
        ApplyTemplateView.as_view(),
        name="apply_template",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/<int:pk>/",
        PromptViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="prompt_detail",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/<int:pk>/review/",
        PromptViewSet.as_view({"post": "review"}),
        name="prompt_review",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/<int:pk>/review-history/",
        PromptViewSet.as_view({"get": "review_history"}),
        name="prompt_review_history",
    ),
    path(
        "datasets/<int:dataset_pk>/prompts/<int:pk>/translate/",
        PromptViewSet.as_view({"post": "translate"}),
        name="prompt_translate",
    ),
    # User endpoints
    path("user/prompts/", UserPromptsView.as_view(), name="user_prompts"),
    path("user/datasets/", UserDistributedDatasetsView.as_view(), name="user_datasets"),
    # Admin endpoints
    path("hf-sync/", HFSyncView.as_view(), name="hf_sync"),
    # Dataset validation
    path("dataset/validate/", DatasetValidationView.as_view(), name="dataset_validate"),
    # OpenRouter endpoints
    path("openrouter/test/", LLMTestView.as_view(), name="openrouter_test"),
    path("openrouter/models/", LLMModelsView.as_view(), name="openrouter_models"),
    path("openrouter/api-key/", OpenRouterKeyView.as_view(), name="openrouter_key"),
]
