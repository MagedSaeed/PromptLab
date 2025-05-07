from django.urls import path
from core.views import (
    OpenRouterAPIKeyView,
    DeleteOpenRouterAPIKeyView
)

app_name = "core"

urlpatterns = [
    path('openrouter/api-key/', OpenRouterAPIKeyView.as_view(), name='openrouter_api_key'),
    path('openrouter/delete-api-key/', DeleteOpenRouterAPIKeyView.as_view(), name='delete_openrouter_api_key'),
]