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


class LoginPromptView(TemplateView):
    template_name = "login.html"


class QuicksightView(OIDCLoginRequiredMixin, TemplateView):
    template_name = "quicksight.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        qs = boto3.client("quicksight", region_name="eu-west-1")
        rolename = "dev_user_michaeljcollinsuk"
        session_name = "michaeljcollinsuk"
        try:
            response = qs.register_user(
                IdentityType="IAM",
                IamArn=f"arn:aws:iam::525294151996:role/{rolename}",
                SessionName=session_name,
                Email="michael.collins5@justice.gov.uk",
                UserRole="AUTHOR",
                AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                Namespace="default",
                # UserName=user_name
            )
        except Exception as error:
            print(f"User probably already registered {error}")
            pass

        response = qs.generate_embed_url_for_registered_user(
            **{
                "AwsAccountId": os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                "UserArn": f"arn:aws:quicksight:eu-west-1:525294151996:user/default/{rolename}/{session_name}",  # noqa
                "ExperienceConfiguration": {"QuickSightConsole": {"InitialPath": "/start"}},
            }
        )

        context["embed_url"] = response["EmbedUrl"]
        return context

    def describe_user(self, qs, rolename, session_name):
        return qs.describe_user(
            AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
            Namespace="default",
            UserName=f"{rolename}/{session_name}",
        )

    def describe_policy_assignment(self, qs, name):
        return qs.describe_iam_policy_assignment(
            AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
            Namespace="default",
            AssignmentName="michael-test-1",
        )
