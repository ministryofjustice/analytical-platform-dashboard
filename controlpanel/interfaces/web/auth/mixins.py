from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse

from controlpanel.core.auth import OIDCSessionValidator


class OIDCLoginRequiredMixin(LoginRequiredMixin):
    """Verify that the current user is (still) authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse("login-prompt"))
        if OIDCSessionValidator(request).expired():
            return redirect(reverse("login-prompt"))
        return super().dispatch(request, *args, **kwargs)
