import pytest

from notifications.models import NotificationType, NotificationTemplate, render_notification_template


@pytest.fixture(scope='function')
def notification_type():
    setattr(NotificationType, 'TEST', 'test')
    yield NotificationType.TEST
    delattr(NotificationType, 'TEST')


@pytest.fixture
def notification_template(notification_type):
    template = NotificationTemplate.objects.language('en').create(
        type=NotificationType.TEST,
        short_message="test short message, variable value: {{ short_message_var }}!",
        subject="test subject, variable value: {{ subject_var }}!",
        body="test body, variable value: {{ body_var }}!",
    )
    template.set_current_language('fi')
    template.short_message = "testilyhytviesti, muuttujan arvo: {{ short_message_var }}!"
    template.subject = "testiotsikko, muuttujan arvo: {{ subject_var }}!"
    template.body = "testiruumis, muuttujan arvo: {{ body_var }}!"
    template.save()

    return template


@pytest.mark.django_db
def test_notification_template_rendering(notification_template):
    context = {
        'short_message_var': 'foo',
        'subject_var': 'bar',
        'body_var': 'baz',
    }

    rendered = render_notification_template(NotificationType.TEST, context, 'en')
    assert len(rendered) == 3
    assert rendered['short_message'] == "test short message, variable value: foo!"
    assert rendered['subject'] == "test subject, variable value: bar!"
    assert rendered['body'] == "test body, variable value: baz!"

    rendered = render_notification_template(NotificationType.TEST, context, 'fi')
    assert len(rendered) == 3
    assert rendered['short_message'] == "testilyhytviesti, muuttujan arvo: foo!"
    assert rendered['subject'] == "testiotsikko, muuttujan arvo: bar!"
    assert rendered['body'] == "testiruumis, muuttujan arvo: baz!"
