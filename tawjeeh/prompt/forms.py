from django import forms
from prompt.models import Prompt


class PromptCreateForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = ["name", "template", "answer_choices", "dataset_subset"]

    def __init__(self, *args, **kwargs):
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
        self.fields["dataset_subset"].required = True
        self.fields["dataset_subset"].error_messages = {
            "required": "Please select a dataset from the left sidebar first.",
        }
