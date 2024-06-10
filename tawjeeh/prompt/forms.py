import datasets
from django import forms
from prompt.models import Prompt


class PromptCreateForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = [
            "name",
            "template",
            "answer_choices",
            "dataset_subset",
        ]

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop("dataset")
        super().__init__(*args, **kwargs)
        self.fields["answer_choices"].widget.attrs.update(
            {
                "placeholder": "Enter choices separated by ||. You may leave this empty if the choices are already in the template"
            }
        )
        self.fields["name"].widget.attrs.update(
            {"placeholder": "Enter prompt name here"}
        )
        # make dataset_subset hidden as this will be handled by the ui from the dataset information left sidebar
        self.fields["dataset_subset"].widget = forms.HiddenInput()
        self.instance.dataset = self.dataset
        if len(self.instance.dataset.subsets_with_splits) > 1:
            self.fields["dataset_subset"].required = True
            self.fields["dataset_subset"].error_messages = {
                "required": "Please select a dataset from the left sidebar first.",
            }

    def save(self, commit=True):
        if not len(self.instance.dataset.subsets_with_splits) > 1:
            self.instance.dataset_subset = datasets.get_dataset_default_config_name(
                self.dataset.huggingface_name,
                trust_remote_code=True,
            )
        return super().save(commit=commit)
