from django import forms
from prompt.models import Prompt


class PromptCreateForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = ["name", "template", "answer_choices"]

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
