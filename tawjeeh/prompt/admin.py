import json

from django.contrib import admin, messages
from django.db.models import Prefetch
from django.utils.safestring import mark_safe

# from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin

# from django.core.management import call_command
from prompt.models import Dataset, Prompt, PromptingProject, PromptReviewAction, Task
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer

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
    list_select_related = True
    readonly_fields = [
        "configs_details_prettified",
        "features_prettified",
        "columns_names_prettified",
        "huggingface_raw_prettified",
    ]
    raw_id_fields = ["tasks"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "tasks",
                Prefetch(
                    "prompts", queryset=Prompt.objects.select_related("created_by")
                ),
            )
        )

    def _prettify_json(self, data):
        """Helper function to prettify JSON data"""
        # Convert the data to sorted, indented JSON with non-ASCII character support
        json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)

        # Truncate the data to 5000 characters
        json_str = json_str[:5000]

        # Define a custom style that increases font size
        custom_style = """
            <style>
                .highlight {
                    all: initial;  /* Reset all properties */
                    font-family: 'Courier New', Courier, monospace !important;
                    font-size: 16px !important;
                    line-height: 1.5 !important;
                    background-color: var(--highlight-bg, #f8f8f8) !important;
                    color: var(--highlight-color, #333) !important;
                    display: block !important;
                    padding: 15px !important;
                    border-radius: 5px !important;
                    white-space: pre-wrap !important;
                    word-break: break-all !important;
                    overflow-x: auto !important;
                }
                .highlight * {
                    font-size: inherit !important;
                }
                .highlight .p { color: var(--highlight-punctuation, #999) !important; }
                .highlight .n { color: var(--highlight-name, #666) !important; }
                .highlight .s { color: var(--highlight-string, #d14) !important; }
                .highlight .mf, .highlight .mi { color: var(--highlight-number, #099) !important; }
                @media (prefers-color-scheme: dark) {
                    .highlight {
                        --highlight-bg: #282a36 !important;
                        --highlight-color: #f8f8f2 !important;
                        --highlight-punctuation: #6272a4 !important;
                        --highlight-name: #8be9fd !important;
                        --highlight-string: #f1fa8c !important;
                        --highlight-number: #bd93f9 !important;
                    }
                }
            </style>
        """

        # Get the Pygments formatter with our custom style
        formatter = HtmlFormatter(style="default")

        # Highlight the data
        highlighted = highlight(json_str, JsonLexer(), formatter)

        # Combine the custom style with the highlighted output
        styled_output = (
            f"{custom_style}<div class='highlight-wrapper'>{highlighted}</div>"
        )

        # Return safe HTML
        return mark_safe(styled_output)

    def configs_details_prettified(self, instance):
        return self._prettify_json(instance.configs_details)

    configs_details_prettified.short_description = "Configs Details"

    def features_prettified(self, instance):
        return self._prettify_json(instance.features)

    features_prettified.short_description = "Features"

    def columns_names_prettified(self, instance):
        return self._prettify_json(instance.columns_names)

    columns_names_prettified.short_description = "Column Names"

    def huggingface_raw_prettified(self, instance):
        return self._prettify_json(instance.huggingface_raw)

    huggingface_raw_prettified.short_description = "Huggingface Raw"

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # Remove the original fields and add the prettified versions
        fields = [
            f
            for f in fields
            if f
            not in ["configs_details", "features", "columns_names", "huggingface_raw"]
        ]
        fields.extend(
            [
                "configs_details_prettified",
                "features_prettified",
                "columns_names_prettified",
                "huggingface_raw_prettified",
            ]
        )
        return fields

    class Media:
        css = {
            "all": (
                "admin/css/vendor/select2/select2.css",
                "admin/css/autocomplete.css",
            )
        }


class PromptStatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("RETURNED_FOR_MODIFICATION", "Returned for modification"),
            ("APPROVED", "Approved"),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        # Use the model's annotation method
        return Prompt.with_status_annotations(queryset).filter(
            calculated_status=self.value()
        )


class PromptAdmin(ImportExportModelAdmin):
    search_fields = ["name", "dataset__name", "created_by__username"]
    list_filter = [PromptStatusFilter, "dataset", "dataset__tasks", "created_by"]
    list_select_related = ["dataset", "created_by", "task"]
    list_display = ("name", "dataset", "created_by", "status", "created_on")
    raw_id_fields = ["dataset", "task", "base_prompt", "created_by"]
    readonly_fields = ["status"]

    def get_queryset(self, request):
        # Start with base queryset with essential select_related
        qs = (
            super()
            .get_queryset(request)
            .select_related("dataset", "created_by", "task")
        )

        # Only prefetch related review actions if we're viewing a detail page
        if "change" in request.path:
            qs = qs.prefetch_related(
                Prefetch(
                    "review_actions",
                    queryset=PromptReviewAction.objects.select_related(
                        "submitter"
                    ).only(
                        "id",
                        "prompt_id",
                        "submitter_id",
                        "prompt_status",
                        "submitter_decision",
                        "taken_on",
                        "submitter__username",
                    ),
                )
            )
        # For list views, annotate with status calculations instead of prefetching
        elif (
            any(param.startswith("status") for param in request.GET) or not request.GET
        ):
            qs = Prompt.with_status_annotations(qs)

        # Use .only() to limit fields fetched
        return qs.only(
            "id",
            "name",
            "template",
            "text_direction",
            "dataset_id",
            "dataset_subset",
            "created_by_id",
            "created_on",
            "last_updated_on",
            "task_id",
            "answer_choices",
            "dataset__name",
            "dataset__huggingface_name",
            "created_by__username",
            "task__name",
        )

    @admin.display(description="Status")
    def status(self, obj):
        # Use annotated field if available
        if hasattr(obj, "calculated_status"):
            return obj.calculated_status
        # Fall back to property which uses prefetched data if available
        return obj.status


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
    list_select_related = ["prompt", "prompt__dataset", "submitter"]
    raw_id_fields = ["prompt", "submitter"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("prompt", "prompt__dataset", "submitter")
            .only(
                "id",
                "prompt_id",
                "submitter_id",
                "prompt_status",
                "submitter_decision",
                "taken_on",
                "submitter_comment",
                "prompt__name",
                "prompt__dataset__name",
                "submitter__username",
            )
            # Prefetch tasks with a limited set of fields
            .prefetch_related(
                Prefetch(
                    "prompt__dataset__tasks", queryset=Task.objects.only("id", "name")
                )
            )
        ).order_by("-taken_on")


class PromptingProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "get_prompters_count", "get_datasets_count")
    search_fields = ("name", "owner__username", "prompters__username")
    filter_horizontal = ("prompters", "datasets")
    list_select_related = ["owner"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("prompters", "datasets")

    def get_prompters_count(self, obj):
        return obj.prompters.count()

    get_prompters_count.short_description = "Prompters Count"

    def get_datasets_count(self, obj):
        return obj.datasets.count()

    get_datasets_count.short_description = "Datasets Count"

    actions = ["distribute_datasets_action"]

    @admin.action(description="Distribute datasets to prompters")
    def distribute_datasets_action(self, request, queryset):
        for project in queryset:
            try:
                result = project.distribute_datasets()
                self.message_user(request, result, messages.SUCCESS)
            except Exception as e:
                self.message_user(
                    request,
                    f"Error distributing datasets for {project.name}: {str(e)}",
                    messages.ERROR,
                )

    def response_change(self, request, obj):
        if "_distribute_datasets" in request.POST:
            try:
                result = obj.distribute_datasets()
                self.message_user(request, result, messages.SUCCESS)
            except Exception as e:
                self.message_user(
                    request, f"Error distributing datasets: {str(e)}", messages.ERROR
                )
        return super().response_change(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_distribute_button"] = True
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )


admin.site.register(Task, TaskAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Prompt, PromptAdmin)
admin.site.register(PromptReviewAction, PromptReviewActionAdmin)
admin.site.register(PromptingProject, PromptingProjectAdmin)
