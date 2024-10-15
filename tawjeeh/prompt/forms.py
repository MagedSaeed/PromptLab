import json

from django import forms
from prompt.models import Prompt, PromptReviewAction, Task


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
        if self.dataset.default_answer_choices:
            self.fields["answer_choices"].initial = self.dataset.default_answer_choices
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
    task = forms.ChoiceField()
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
        if data["task"]:
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
