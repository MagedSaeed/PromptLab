from django.urls import path
from prompt.views import DatasetListView, PromptCreateView, TaskListView

app_name = "prompt"

urlpatterns = [
    path("task/list", TaskListView.as_view(), name="task_list"),
    path("dataset/list", DatasetListView.as_view(), name="dataset_list"),
    path(
        "dataset/<int:dataset_pk>/prompt/add",
        PromptCreateView.as_view(),
        name="prompt_create",
    ),
]
