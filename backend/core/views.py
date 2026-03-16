from django.contrib.auth import logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.serializers import UserSerializer


@require_GET
def csrf_token_view(request):
    """Set CSRF cookie and return token"""
    token = get_token(request)
    return JsonResponse({"csrfToken": token})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get or update current user profile"""
    if request.method == "GET":
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    elif request.method == "PATCH":
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout the current user"""
    logout(request)
    return Response({"detail": "Successfully logged out."})


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def openrouter_key_view(request):
    """Update OpenRouter API key"""
    api_key = request.data.get("openrouter_api_key", "")
    if api_key and (len(api_key) < 10 or not api_key.startswith("sk-or-")):
        return Response(
            {"error": "Invalid API key format"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    request.user.openrouter_api_key = api_key or None
    request.user.save()
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_openrouter_key_view(request):
    """Delete OpenRouter API key"""
    request.user.openrouter_api_key = None
    request.user.save()
    return Response({"success": True})
