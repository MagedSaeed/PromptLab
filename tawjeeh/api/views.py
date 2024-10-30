from api.permissions import HasProjectSecretKey
from api.serializers import PromptCreateSerializer, PromptListSerializer
from prompt.models import Prompt
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response


class PromptCreateView(CreateAPIView):
    serializer_class = PromptCreateSerializer
    permission_classes = [HasProjectSecretKey]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save()


class PromptListView(ListAPIView):
    serializer_class = PromptListSerializer
    permission_classes = [HasProjectSecretKey]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "template", "tags__name"]
    ordering_fields = ["name", "created_on"]
    ordering = ["-created_on"]  # default ordering

    def get_queryset(self):
        project_secret_key = self.request.query_params.get("project_secret_key")
        if not project_secret_key:
            return Prompt.objects.none()

        return (
            Prompt.objects.filter(
                dataset__prompting_projects__secret_key=project_secret_key
            )
            .select_related("dataset")
            .prefetch_related("tags")
        )
