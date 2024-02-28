import os
from typing import Any

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView

import boto3

from controlpanel.core.models import Datasource, User
from controlpanel.interfaces.web.auth.mixins import OIDCLoginRequiredMixin
from controlpanel.interfaces.web.forms import DatasourceFormView


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
        if False:
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
