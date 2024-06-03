from django import forms
from prompt.models import Dataset, Prompt
from prompt.utils import get_hf_dataset_config_choices


class DatasetAdminForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(DatasetAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["config"].widget = forms.Select(
                choices=get_hf_dataset_config_choices(self.instance.huggingface_name)
            )


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
