from django.urls import path
from prompt.views import TaskListView

app_name = "prompt"

urlpatterns = [
    path("task/list", TaskListView.as_view(), name="task_list"),
]
