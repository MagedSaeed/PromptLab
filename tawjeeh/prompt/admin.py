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
    readonly_fields = ["configs_details_truncated"]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj and obj.configs_details and len(str(obj.configs_details)) > 250_000:
            fields = [f for f in fields if f != "configs_details"]
        else:
            fields = [f for f in fields if f != "configs_details_truncated"]
        return fields

    def configs_details_truncated(self, obj):
        if obj.configs_details:
            json_str = str(obj.configs_details)
            if len(json_str) > 250_000:
                return f"{json_str[:1_000]} ..."
        return obj.configs_details

    configs_details_truncated.short_description = "Configs Details (Truncated)"


class PromptAdmin(admin.ModelAdmin):
    search_fields = ["content", "dataset__name", "dataset__tasks__name"]
    list_filter = ["dataset", "dataset__tasks"]


class PromptReviewActionAdmin(admin.ModelAdmin):
    search_fields = [
        "prompt__name",
        "prompt__dataset__name",
        "prompt__dataset__tasks__name",
    ]
    list_filter = [
        "prompt__name",
        "prompt__dataset",
        "prompt__dataset__tasks",
        "submitter",
    ]


admin.site.register(Task, TaskAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Prompt, PromptAdmin)
admin.site.register(PromptReviewAction, PromptReviewActionAdmin)
