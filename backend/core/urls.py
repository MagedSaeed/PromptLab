from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("csrf-token/", views.csrf_token_view, name="csrf_token"),
    path("profile/", views.profile_view, name="profile"),
    path("logout/", views.logout_view, name="logout"),
    path("openrouter/api-key/", views.openrouter_key_view, name="openrouter_api_key"),
    path("openrouter/api-key/delete/", views.delete_openrouter_key_view, name="delete_openrouter_api_key"),
]
