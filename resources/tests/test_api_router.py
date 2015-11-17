# -*- coding: utf-8 -*-
from resources.api import RespaAPIRouter


def test_accidental_reinitialization_of_api_router():
    # This basically simulates someone `register`ing the same view class more than once.
    # It's unlikely, but at least we get more coverage.
    router = RespaAPIRouter()
    router._register_all_views()
