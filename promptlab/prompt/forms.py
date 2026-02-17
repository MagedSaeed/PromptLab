import json
import secrets
import string

from django import forms
from django.contrib.auth import get_user_model
from prompt.models import Dataset, Prompt, PromptingProject, PromptReviewAction, Task

User = get_user_model()


class PromptCreateUpdateForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = [
            "name",
            "tags",
            "task",
            "template",
            "text_direction",
            "answer_choices",
            "dataset_subset",
        ]

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop("dataset")
        self.base_prompt = kwargs.pop("base_prompt", None)
        self.task = kwargs.pop("task", None)
        super().__init__(*args, **kwargs)
        self.fields["answer_choices"].widget.attrs.update(
            {
                "placeholder": "Enter choices here pressing Enter after each choice (optional)."
            }
        )
        self.fields["tags"].widget.attrs.update(
            {
                "placeholder": "Enter tags here separated by commas or pressing Enter after on each tag (optional)"
            }
        )
        if self.dataset.get_default_answer_choices(task=self.task):
            self.fields["answer_choices"].initial = (
                self.dataset.get_default_answer_choices(task=self.task)
            )
        self.fields["name"].widget.attrs.update(
            {"placeholder": "Enter prompt name here"}
        )
        self.fields["name"].label = False
        self.fields["task"].choices = [
            (task.pk, task.name) for task in self.dataset.tasks.all()
        ]
        if self.task:
            self.fields["task"].initial = self.task
        # make dataset_subset hidden as this will be handled by the ui from the dataset information left sidebar
        self.fields["dataset_subset"].widget = forms.HiddenInput()
        self.fields["template"].widget = forms.HiddenInput()
        self.fields["text_direction"].widget = forms.HiddenInput()
        self.instance.dataset = self.dataset
        if len(self.instance.dataset.get_configs_details()) > 1:
            self.fields["dataset_subset"].required = True
            self.fields["dataset_subset"].error_messages = {
                "required": "Please select a dataset from the left sidebar first.",
            }
        # override the default help text that is useful in the admin page.
        self.fields["tags"].help_text = ""
        self.fields["tags"].label = False
        self.instance.can_edit_text = True
        if not self.instance.updateable:
            self.fields["name"].disabled = True
            self.fields["tags"].disabled = True
            self.fields["template"].disabled = True
            self.fields["text_direction"].disabled = True
            self.fields["answer_choices"].disabled = True
            self.fields["task"].disabled = True
            self.instance.can_edit_text = False
        # self.fields["answer_choices"].label = False

    def is_prompt_reviewable(self):
        return self.instance.reviewable

    def save(self, commit=False):
        if self.base_prompt:
            self.instance.base_prompt = self.base_prompt
        return super().save(commit=commit)


class PromptReviewForm(forms.ModelForm):
    # these are prompt fields,
    # names are chosen to match the prompt fields in the prompt_create_update html template
    name = forms.CharField(label=False)
    tags = forms.CharField(required=False, label=False)
    task = forms.ChoiceField(required=False)
    template = forms.CharField(widget=forms.HiddenInput())
    text_direction = forms.ChoiceField(
        widget=forms.HiddenInput(),
        choices=Prompt.TextDirectionChoices.choices,
    )
    answer_choices = forms.CharField(required=False)
    dataset_subset = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = PromptReviewAction
        fields = ["submitter_comment", "submitter_decision"]

    def __init__(self, *args, **kwargs):
        self.prompt = kwargs.pop("prompt")
        self.reviewer = kwargs.pop("reviewer")
        self.dataset = kwargs.pop("dataset")
        super().__init__(*args, **kwargs)
        self.fields["submitter_comment"].widget = forms.Textarea(attrs={"rows": 3})
        # set fields initials from the prompt
        self.fields["name"].initial = self.prompt.name
        self.fields["tags"].initial = json.dumps(
            list(
                map(
                    lambda item: {"value": item},
                    self.prompt.tags.names(),
                )
            )
        )
        self.fields["task"].choices = [
            (task.pk, task.name) for task in self.dataset.tasks.all()
        ]
        if self.prompt.task:
            self.fields["task"].initial = (self.prompt.task.pk, self.prompt.task.name)
        self.fields["template"].initial = self.prompt.template
        self.fields["text_direction"].initial = self.prompt.text_direction
        self.fields["answer_choices"].initial = self.prompt.answer_choices
        self.fields["dataset_subset"].initial = self.prompt.dataset_subset
        self.prompt.can_edit_text = True
        if self.prompt.is_approved:
            self.fields["name"].disabled = True
            self.fields["template"].disabled = True
            self.fields["text_direction"].disabled = True
            self.fields["answer_choices"].disabled = True
            self.fields["task"].disabled = True
            self.fields["tags"].disabled = True
            self.prompt.can_edit_text = False

    def set_prompt_status(self):
        data = self.cleaned_data
        if (
            data["submitter_decision"]
            == PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION
        ):
            self.instance.prompt_status = PromptReviewAction.PromptStatus.DRAFT

    def clean(self):
        data = self.cleaned_data
        # get the task from its pk
        if data.get("task"):
            data["task"] = Task.objects.get(pk=data["task"])
        # transform tags to a string of comma separated tags list
        if data.get("tags"):
            # tags comes as a string of the following:
            # '[{"value": "tag1"}, {"value": "tag2"}]'
            data["tags"] = json.loads(data["tags"])
            data["tags"] = ",".join(
                tag for tag_dict in data["tags"] for tag in tag_dict.values()
            )
            # tags should end with , so that django-taggit splits it based on ,
            if data["tags"][-1] != ",":
                data["tags"] = data["tags"] + ","
        if data.get("submitter_decision") not in (
            PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION,
            PromptReviewAction.DecisionChoices.APPROVED,
        ):
            self.add_error(
                "submitter_decision",
                "Please select a valid choice, either approve or return for modification.",
            )
        if (
            data.get("submitter_decision")
            == PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION
        ):
            if not data["submitter_comment"]:
                self.add_error(
                    "submitter_comment",
                    "Please add a comment when returning a prompt for modifications.",
                )

    def update_prompt(self):
        data = self.cleaned_data
        prompt_fields = set(self.fields) - {
            "submitter_comment",
            "submitter_decision",
            "tags",
        }
        if data.get("tags"):
            tags = data.pop("tags")
            self.prompt.tags.clear()
            self.prompt.tags.add(*tags.split(","))
        for key in data:
            if key in prompt_fields:
                reviewer_updates = data[key]
                if reviewer_updates:
                    reviewer_updates = reviewer_updates.strip()
                    setattr(self.prompt, key, reviewer_updates)
        self.prompt.save()

    def save(self, commit=True):
        self.set_prompt_status()
        data = self.cleaned_data
        self.instance.prompt = self.prompt
        self.instance.submitter = self.reviewer
        self.instance.prompt_before_submitter_modifications = {
            "tags": list(self.prompt.tags.names())
        }
        if data["task"]:
            self.instance.prompt_before_submitter_modifications["task_name"] = data[
                "task"
            ].name
            data.pop("task")
        self.instance.prompt_before_submitter_modifications.update(
            {
                key: getattr(self.prompt, key)
                for key in self.fields.keys()
                - {
                    "submitter_comment",
                    "submitter_decision",
                    "tags",
                    "task",
                }
            }
        )
        self.update_prompt()
        return super().save(commit=commit)

    def is_prompt_reviewable(self):
        return self.prompt.reviewable


class HFSyncForm(forms.Form):
    sheet_id = forms.CharField(
        initial="1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k",
        required=True,
    )
    sheet_name = forms.CharField(
        initial="final-list",
        required=True,
    )
    default_subset_column = forms.CharField(
        label="Dataset default subset",
        required=True,
        initial="dataset_default_subset",
    )
    subsets_column = forms.CharField(
        label="Subsets to download",
        required=True,
        help_text="Enter subsets separated by commas. Leave empty to download all subsets.",
        initial="dataset_subsets_to_download",
    )
    link_column = forms.CharField(
        initial="link",
        required=True,
    )
    task_column = forms.CharField(
        initial="task_name",
        required=True,
    )
    is_single_classification_column = forms.CharField(
        initial="is_single_classification",
        required=True,
    )
    target_column = forms.CharField(
        initial="target_column",
        required=True,
    )
    clear_datasets = forms.BooleanField(required=False)
    target_project = forms.ModelChoiceField(
        queryset=PromptingProject.objects.none(),
        label="Target Project",
        help_text="Select the project where datasets will be added",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # example_template_column = forms.CharField(
    #     initial="example_template",
    #     required=False,
    # )
    # example_template_created_by_column = forms.CharField(
    #     initial="example_template_created_by",
    #     required=False,
    # )
    # example_template_subset_column = forms.CharField(
    #     initial="subset",
    #     required=False,
    # )
    # answer_choices_column = forms.CharField(
    #     initial="answer_choices",
    #     required=False,
    # )
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["target_project"].queryset = PromptingProject.objects.filter(
            owner=user
        ).distinct()


class ProjectForm(forms.ModelForm):
    """Form for creating and updating PromptingProject."""

    # Regular prompters can only create prompts
    prompters = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
        help_text="Users who can create prompts for this project",
    )

    # Reviewer prompters can both create and review prompts
    reviewers = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
        help_text="Users who can create and review prompts for this project",
    )

    remove_datasets = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Comma-separated list of dataset IDs to remove",
    )

    class Meta:
        model = PromptingProject
        fields = [
            "name",
            "description",
            # "datasets",
            "minimum_prompts_per_prompter",
            "secret_key",
            "reviewers",
            "prompters",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "minimum_prompts_per_prompter": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "secret_key": forms.TextInput(
                attrs={"class": "form-control", "readonly": True}
            ),
        }
        help_texts = {
            "name": "Give your project a descriptive name",
            "description": "Provide details about the project (optional)",
            "minimum_prompts_per_prompter": "Minimum number of prompts each prompter should contribute (optional)",
            "secret_key": "Used for API access - automatically generated but can be changed",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        # Make description optional
        self.fields["description"].required = False
        self.fields["minimum_prompts_per_prompter"].required = False

        # Generate a random 5-character secret key by default if this is a new project
        if not self.instance.pk and not self.initial.get("secret_key"):
            alphabet = string.ascii_letters + string.digits
            random_key = "".join(secrets.choice(alphabet) for _ in range(5))
            self.initial["secret_key"] = random_key

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set the owner to the current user if this is a new project
        if not instance.pk and self.user:
            instance.owner = self.user

        if commit:
            instance.save()
            self.save_m2m()

            # Handle dataset removal
            remove_datasets_str = self.cleaned_data.get("remove_datasets", "")
            if remove_datasets_str:
                dataset_ids_to_remove = [
                    int(id.strip())
                    for id in remove_datasets_str.split(",")
                    if id.strip().isdigit()
                ]
                datasets_to_remove = Dataset.objects.filter(
                    id__in=dataset_ids_to_remove, project=instance
                )
                datasets_to_remove.delete()

        return instance


class LLMTestForm(forms.Form):
    """Form for testing prompts with OpenRouter LLMs."""

    model = forms.ChoiceField(
        label="Select LLM Model",
        choices=[],
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Initialize model choices
        if user and user.openrouter_api_key:
            try:
                self.fields["model"].choices = self.get_openrouter_models(
                    user.openrouter_api_key
                )
                self.fields["model"].help_text = (
                    "Select a model to test your prompt with"
                )
            except Exception as e:
                self.fields["model"].choices = [
                    ("", f"Error fetching models: {str(e)}")
                ]
                self.fields["model"].disabled = True
        else:
            self.fields["model"].choices = [("", "Please add OpenRouter API key first")]
            self.fields["model"].help_text = (
                "Add your OpenRouter API key in user settings to enable testing"
            )
            self.fields["model"].disabled = True

    def get_openrouter_models(self, api_key):
        """Get available models from OpenRouter API or cache."""
        import requests
        from django.core.cache import cache

        # Check cache first
        cache_key = (
            f"openrouter_models_{api_key[:8]}"  # Use part of API key as cache key
        )
        cached_models = cache.get(cache_key)

        if cached_models:
            return cached_models

        # If not in cache, fetch from API
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://promptlab.up.railway.app",  # Required by OpenRouter
                "X-Title": "PromptLab Prompt Testing",
            }
            response = requests.get(
                "https://openrouter.ai/api/v1/models", headers=headers
            )
            response.raise_for_status()

            models_data = response.json().get("data", [])

            # Format choices for form field (id, display_name)
            choices = []
            for model in models_data:
                model_id = model.get("id")
                name = model.get("name") or model_id

                # Format pricing info if available
                pricing = model.get("pricing", {}).get("prompt")
                price_info = f" (${pricing}/1M tokens)" if pricing else ""

                display_name = f"{name}{price_info}"
                choices.append((model_id, display_name))

            # Sort by name
            choices.sort(key=lambda x: x[1])

            # Add empty choice
            final_choices = [("", "Select a model...")] + choices

            # Cache for 1 hour
            cache.set(cache_key, final_choices, 60 * 60)

            return final_choices
        except Exception as e:
            # Return empty list with error message
            return [("", f"Error fetching models: {str(e)}")]


class HuggingFaceDatasetForm(forms.Form):
    """Form for adding datasets from HuggingFace Hub"""

    dataset_path = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., arbml/watan_2004 or microsoft/DialoGPT-medium",
                "id": "datasetPathInput",
            }
        ),
        help_text="Enter the HuggingFace dataset path (author/dataset-name)",
    )

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Display name for the dataset",
                "id": "datasetNameInput",
            }
        ),
        help_text="A readable name for the dataset",
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Brief description of the dataset (optional)",
                "id": "datasetDescriptionInput",
            }
        ),
        help_text="Optional description of the dataset",
    )

    tasks = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "sentiment analysis, question answering, etc.",
                "id": "datasetTasksInput",
            }
        ),
        help_text="Comma-separated list of tasks this dataset is used for (optional)",
    )

    def clean_dataset_path(self):
        dataset_path = self.cleaned_data["dataset_path"].strip()

        # Basic validation of the path format
        if "/" not in dataset_path:
            raise forms.ValidationError(
                'Dataset path should be in format "author/dataset-name"'
            )

        parts = dataset_path.split("/")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise forms.ValidationError(
                'Invalid dataset path format. Should be "author/dataset-name"'
            )

        return dataset_path
