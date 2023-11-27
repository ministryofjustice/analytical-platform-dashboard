from django.conf import settings
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

import structlog
from authlib.integrations.django_client import OAuth, OAuthError, token_update

from controlpanel.core.models.user import User

logger = structlog.get_logger(__name__)

oauth = OAuth()
# oauth.register("auth0", **(settings.AUTHLIB_OAUTH_CLIENTS["auth0"]))
oauth.register(
    "azure",
    client_id=settings.AUTHLIB_OAUTH_CLIENTS["azure"]["client_id"],
    # client_secret is not needed for PKCE flow
    server_metadata_url=settings.AUTHLIB_OAUTH_CLIENTS["azure"]["server_metadata_url"],
    client_kwargs=settings.AUTHLIB_OAUTH_CLIENTS["azure"]["client_kwargs"],
)


@receiver(token_update)
def on_token_update(sender, token, refresh_token=None, access_token=None, **kwargs):
    """for information purpose only
    Since this app (so far) doesn't use access_token linking to the user directly
    the refresh_token is not very useful here, even app will use the access_token
    in the future,  using the auto token_update signal from authlib, the problem will
    be where we store the tokens (access_token and refresh_token), if we store them in
    the session, this token_update won't allow app to access current session object
    from current request, alternatively we can use django-crequest or refresh the
    access_token manually
    """
    if refresh_token:
        logger.info("The token has been refreshed by using refresh_token")


class OIDCSubAuthenticationBackend:
    def __init__(self, token):
        self.token = token

    def filter_users_by_claims(self):
        user_id = self.token.get("userinfo", {}).get("oid")
        return User.objects.filter(pk=user_id).first()

    def _get_username(self, user_info):
        return user_info.get("username") or User.construct_username(user_info.get("name"))

    def _create_user(self):
        user_info = self.token.get("userinfo")
        return User.objects.create(
            pk=user_info.get("oid"),
            username=self._get_username(user_info),
            nickname=user_info.get("nickname", ""),
            email=user_info.get("email"),
            name=user_info.get("name", ""),
        )

    def _update_user(self, user):
        user_info = self.token.get("userinfo")
        # Update the non-key information to sync the user's info
        # with user profile from idp when the user's username is not changed.
        if user.username != self._get_username(user_info):
            return user

        if user.email != user_info.get("email"):
            user.email = user_info.get("email")
            user.save()
        if user.name != user_info.get("name"):
            user.name = user_info.get("name", "")
            user.save()
        return user

    def _verify_claims(self):
        """Can check certain attributes"""
        return True

    def create_or_update_user(self):
        if not self._verify_claims():
            return None

        if not self.token.get("userinfo"):
            return None

        user = self.filter_users_by_claims()

        if user and user.is_active:
            return self._update_user(user)
        else:
            return self._create_user()


class OIDCSessionValidator:
    def __init__(self, request):
        """refresh needs to attach the current request"""
        self.request = request

    def _refresh_by_silence_auth(self):
        """TBD should we re-auth silent before token is expired just for covering
        the timing issue if someone is removed from IDP, but this user is still valid user
        and has valid session with Control panel at that moment?
        """
        try:
            redirect_uri = self.request.build_absolute_uri(reverse("authenticate"))
            # TODO come back to this
            return oauth.auth0.authorize_redirect(self.request, redirect_uri, prompt="none")
        except OAuthError as ex:
            logger.debug("Failed to perform silence-auth due to error (%s)", ex.__str__())
            return False

    def _has_access_token_expired(self):
        current_seconds = timezone.now().timestamp()
        token_expiry_seconds = self.request.session.get("oidc_access_token_expiration")
        return token_expiry_seconds and current_seconds > token_expiry_seconds

    def _has_id_token_expired(self):
        current_seconds = timezone.now().timestamp()
        token_expiry_seconds = self.request.session.get("oidc_id_token_expiration")
        return token_expiry_seconds and current_seconds > token_expiry_seconds

    def expired(self):
        """
        Validate the id_token by renewing the id_token by using silence_auth
        TBD : not sure whether it is useful or not, right now the id_token
        will be renewed based on t
        """
        return self._has_access_token_expired() or self._has_id_token_expired()
