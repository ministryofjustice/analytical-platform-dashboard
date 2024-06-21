import os
from typing import Any

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView, UpdateView

import boto3

from controlpanel.core.models import Datasource, User
from controlpanel.interfaces.web.auth.mixins import OIDCLoginRequiredMixin
from controlpanel.interfaces.web.forms import DatasourceFormView, DatasourceQuicksightForm


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
        context["embed_url"] = None
        user_name = "michael.collins"
        try:
            response = qs.register_user(
                IdentityType='QUICKSIGHT',
                Email="michael.collins5@justice.gov.uk",
                UserRole="AUTHOR",
                AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                Namespace="default",
                UserName=user_name
            )
            context["register_url"] = response["UserInvitationUrl"]
        except Exception as error:
            response = qs.generate_embed_url_for_registered_user(
                **{
                    "AwsAccountId": os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                    "UserArn": f"arn:aws:quicksight:eu-west-1:525294151996:user/default/{user_name}",
                    "ExperienceConfiguration": {"QuickSightConsole": {"InitialPath": "/start"}},
                }
            )

            context["embed_url"] = response["EmbedUrl"]

        return context


class DatasourcesList(OIDCLoginRequiredMixin, ListView):
    template_name = "datasources-list.html"
    model = Datasource
    context_object_name = "datasources"


class DatasourcesCreate(OIDCLoginRequiredMixin, FormView):
    template_name = "datasources.html"
    form_class = DatasourceFormView
    success_url = reverse_lazy("datasources-list")

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: Any) -> HttpResponse:
        obj = form.save()
        create_bucket = False
        if create_bucket:
            s3 = boto3.client(
                "s3",
                region_name="eu-west-1",
                aws_access_key_id=os.environ.get("DATA_ACCESS_KEY"),
                aws_secret_access_key=os.environ.get("DATA_SECRET_KEY"),
                aws_session_token=os.environ.get("DATA_SESSION_TOKEN"),
            )
            s3.create_bucket(
                Bucket=obj.name,
                CreateBucketConfiguration={
                    "LocationConstraint": "eu-west-1",
                },
            )
        return super().form_valid(form)


class DatasourcesManage(OIDCLoginRequiredMixin, UpdateView):
    form_class = DatasourceQuicksightForm
    template_name = "datasources-manage.html"
    model = Datasource
    success_url = reverse_lazy("datasources-list")

    def form_valid(self, form: DatasourceQuicksightForm) -> HttpResponse:
        redirect = super().form_valid(form)
        if self.object.is_quicksight_enabled:
            # TODO would need to get or create policy first
            qs = boto3.client("quicksight", region_name="eu-west-1")
            qs.create_iam_policy_assignment(
                AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                AssignmentName="michael-test-1",
                AssignmentStatus="ENABLED",
                PolicyArn=os.environ.get("QUICKSIGHT_POLICY_ARN"),
                Identities={"User": [os.environ.get("QUICKSIGHT_USERNAME")]},
                Namespace="default",
            )
        else:
            qs = boto3.client("quicksight", region_name="eu-west-1")
            qs.delete_iam_policy_assignment(
                AwsAccountId=os.environ.get("QUICKSIGHT_ACCOUNT_ID"),
                AssignmentName="michael-test-1",
                Namespace="default",
            )
        return redirect
