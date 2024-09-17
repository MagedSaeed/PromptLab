from api import views
from django.urls import path

app_name = "api"

urlpatterns = [
    path(
        "prompt/create",
        views.PromptViewSet.as_view({"post": "create"}),
        name="prompt_create",
    ),
]
