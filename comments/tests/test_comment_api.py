import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from resources.tests.test_reservation_api import reservation
from comments.models import Comment


LIST_URL = reverse('comment-list')


def get_detail_url(resource):
    return reverse('comment-detail', kwargs={'pk': resource.pk})


@pytest.fixture
def new_comment_data(reservation):
    return {
        'target_type': 'reservation',
        'target_id': reservation.id,
        'text': 'new comment text',
    }


@pytest.fixture
def reservation_comment(reservation, user):
    return Comment.objects.create(
        content_type=ContentType.objects.get(app_label='resources', model='reservation'),
        object_id=reservation.id,
        created_by=user,
        text='test reservation comment text',
    )


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_comment_endpoints_get(user_api_client, user, reservation_comment, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(reservation_comment)

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


@pytest.mark.django_db
def test_comment_create(user_api_client, user, reservation, new_comment_data):
    response = user_api_client.post(LIST_URL, data=new_comment_data)
    assert response.status_code == 201

    new_comment = Comment.objects.latest('id')
    assert new_comment.created_at
    assert new_comment.created_by == user
    assert new_comment.content_type == ContentType.objects.get(app_label='resources', model='reservation')
    assert new_comment.object_id == reservation.id
    assert new_comment.text == 'new comment text'


@pytest.mark.django_db
def test_cannot_modify_or_delete_comment(user_api_client, reservation_comment, new_comment_data):
    url = get_detail_url(reservation_comment)

    response = user_api_client.put(url, data=new_comment_data)
    assert response.status_code == 405

    response = user_api_client.patch(url, data=new_comment_data)
    assert response.status_code == 405

    response = user_api_client.delete(url, data=new_comment_data)
    assert response.status_code == 405


@pytest.mark.parametrize('data_changes', (
    {'target_type': 'invalid type'},
    {'target_type': 'resource'},
    {'target_id': 777},
))
@pytest.mark.django_db
def test_comment_create_illegal_target(user_api_client, new_comment_data, data_changes):
    new_comment_data.update(data_changes)
    response = user_api_client.post(LIST_URL, data=new_comment_data)
    assert response.status_code == 400
