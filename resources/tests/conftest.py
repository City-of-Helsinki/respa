# -*- coding: utf-8 -*-
import pytest
from rest_framework.test import APIClient, APIRequestFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_rf():
    return APIRequestFactory()
