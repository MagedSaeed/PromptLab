from core.forms import OpenRouterAPIKeyForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, View


class OpenRouterAPIKeyView(LoginRequiredMixin, FormView):
    """View to manage OpenRouter API key"""

    form_class = OpenRouterAPIKeyForm
    template_name = "core/modals/openrouter_api_modal.html"
    success_url = reverse_lazy("home")  # Not used for AJAX

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return JsonResponse({"success": True})


class DeleteOpenRouterAPIKeyView(LoginRequiredMixin, View):
    """View to delete the OpenRouter API key"""

    def post(self, request, *args, **kwargs):
        user = request.user
        user.openrouter_api_key = None
        user.save()
        return JsonResponse({"success": True})
