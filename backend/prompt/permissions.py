from rest_framework import permissions

from prompt.models import PromptingProject


class IsProjectOwner(permissions.BasePermission):
    """Only allow the project owner."""

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PromptingProject):
            return obj.owner == request.user
        if hasattr(obj, "project") and obj.project:
            return obj.project.owner == request.user
        return False


class IsProjectMember(permissions.BasePermission):
    """Allow any project member (owner, prompter, or reviewer)."""

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PromptingProject):
            return obj.is_member(request.user)
        if hasattr(obj, "project") and obj.project:
            return obj.project.is_member(request.user)
        return False


class IsProjectReviewer(permissions.BasePermission):
    """Only allow project reviewers (or owner)."""

    def has_object_permission(self, request, view, obj):
        project = obj if isinstance(obj, PromptingProject) else getattr(obj, "project", None)
        if not project:
            return False
        return (
            project.owner == request.user
            or project.reviewers.filter(pk=request.user.pk).exists()
        )


class IsPromptCreator(permissions.BasePermission):
    """Only allow the prompt creator."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user
        return False
