# -*- coding: utf-8 -*-
from resources.api import RespaAPIRouter
from django.urls import reverse
import pytest


def test_accidental_reinitialization_of_api_router():
    # This basically simulates someone `register`ing the same view class more than once.
    # It's unlikely, but at least we get more coverage.
    router = RespaAPIRouter()
    router._register_all_views()


@pytest.mark.django_db
def test_api_html_view(client):
    resp = client.get(reverse('reservation-list'), HTTP_ACCEPT='text/html')
    assert resp.status_code == 200
