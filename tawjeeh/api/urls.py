from api import views
from django.urls import path

app_name = "api"

urlpatterns = [
    path(
        "prompt/create",
        views.PromptCreateView.as_view(),
        name="prompt_create",
    ),
    path(
        "prompt/list",
        views.PromptListView.as_view(),
        name="prompt_list",
    ),
]
