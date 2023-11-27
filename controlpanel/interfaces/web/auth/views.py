import base64
import hashlib
import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from authlib.common.security import generate_token
from authlib.integrations.django_client import OAuthError

from controlpanel.core.auth import OIDCSubAuthenticationBackend, oauth


def pkce_transform(code_verifier):
    """Transforms the code verifier to a code challenge."""
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class OIDCLoginView(View):
    def get(self, request):
        code_verifier = generate_token(64)
        # request.session["code_verifier"] = code_verifier
        code_challenge = pkce_transform(code_verifier)

        redirect_uri = request.build_absolute_uri(reverse("authenticate"))
        print(redirect_uri)

        return oauth.azure.authorize_redirect(request, redirect_uri, code_challenge=code_challenge)


class OIDCAuthenticationView(View):
    def _update_sessions(self, request, token):
        """TBD should we consider renewing the id_token?"""
        request.session["oidc_id_token_renew_gap"] = (
            time.time() + settings.OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS
        )
        request.session["oidc_access_token_expiration"] = token.get("expires_at")
        request.session["oidc_id_token_expiration"] = token["userinfo"].get("exp")

        if token.get("refresh_token"):
            request.session["refresh_token"] = token["refresh_token"]

    def _login_success(self, request, user, token):
        auth.login(self.request, user)
        self._update_sessions(request, token)

    @property
    def failure_url(self):
        return reverse("login-fail")

    def _login_failure(self):
        return redirect(self.failure_url)

    def get(self, request):
        # should this be used?
        # code_verifier = request.session["code_verifier"]
        try:
            token = oauth.azure.authorize_access_token(request)
            oidc_auth = OIDCSubAuthenticationBackend(token)
            user = oidc_auth.create_or_update_user()
            if not user:
                return self._login_failure()
            else:
                self._login_success(request, user, token)
                return redirect("/")
        except OAuthError:
            return self._login_failure()


class OIDCLogoutView(View):
    http_method_names = ["get", "post"]

    def _get_oidc_logout_redirect_url(self, request):
        params = urlencode(
            {
                "returnTo": f"{request.scheme}://{request.get_host()}{reverse('index')}",
                "client_id": settings.OIDC_RP_CLIENT_ID,
            }
        )
        return f"{settings.OIDC_LOGOUT_URL}?{params}"

    def post(self, request):
        logout_url = self._get_oidc_logout_redirect_url(request)

        if request.user.is_authenticated:
            auth.logout(request)

        return redirect(logout_url)

    def get(self, request):
        if self.get_settings("ALLOW_LOGOUT_GET_METHOD", False):
            return self.post(request)
        return HttpResponseNotAllowed(["POST"])


class LogoutView(OIDCLogoutView):
    def get(self, request):
        return super().post(request)


class LoginFail(TemplateView):
    template_name = "login-fail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["environment"] = settings.ENV
        return context
