from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    masked_openrouter_api_key = serializers.CharField(read_only=True)
    openrouter_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    is_moderator = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_moderator",
            "openrouter_api_key",
            "masked_openrouter_api_key",
        ]
        read_only_fields = ["id", "username", "email", "is_staff"]
