# -*- coding: utf-8 -*-
import pytest
from django.contrib.auth import get_user_model

from resources.models import Reservation
from users.admin import pseudonymize_user_data


@pytest.mark.django_db
def test_pseudonymize_user_data(api_client, resource_in_unit, user):
    """
    Test pseudonymization of user data.
    """
    user.first_name = 'testi_ukkeli'
    user.save()
    Reservation.objects.create(
        resource=resource_in_unit,
        begin='2015-04-04T09:00:00+02:00',
        end='2015-04-04T10:00:00+02:00',
        user=user,
        reserver_name='John Smith',
        event_subject="John's welcome party",
        state=Reservation.CONFIRMED
    )
    # pseudonymize_user_data expects a queryset instead of single object
    test_user = get_user_model().objects.all().filter(first_name='testi_ukkeli')
    pseudonymize_user_data(modeladmin=None, request=None, queryset=test_user)
    assert get_user_model().objects.filter(first_name='testi_ukkeli').count() == 0
    assert Reservation.objects.filter(resource=resource_in_unit)[0].event_description == 'Sensitive data of this reservation has been pseudonymized by a script.'
