import datasets
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
        self.fields["name"].widget.attrs.update(
            {"placeholder": "Enter prompt name here"}
        )
        # make dataset_subset hidden as this will be handled by the ui from the dataset information left sidebar
        self.fields["dataset_subset"].widget = forms.HiddenInput()
        self.fields["template"].widget = forms.HiddenInput()
        self.fields["text_direction"].widget = forms.HiddenInput()
        self.instance.dataset = self.dataset
        if len(self.instance.dataset.subsets_with_splits) > 1:
            self.fields["dataset_subset"].required = True
            self.fields["dataset_subset"].error_messages = {
                "required": "Please select a dataset from the left sidebar first.",
            }
        if not self.instance.updateable:
            self.fields["name"].disabled = True
            self.fields["template"].disabled = True
            self.fields["text_direction"].disabled = True
            self.fields["answer_choices"].disabled = True
        self.fields["answer_choices"].label = False

    def save(self, commit=True):
        if not len(self.instance.dataset.subsets_with_splits) > 1:
            self.instance.dataset_subset = datasets.get_dataset_default_config_name(
                self.dataset.huggingface_name,
                trust_remote_code=True,
            )
        return super().save(commit=commit)


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

    def set_prompt_status(self):
        data = self.cleaned_data
        if (
            data["submitter_decision"]
            == PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION
        ):
            self.instance.prompt_status = PromptReviewAction.PromptStatus.DRAFT

    def clean(self):
        data = self.cleaned_data
        if (
            data["submitter_decision"]
            == PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION
        ):
            if not data["submitter_comment"]:
                self.add_error(
                    "submitter_comment",
                    "Please add a comment when returning a prompt for modifications.",
                )

    def get_prompt_reviewer_modifications(self):
        data = self.cleaned_data
        prompt_modifications = {}
        prompt_fields = set(self.fields) - {"submitter_comment", "submitter_decision"}
        for key in data:
            if key in prompt_fields:
                if data[key] != getattr(self.prompt, key):
                    reviewer_updates = data[key]
                    if reviewer_updates:
                        reviewer_updates = reviewer_updates.strip()
                    prompt_modifications[key] = reviewer_updates
        return prompt_modifications

    def save(self, commit=True):
        self.set_prompt_status()
        self.instance.prompt = self.prompt
        self.instance.submitter = self.reviewer
        prompt_modifications = self.get_prompt_reviewer_modifications()
        self.instance.prompt_before_modifications = prompt_modifications
        return super().save(commit=commit)
