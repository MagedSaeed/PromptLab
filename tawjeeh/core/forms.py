from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class OpenRouterAPIKeyForm(forms.ModelForm):
    """Form for managing OpenRouter API key"""
    openrouter_api_key = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'sk-or-...',
            'autocomplete': 'off'
        }),
        required=False,
        help_text='Your API key will be stored securely and used to test prompts against OpenRouter LLMs.'
    )

    class Meta:
        model = User
        fields = ['openrouter_api_key']
        
    def clean_openrouter_api_key(self):
        api_key = self.cleaned_data.get('openrouter_api_key')
        
        # If the user is trying to clear the key, that's fine
        if not api_key and 'openrouter_api_key' in self.changed_data:
            return None
            
        # If the user is submitting a new key, validate its format
        if api_key:
            # Check if it starts with the OpenRouter prefix (typically sk-or-)
            if not api_key.startswith('sk-or-'):
                raise ValidationError(
                    "The API key doesn't appear to be valid. OpenRouter API keys typically start with 'sk-or-'."
                )
                
            # Check minimum length
            if len(api_key) < 20:
                raise ValidationError(
                    "The API key is too short. Please check that you've entered it correctly."
                )
                
        elif self.instance.pk and not self.instance.openrouter_api_key and 'openrouter_api_key' in self.changed_data:
            # User is trying to save an empty key (when updating)
            raise ValidationError("Please enter an API key or cancel.")
            
        return api_key