from django.apps import AppConfig


class PromptConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prompt"

    def ready(self):
        import prompt.signals  # noqa F401
