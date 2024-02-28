import os
from typing import Any

from django.views.generic import TemplateView

import boto3

from controlpanel.core.models import User
from controlpanel.interfaces.web.auth.mixins import OIDCLoginRequiredMixin


class IndexView(OIDCLoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "users": User.objects.all(),
            }
        )
        return context


class QuicksightView(OIDCLoginRequiredMixin, TemplateView):
    template_name = "quicksight.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        qs = boto3.client("quicksight", region_name="eu-west-1")
        response = qs.generate_embed_url_for_registered_user(
            **{
                "AwsAccountId": os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                "UserArn": os.environ.get("QUICKSIGHT_USER_ARN"),
                "ExperienceConfiguration": {"QuickSightConsole": {"InitialPath": "/start"}},
            }
        )
        context["embed_url"] = response["EmbedUrl"]

        return context
