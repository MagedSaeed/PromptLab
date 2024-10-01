from django import forms
from prompt.models import Prompt, PromptReviewAction


class PromptCreateUpdateForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = [
            "name",
            "template",
            "text_direction",
            "answer_choices",
            "dataset_subset",
        ]

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop("dataset")
        super().__init__(*args, **kwargs)
        self.fields["answer_choices"].widget.attrs.update(
            {
                "placeholder": "Enter choices here pressing Enter after each choice (optional)."
            }
        )
        if self.dataset.default_answer_choices:
            self.fields["answer_choices"].initial = self.dataset.default_answer_choices
        self.fields["name"].widget.attrs.update(
            {"placeholder": "Enter prompt name here"}
        )
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
        self.instance.can_edit_text = True
        if not self.instance.updateable:
            self.fields["name"].disabled = True
            self.fields["template"].disabled = True
            self.fields["text_direction"].disabled = True
            self.fields["answer_choices"].disabled = True
            self.instance.can_edit_text = False
        # self.fields["answer_choices"].label = False

    def is_prompt_reviewable(self):
        return self.instance.reviewable


class PromptReviewForm(forms.ModelForm):
    # these are prompt fields,
    # names are chosen to match the prompt fields in the prompt_create_update html template
    name = forms.CharField()
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
        prompt_fields = set(self.fields) - {"submitter_comment", "submitter_decision"}
        for key in data:
            if key in prompt_fields:
                reviewer_updates = data[key]
                if reviewer_updates:
                    reviewer_updates = reviewer_updates.strip()
                    setattr(self.prompt, key, reviewer_updates)
        self.prompt.save()

    def save(self, commit=True):
        self.set_prompt_status()
        self.instance.prompt = self.prompt
        self.instance.submitter = self.reviewer
        self.instance.prompt_before_submitter_modifications = {
            key: getattr(self.prompt, key)
            for key in self.fields.keys()
            - {
                "submitter_comment",
                "submitter_decision",
            }
        }
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
