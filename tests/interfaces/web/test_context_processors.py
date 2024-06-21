from django.urls import reverse

import pytest

from controlpanel.interfaces.web.context_processors import header_context, nav_items


class TestContextProcessors:
    @pytest.fixture
    def request_obj(self, rf, superuser):
        request = rf.get("/")
        request.user = superuser
        return request

    def test_nav_items(self, request_obj):
        home = {"name": "Home", "url": "/", "active": True}
        data_products = {"name": "Quicksight", "url": reverse("quicksight"), "active": False}
        assert nav_items(request=request_obj) == {"nav_items": [home, data_products]}

    def test_header_context(self, request_obj):
        expected_nav_items = [
            {"name": request_obj.user.name, "url": ""},
            {"name": "Sign out", "url": reverse("logout")},
        ]

        context = header_context(request=request_obj)
        assert context.get("header_nav_items") == expected_nav_items
        assert (
            context.get("header_organisation_url")
            == "https://www.gov.uk/government/organisations/ministry-of-justice"
        )
        assert (
            context.get("header_service_url")
            == "https://github.com/ministryofjustice/data-platform"
        )
