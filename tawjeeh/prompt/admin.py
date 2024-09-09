import json

from django.contrib import admin
from django.utils.safestring import mark_safe

# from django.core.management import call_command
from prompt.models import Dataset, Prompt, PromptReviewAction, Task
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
    readonly_fields = [
        "configs_details_prettified",
        "features_prettified",
        "columns_names_prettified",
        "huggingface_raw_prettified",
    ]

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


class PromptAdmin(admin.ModelAdmin):
    search_fields = ["dataset__name", "dataset__tasks__name"]
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
