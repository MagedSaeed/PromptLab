from rest_framework import permissions


class HasProjectSecretKey(permissions.BasePermission):
    def has_permission(self, request, view):
        project_secret_key = request.data.get(
            "project_secret_key"
        ) or request.query_params.get("project_secret_key")
        if not project_secret_key:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        project_secret_key = request.data.get(
            "project_secret_key"
        ) or request.query_params.get("project_secret_key")
        return obj.project.secret_key == project_secret_key
