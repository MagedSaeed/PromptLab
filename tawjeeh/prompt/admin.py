from django.contrib import admin, messages
from django.core.management import call_command
from prompt.models import Dataset, Prompt, Task

# Register your models here.


@admin.action(description="Sync with Hugging Face")
def sync_with_huggingface(modeladmin, request, queryset):
    try:
        call_command("sync_with_hf")
        modeladmin.message_user(
            request, "Successfully synced with Hugging Face", messages.SUCCESS
        )
    except Exception as e:
        modeladmin.message_user(
            request, f"Error syncing with Hugging Face: {e}", messages.ERROR
        )


class TaskAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = ["name"]
    actions = [sync_with_huggingface]


class DatasetAdmin(admin.ModelAdmin):
    search_fields = ["name", "description", "tasks__name"]
    list_filter = ["tasks"]
    filter_horizontal = ["tasks"]


class PromptAdmin(admin.ModelAdmin):
    search_fields = ["content", "dataset__name", "dataset__tasks__name"]
    list_filter = ["dataset", "dataset__tasks"]


admin.site.register(Task, TaskAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Prompt, PromptAdmin)
