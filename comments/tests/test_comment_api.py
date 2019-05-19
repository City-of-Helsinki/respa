import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.core import mail
from django.test.utils import override_settings
from guardian.shortcuts import assign_perm

from caterings.models import CateringOrder
from resources.models import Reservation, ResourceGroup

from resources.tests.test_reservation_api import reservation, reservation2, reservation3
from resources.tests.utils import assert_response_objects
from caterings.tests.conftest import (
    catering_order, catering_order2, catering_order3, catering_product, catering_product2, catering_product3,
    catering_product_category, catering_product_category2, catering_provider, catering_provider2,
)
from comments.models import Comment
from notifications.models import NotificationTemplate, NotificationType, DEFAULT_LANG, format_datetime_tz
from notifications.tests.utils import check_received_mail_exists


LIST_URL = reverse('comment-list')


@pytest.fixture
def new_catering_order_comment_data(catering_order):
    return {
        'target_type': 'catering_order',
        'target_id': catering_order.id,
        'text': 'new catering order comment text',
    }


def get_detail_url(resource):
    return reverse('comment-detail', kwargs={'pk': resource.pk})


@pytest.fixture
def new_reservation_comment_data(reservation):
    return {
        'target_type': 'reservation',
        'target_id': reservation.id,
        'text': 'new comment text',
    }


@pytest.fixture
def reservation_comment(reservation, user):
    return Comment.objects.create(
        content_type=ContentType.objects.get_for_model(Reservation),
        object_id=reservation.id,
        created_by=user,
        text='test reservation comment text',
    )


@pytest.fixture
def reservation2_comment(reservation2, user):
    return Comment.objects.create(
        content_type=ContentType.objects.get_for_model(Reservation),
        object_id=reservation2.id,
        created_by=user,
        text='test reservation 2 comment text',
    )


@pytest.fixture
def catering_order_comment(catering_order, user):
    return Comment.objects.create(
        content_type=ContentType.objects.get_for_model(CateringOrder),
        object_id=catering_order.id,
        created_by=user,
        text='test catering order comment text',
    )


@pytest.fixture
def catering_order2_comment(catering_order2, user):
    return Comment.objects.create(
        content_type=ContentType.objects.get_for_model(CateringOrder),
        object_id=catering_order2.id,
        created_by=user,
        text='test catering order 2 comment text',
    )


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_comment_endpoints_get(user_api_client, user, catering_order_comment, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(catering_order_comment)

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
        'created_by',
        'target_type',
        'target_id',
        'text',
    }
    assert len(data.keys()) == len(expected_keys)
    assert set(data.keys()) == expected_keys

    assert data['id'] and data['created_at']
    author = data['created_by']
    assert len(author.keys()) == 1
    assert author['display_name'] == user.get_display_name()
    assert data['target_type'] == 'catering_order'
    assert data['text'] == 'test catering order comment text'


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_comment_create(
        user_api_client, user, general_admin,
        reservation, new_reservation_comment_data):
    COMMENT_CREATED_BODY = """Target type: {{ target_type }}
Created by: {{ created_by.display_name }}
Created at: {{ created_at|format_datetime }}
Resource: {{ reservation.resource }}
Reservation: {{ reservation|reservation_time }}
{{ text }}
"""
    NotificationTemplate.objects.language(DEFAULT_LANG).create(
        type=NotificationType.RESERVATION_COMMENT_CREATED,
        short_message="Reservation comment added for {{ reservation.resource }}",
        subject="Reservation comment added for {{ reservation.resource }}",
        body=COMMENT_CREATED_BODY
    )

    user.preferred_language = DEFAULT_LANG
    user.save()

    unit = reservation.resource.unit
    unit.manager_email = 'manager@management.com'
    unit.save()

    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data)
    assert response.status_code == 201

    assert Comment.objects.count() == 1
    new_comment = Comment.objects.latest('id')
    assert new_comment.created_at
    assert new_comment.created_by == user
    assert new_comment.content_type == ContentType.objects.get_for_model(Reservation)
    assert new_comment.object_id == reservation.id
    assert new_comment.text == new_reservation_comment_data['text']

    created_at = format_datetime_tz(new_comment.created_at, reservation.resource.unit.get_tz())
    strings = [
        "Created by: %s" % user.get_display_name(),
        "Created at: %s" % created_at,
        "Resource: %s" % reservation.resource.name,
        "Reservation: to 4.4.2115 klo 9.00–10.00",
        new_reservation_comment_data['text'],
    ]

    check_received_mail_exists("Reservation comment added for %s" % reservation.resource.name,
                               unit.manager_email, strings)

    # Next make sure that a comment by another user reaches the reserver
    user_api_client.force_authenticate(user=general_admin)
    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data)
    assert response.status_code == 201
    assert Comment.objects.count() == 2

    assert len(mail.outbox) == 2
    check_received_mail_exists("Reservation comment added for %s" % reservation.resource.name,
                               user.email, [])


@pytest.mark.django_db
def test_catering_order_comment_create(user_api_client, user, catering_order, new_catering_order_comment_data):
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data)
    assert response.status_code == 201

    new_comment = Comment.objects.latest('id')
    assert new_comment.created_at
    assert new_comment.created_by == user
    assert new_comment.content_type == ContentType.objects.get_for_model(CateringOrder)
    assert new_comment.object_id == catering_order.id
    assert new_comment.text == 'new catering order comment text'


@pytest.mark.django_db
def test_cannot_modify_or_delete_comment(user_api_client, reservation_comment, new_reservation_comment_data):
    url = get_detail_url(reservation_comment)

    response = user_api_client.put(url, data=new_reservation_comment_data)
    assert response.status_code == 405

    response = user_api_client.patch(url, data=new_reservation_comment_data)
    assert response.status_code == 405

    response = user_api_client.delete(url, data=new_reservation_comment_data)
    assert response.status_code == 405


@pytest.mark.parametrize('data_changes', (
    {'target_type': 'invalid type'},
    {'target_type': 'resource'},
    {'target_id': 777},
))
@pytest.mark.django_db
def test_comment_create_illegal_target(user_api_client, new_reservation_comment_data, data_changes):
    new_reservation_comment_data.update(data_changes)
    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data)
    assert response.status_code == 400


@pytest.mark.django_db
def test_reservation_comment_visibility(user_api_client, user, user2, reservation_comment, reservation2_comment,
                                        reservation, reservation2, test_unit, test_unit2):

    # two reservation comments made on own reservations, both should be visible
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (reservation_comment, reservation2_comment))

    # the second comment is created by the other user, still both should be visible
    reservation2_comment.created_by = user2
    reservation2_comment.save()
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (reservation_comment, reservation2_comment))

    # the second comment is created by the other user to her reservation, it should be hidden
    reservation2.user = user2
    reservation2.save()
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, reservation_comment)

    # adding comment access perm to an unrelated unit, the hidden comment should still be hidden
    assign_perm('unit:can_access_reservation_comments', user, test_unit)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, reservation_comment)

    # adding comment access perm to the second commit's unit, both comment should be visible once again
    assign_perm('unit:can_access_reservation_comments', user, test_unit2)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (reservation_comment, reservation2_comment))


@pytest.mark.django_db
def test_catering_order_comment_visibility(user_api_client, user, user2, catering_order2, catering_order_comment,
                                           catering_order2_comment, test_unit, test_unit2):

    # two reservation comments made on own reservations, both should be visible
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order_comment, catering_order2_comment))

    # the second comment is created by the other user, still both should be visible
    catering_order2_comment.created_by = user2
    catering_order2_comment.save()
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order_comment, catering_order2_comment))

    # the second comment is created by the other user to her reservation, it should be hidden
    catering_order2.reservation.user = user2
    catering_order2.reservation.save()
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, catering_order_comment)

    # adding comment access perm to an unrelated unit, the hidden comment should still be hidden
    assign_perm('unit:can_access_reservation_comments', user, test_unit)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, catering_order_comment)

    # adding comment access perm to the second commit's unit, both comment should be visible once again
    assign_perm('unit:can_view_reservation_catering_orders', user, test_unit2)
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order_comment, catering_order2_comment))


@pytest.mark.django_db
def test_reservation_comment_creation_rights(user_api_client, user, reservation3, new_reservation_comment_data):
    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data)
    assert response.status_code == 201

    # other user's reservation
    new_reservation_comment_data['target_id'] = reservation3.id
    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'You cannot comment this object.' in str(response.data)

    assign_perm('unit:can_access_reservation_comments', user, reservation3.resource.unit)
    response = user_api_client.post(LIST_URL, data=new_reservation_comment_data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_catering_order_comment_creation_rights(user_api_client, user, catering_order, catering_order3,
                                                new_catering_order_comment_data):
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data)
    assert response.status_code == 201

    # other user's reservation
    new_catering_order_comment_data['target_id'] = catering_order3.id
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'You cannot comment this object.' in str(response.data)

    assign_perm('unit:can_view_reservation_catering_orders', user, catering_order3.reservation.resource.unit)
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_reservation_comment_filtering(user_api_client, reservation_comment, reservation2_comment,
                                       catering_order_comment, reservation):
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (reservation_comment, reservation2_comment, catering_order_comment))

    response = user_api_client.get(LIST_URL + '?target_type=reservation')
    assert response.status_code == 200
    assert_response_objects(response, (reservation_comment, reservation2_comment))

    response = user_api_client.get(LIST_URL + '?target_type=reservation&target_id=%s' % reservation.id)
    assert response.status_code == 200
    assert_response_objects(response, reservation_comment)


@pytest.mark.django_db
def test_catering_order_comment_filtering(user_api_client, catering_order, catering_order_comment,
                                          catering_order2_comment, reservation_comment):
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_order_comment, catering_order2_comment, reservation_comment))

    response = user_api_client.get(LIST_URL + '?target_type=catering_order')
    assert response.status_code == 200
    assert_response_objects(response, (catering_order_comment, catering_order2_comment))

    response = user_api_client.get(LIST_URL + '?target_type=catering_order&target_id=%s' % catering_order.id)
    assert response.status_code == 200
    assert_response_objects(response, catering_order_comment)


@pytest.mark.django_db
def test_non_commentable_model_comments_hidden(user_api_client, resource_group, user):
    Comment.objects.create(
        content_type=ContentType.objects.get_for_model(ResourceGroup),
        object_id=resource_group.id,
        created_by=user,
        text='this comment should be hidden because ResourceGroup in not a commentable model',
    )

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert not response.data['results']


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_catering_order_comment_create2(
        user_api_client, user, general_admin, catering_order,
        new_catering_order_comment_data):
    COMMENT_CREATED_BODY = """Target type: {{ target_type }}
Created by: {{ created_by.display_name }}
Created at: {{ created_at|format_datetime }}
Resource: {{ catering_order.reservation.resource.name }}
Reservation: {{ catering_order.reservation|reservation_time }}
Serving time: {{ catering_order.serving_time }}
{{ text }}
"""
    NotificationTemplate.objects.language(DEFAULT_LANG).create(
        type=NotificationType.CATERING_ORDER_COMMENT_CREATED,
        short_message="Catering comment added for {{ catering_order.reservation.resource.name }}",
        subject="Catering comment added for {{ catering_order.reservation.resource.name }}",
        body=COMMENT_CREATED_BODY
    )

    user.preferred_language = DEFAULT_LANG
    user.save()

    provider = catering_order.get_provider()
    provider.notification_email = 'catering.person@caterer.org'
    provider.save()

    # First make sure that the notification from a user's comment reaches catering.
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data)
    assert response.status_code == 201

    assert Comment.objects.count() == 1
    comment = Comment.objects.first()
    reservation = catering_order.reservation

    created_at = format_datetime_tz(comment.created_at, reservation.resource.unit.get_tz())
    strings = [
        "Created by: %s" % user.get_display_name(),
        "Created at: %s" % created_at,
        "Resource: %s" % reservation.resource.name,
        "Reservation: to 4.4.2115 klo 9.00–10.00",
        "Serving time: 12.00",
        new_catering_order_comment_data['text'],
    ]

    check_received_mail_exists("Catering comment added for %s" % reservation.resource.name,
                               provider.notification_email, strings)

    # Next make sure that a comment by another user reaches the reserver
    user_api_client.force_authenticate(user=general_admin)
    response = user_api_client.post(LIST_URL, data=new_catering_order_comment_data)
    assert response.status_code == 201
    assert Comment.objects.count() == 2

    assert len(mail.outbox) == 2
    check_received_mail_exists("Catering comment added for %s" % reservation.resource.name,
                               user.email, [])
