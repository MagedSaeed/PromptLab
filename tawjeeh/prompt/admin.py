from django.contrib import admin

# from django.core.management import call_command
from prompt.models import Dataset, Prompt, PromptReviewAction, Task

# from django.contrib import messages


# Register your models here.


# @admin.action(description="Sync with Hugging Face")
# def sync_with_huggingface(modeladmin, request, queryset):
#     try:
#         call_command(
#             "sync_with_hf",
#             sheet_url="1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k",
#             sheet_name="final-list",
#         )
#         modeladmin.message_user(
#             request,
#             "Successfully synced with Hugging Face",
#             messages.SUCCESS,
#         )
#     except Exception as e:
#         modeladmin.message_user(
#             request,
#             f"Error syncing with Hugging Face: {e}",
#             messages.ERROR,
#         )


class TaskAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = ["name"]
    # actions = [sync_with_huggingface]


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
admin.site.register(PromptReviewAction)
