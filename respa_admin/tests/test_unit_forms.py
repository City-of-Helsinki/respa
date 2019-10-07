import pytest
from django.urls import reverse
from resources.models import Unit


@pytest.mark.django_db
def test_editing_unit_via_form_view(admin_client, test_unit, test_unit_form_data):
    url = reverse('respa_admin:edit-unit', kwargs={'unit_id': test_unit.pk})
    unit_data = test_unit_form_data
    unit_data.update({
        'name_fi': 'Edited name',
    })
    response = admin_client.post(
        url,
        data=unit_data,
        follow=True
    )
    assert response.status_code == 200
    assert Unit.objects.count() == 1  # Still only 1 unit in db

    # Validate that the changes did happen
    edited_unit = Unit.objects.get(pk=test_unit.pk)
    assert edited_unit.name == 'Edited name'
    assert test_unit.name != edited_unit.name


@pytest.mark.django_db
def test_add_unit_period(admin_client, test_unit, empty_period_form_data, test_unit_form_data):
    url = reverse('respa_admin:edit-unit', kwargs={'unit_id': test_unit.pk})
    unit_data = test_unit_form_data
    unit_data['name_fi'] = 'Edited unit'
    period_data = empty_period_form_data
    test_period = {
        'name': 'Test period',
        'start': '2020-01-01',
        'end': '2020-06-01',
    }
    test_day = {
        'opens': '08:00',
        'closes': '12:00',
        'weekday': '1',
    }
    period_data.update({
        'periods-TOTAL_FORMS': ['1'],
        'days-periods-0-TOTAL_FORMS': ['1'],
        'periods-0-name': test_period['name'],
        'periods-0-start': test_period['start'],
        'periods-0-end': test_period['end'],
        'days-periods-0-0-opens': test_day['opens'],
        'days-periods-0-0-closes': test_day['closes'],
        'days-periods-0-0-weekday': test_day['weekday'],
    })
    # Edit the unit
    unit_data.update(period_data)
    response = admin_client.post(
        url,
        data=unit_data,
        follow=True
    )
    assert response.status_code == 200
    edited_unit = Unit.objects.get(pk=test_unit.pk)
    assert edited_unit.periods.count() == 1
    assert edited_unit.periods.first().name == test_period['name']
    assert edited_unit.periods.first().start.isoformat() == test_period['start']
    assert edited_unit.periods.first().end.isoformat() == test_period['end']
    assert edited_unit.periods.first().days.count() == 1
    assert edited_unit.periods.first().days.first().opens.strftime('%H:%M') == test_day['opens']
    assert edited_unit.periods.first().days.first().closes.strftime('%H:%M') == test_day['closes']
    assert edited_unit.periods.first().days.first().weekday == int(test_day['weekday'])
