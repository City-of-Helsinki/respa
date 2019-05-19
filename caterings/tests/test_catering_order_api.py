import datetime
import pytest
from django.test.utils import override_settings
from django.urls import reverse
from parler.utils.context import switch_language
from guardian.shortcuts import assign_perm
from resources.tests.utils import assert_response_objects, check_disallowed_methods, check_keys
from resources.models import Reservation
from resources.models.utils import DEFAULT_LANG
from caterings.models import CateringOrder, CateringOrderLine, CateringProduct
from notifications.models import NotificationTemplate, NotificationType
from notifications.tests.utils import check_received_mail_exists


LIST_URL = reverse('cateringorder-list')


def get_detail_url(catering_order):
    return reverse('cateringorder-detail', kwargs={'pk': catering_order.pk})


@pytest.fixture
def new_order_data(catering_product, reservation):
    return {
        'reservation': reservation.pk,
        'order_lines': [
            {
                'product': catering_product.pk,
                'quantity': 2,
            }
        ],
        'invoicing_data': '123456',
        'message': 'no sugar please',
        'serving_time': '13:00:00',
    }


@pytest.fixture
def update_order_data(catering_product2, catering_product3, reservation2):
    return {
        'reservation': reservation2.pk,
        'order_lines': [
            {
                'product': catering_product2.pk,
            },
            {
                'product': catering_product3.pk,
                'quantity': 7,
            }
        ],
        'invoicing_data': '654321',
        'serving_time': None,
    }


@pytest.mark.django_db
def test_catering_order_endpoint_disallowed_methods(user_api_client, catering_product):
    detail_url = get_detail_url(catering_product)
    check_disallowed_methods(user_api_client, (LIST_URL,), ('put', 'patch', 'delete'))
    check_disallowed_methods(user_api_client, (detail_url,), ('post',))


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_catering_orders_endpoints_get(user_api_client, user, catering_order, catering_product, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(catering_order)

    response = user_api_client.get(url)
    assert response.status_code == 200
    if endpoint == 'list':
        assert len(response.data['results']) == 1
        data = response.data['results'][0]
    else:
        data = response.data

    expected_keys = {
        'id',
        'created_at',
        'modified_at',
        'reservation',
        'order_lines',
        'invoicing_data',
        'message',
        'serving_time',
    }
    check_keys(data, expected_keys)

    assert data['id']
    assert data['created_at']
    assert data['modified_at']
    assert data['reservation'] == catering_order.reservation.pk
    assert data['invoicing_data'] == catering_order.invoicing_data
    assert data['message'] == catering_order.message
    assert data['serving_time'] == '12:00:00'

    order_lines = data['order_lines']
    assert len(order_lines) == 1
    order_line = order_lines[0]
    check_keys(order_line, {'product', 'quantity'})
    assert order_line['product'] == catering_product.pk
    assert order_line['quantity'] == 1


@pytest.mark.django_db
def test_other_people_orders_hidden(api_client, user_api_client, user2, catering_order):
    detail_url = get_detail_url(catering_order)

    # verify that own order is visible just in case
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 1
    response = user_api_client.get(detail_url)
    assert response.status_code == 200

    # unauthenticated user
    response = api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 0
    response = api_client.get(detail_url)
    assert response.status_code == 404

    # other user
    user_api_client.force_authenticate(user=user2)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 0
    response = user_api_client.get(detail_url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_order_create(user_api_client, reservation, catering_product, new_order_data):
    response = user_api_client.post(LIST_URL, data=new_order_data, format='json')
    assert response.status_code == 201

    order_object = CateringOrder.objects.latest('id')
    assert order_object.created_at and order_object.modified_at
    assert order_object.reservation == reservation
    assert order_object.serving_time == datetime.time(13, 00, 00)
    assert order_object.order_lines.count() == 1
    order_line_object = order_object.order_lines.all()[0]
    assert order_line_object.product == catering_product
    assert order_line_object.quantity == 2


@pytest.mark.django_db
def test_order_update(user_api_client, reservation2, catering_product2, catering_product3, catering_order,
                      update_order_data):
    detail_url = get_detail_url(catering_order)
    response = user_api_client.put(detail_url, data=update_order_data, format='json')
    assert response.status_code == 200

    assert CateringOrder.objects.count() == 1
    order_object = CateringOrder.objects.latest('id')
    assert order_object.created_at and order_object.modified_at
    assert order_object.reservation == reservation2
    assert order_object.serving_time is None
    assert order_object.order_lines.count() == 2
    assert CateringOrderLine.objects.count() == 2

    order_line_object = order_object.order_lines.all()[0]
    assert order_line_object.product == catering_product2
    assert order_line_object.quantity == 1
    order_line_object2 = order_object.order_lines.all()[1]
    assert order_line_object2.product == catering_product3
    assert order_line_object2.quantity == 7


@pytest.mark.django_db
def test_product_removal_with_zero_quantity(user_api_client, catering_product, new_order_data):
    product2 = CateringProduct.objects.create(category=catering_product.category, name="Pulla")
    new_order_data['order_lines'].append(dict(product=product2.id, quantity=1))
    response = user_api_client.post(LIST_URL, data=new_order_data, format='json')
    assert response.status_code == 201
    order = CateringOrder.objects.last()
    assert order.order_lines.count() == 2

    detail_url = get_detail_url(order)
    new_order_data['order_lines'][1]['quantity'] = 0
    response = user_api_client.put(detail_url, data=new_order_data, format='json')
    assert response.status_code == 200
    assert order.order_lines.count() == 1


@pytest.mark.django_db
def test_cannot_modify_orders_if_no_permission(user_api_client, user2, catering_order, reservation3,
                                               new_order_data):
    error_message = "No permission to modify this reservation's catering orders."

    # try to create an order
    new_order_data['reservation'] = reservation3.pk
    response = user_api_client.post(LIST_URL, data=new_order_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 403
    assert error_message in str(response.data)

    # try to update an order
    detail_url = get_detail_url(catering_order)
    response = user_api_client.put(detail_url, data=new_order_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 403
    assert error_message in str(response.data)

    response = user_api_client.patch(
        detail_url, data={'reservation': reservation3.pk}, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 403
    assert error_message in str(response.data)

    # try to update an order belonging to another user
    user_api_client.force_authenticate(user=user2)
    response = user_api_client.patch(
        detail_url, data={'reservation': reservation3.pk}, format='json', HTTP_ACCEPT_LANGUAGE='en'
    )
    assert response.status_code == 404  # user can't even access the catering order

    # after giving a permission to view the catering orders, we still can't modify it
    resource = catering_order.reservation.resource
    assign_perm('unit:can_view_reservation_catering_orders', user2, resource.unit)
    response = user_api_client.get(detail_url, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 200
    response = user_api_client.put(detail_url, data=response.data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 403

    response = user_api_client.get(detail_url, format='json', HTTP_ACCEPT_LANGUAGE='en')
    # but now we can!
    assign_perm('unit:can_modify_reservation_catering_orders', user2, resource.unit)
    response = user_api_client.put(detail_url, data=response.data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 200


@pytest.mark.django_db
def test_can_view_others_orders_if_has_perm(user_api_client, user2, catering_order, reservation):
    user_api_client.force_authenticate(user=user2)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert not response.data['results']

    assign_perm('unit:can_view_reservation_catering_orders', user2, reservation.resource.unit)
    user_api_client.force_authenticate(user=user2)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, catering_order)


@pytest.mark.django_db
def test_order_cannot_contain_products_from_several_providers(user_api_client, catering_product, catering_product2,
                                                              new_order_data):
    new_order_data['order_lines'] = [
        {
            'product': catering_product.pk,
        },
        {
            'product': catering_product2.pk,
        }
    ]

    response = user_api_client.post(LIST_URL, data=new_order_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'The order contains products from several providers.' in str(response.data)


@pytest.mark.django_db
def test_order_cannot_have_provider_not_available_in_unit(user_api_client, reservation2, new_order_data):
    new_order_data['reservation'] = reservation2.pk

    response = user_api_client.post(LIST_URL, data=new_order_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert "The provider isn't available in the reservation's unit." in str(response.data)


@pytest.mark.django_db
def test_reservation_filter(user_api_client, catering_order, reservation, reservation2, reservation3):
    catering_order2 = CateringOrder.objects.create(
        reservation=reservation2,
        provider=catering_order.provider,
        invoicing_data='123456',
    )
    catering_order3 = CateringOrder.objects.create(
        reservation=reservation2,
        provider=catering_order.provider,
        invoicing_data='654321',
    )
    catering_order_that_should_not_be_visible = CateringOrder.objects.create(
        reservation=reservation3,
        provider=catering_order.provider,
        invoicing_data='xxx',
    )

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order, catering_order2, catering_order3))

    response = user_api_client.get(LIST_URL + '?reservation=%s' % reservation.pk)
    assert response.status_code == 200
    assert_response_objects(response, catering_order)

    response = user_api_client.get(LIST_URL + '?reservation=%s' % reservation2.pk)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order2, catering_order3))

    response = user_api_client.get(LIST_URL + '?reservation=%s' % reservation3.pk)
    assert response.status_code == 200
    assert not len(response.data['results'])


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_catering_notifications(user, user_api_client, catering_product,
                                reservation, new_order_data):
    provider = catering_product.category.provider
    provider.notification_email = 'catering.person@caterer.org'
    provider.save()

    reservation.number_of_participants = 42
    reservation.save()

    #
    # Create
    #
    CREATED_BODY = """Resource: {{ resource }}
Reservation: {{ reservation|reservation_time }}
Participants: {{ reservation.number_of_participants }}
Serving time: {{ serving_time }}
Invoicing data: {{ invoicing_data }}
Message: {{ message }}
Order lines: {% for line in order_lines %}
  {{ line.quantity }}x {{ line.product }}
{% endfor %}
"""
    strings = [
        "Resource: %s" % reservation.resource.name,
        "Participants: %d" % reservation.number_of_participants,
        "Reservation: to 4.4.2115 klo 9.00–10.00",
        "Serving time: 13.00",
        "Invoicing data: %s" % new_order_data['invoicing_data'],
        "Message: %s" % new_order_data['message'],
        "  2x Kahvi\n"
    ]
    NotificationTemplate.objects.language(DEFAULT_LANG).create(
        type=NotificationType.CATERING_ORDER_CREATED,
        short_message="Catering order for {{ resource }} created",
        subject="Catering order for {{ resource }} created",
        body=CREATED_BODY
    )

    response = user_api_client.post(LIST_URL, data=new_order_data, format='json')
    assert response.status_code == 201

    user.preferred_language = DEFAULT_LANG
    user.save()

    check_received_mail_exists("Catering order for %s created" % reservation.resource.name,
                               provider.notification_email, strings)

    # Test that serving time is set to the reservation begin time
    # if no specific serving time is given.
    order = CateringOrder.objects.first()
    order.serving_time = None
    order.save()
    context = order.get_notification_context(DEFAULT_LANG)
    assert context['serving_time'] == '9.00'

    #
    # Modify
    #
    product2 = CateringProduct.objects.create(
        name_fi='Aatsipoppa',
        category=catering_product.category,
    )
    NotificationTemplate.objects.language(DEFAULT_LANG).create(
        type=NotificationType.CATERING_ORDER_MODIFIED,
        short_message="Catering order for {{ resource }} modified",
        subject="Catering order for {{ resource }} modified",
        body=CREATED_BODY
    )
    strings = [
        "  3x Kahvi\n"
        "  4x Aatsipoppa\n"
    ]

    new_order_data['order_lines'][0]['quantity'] = 3
    new_order_data['order_lines'].append(dict(product=product2.id, quantity=4))
    new_order_data['serving_time'] = None

    detail_url = get_detail_url(order)
    response = user_api_client.put(detail_url, data=new_order_data, format='json')
    assert response.status_code == 200
    check_received_mail_exists("Catering order for %s modified" % reservation.resource.name,
                               provider.notification_email, strings)

    # Make sure we send a notification also if the underlying reservation changes.
    reservation = CateringOrder.objects.first().reservation
    reservation.begin += datetime.timedelta(hours=1)
    reservation.end += datetime.timedelta(hours=1)
    reservation.save()
    reservation.set_state(Reservation.CONFIRMED, reservation.user)

    check_received_mail_exists("Catering order for %s modified" % reservation.resource.name,
                               provider.notification_email, ["Serving time: 10.00"])

    #
    # Delete
    #
    NotificationTemplate.objects.language(DEFAULT_LANG).create(
        type=NotificationType.CATERING_ORDER_DELETED,
        short_message="Catering order for {{ resource }} deleted",
        subject="Catering order for {{ resource }} deleted",
        body=""
    )

    response = user_api_client.delete(detail_url, data=new_order_data, format='json')
    assert response.status_code == 204
    check_received_mail_exists("Catering order for %s deleted" % reservation.resource.name,
                               provider.notification_email, [])

    response = user_api_client.post(LIST_URL, data=new_order_data, format='json')
    assert response.status_code == 201
    reservation.set_state(Reservation.CANCELLED, reservation.user)
    check_received_mail_exists("Catering order for %s deleted" % reservation.resource.name,
                               provider.notification_email, [])
