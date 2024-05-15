from django.urls import path
from prompt.views import TaskListView, DatasetListView

app_name = "prompt"

urlpatterns = [
    path("task/list", TaskListView.as_view(), name="task_list"),
    path("dataset/list", DatasetListView.as_view(), name="dataset_list"),
]
