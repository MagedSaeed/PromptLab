from django.contrib.auth.models import AbstractUser
from django.db import models


class PromptLabUser(AbstractUser):
    openrouter_api_key = models.CharField(max_length=255, blank=True, null=True)

    # Override any methods from AbstractUser if needed
    def __str__(self):
        return self.username

    @property
    def is_moderator(self):
        return self.is_staff

    @property
    def masked_openrouter_api_key(self):
        """Return a masked version of the API key for display"""
        if not self.openrouter_api_key:
            return None
        if len(self.openrouter_api_key) <= 8:
            return "••••••••"
        return f"{self.openrouter_api_key[:4]}•••••••{self.openrouter_api_key[-4:]}"
