import pytest
from parler.utils.context import switch_language

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
        html_body="test <b>HTML</b> body, variable value: {{ html_body_var }}!",
    )
    template.set_current_language('fi')
    template.short_message = "testilyhytviesti, muuttujan arvo: {{ short_message_var }}!"
    template.subject = "testiotsikko, muuttujan arvo: {{ subject_var }}!"
    template.body = "testiruumis, muuttujan arvo: {{ body_var }}!"
    template.html_body = "testi<b>hötömölö</b>ruumis, muuttujan arvo: {{ html_body_var }}!"
    template.save()

    return template


@pytest.mark.django_db
def test_notification_template_rendering(notification_template):
    context = {
        'short_message_var': 'foo',
        'subject_var': 'bar',
        'body_var': 'baz',
        'html_body_var': 'foo <b>bar</b> baz',
    }

    rendered = render_notification_template(NotificationType.TEST, context, 'en')
    assert len(rendered) == 4
    assert rendered['short_message'] == "test short message, variable value: foo!"
    assert rendered['subject'] == "test subject, variable value: bar!"
    assert rendered['body'] == "test body, variable value: baz!"
    assert rendered['html_body'] == "test <b>HTML</b> body, variable value: foo <b>bar</b> baz!"

    rendered = render_notification_template(NotificationType.TEST, context, 'fi')
    assert len(rendered) == 4
    assert rendered['short_message'] == "testilyhytviesti, muuttujan arvo: foo!"
    assert rendered['subject'] == "testiotsikko, muuttujan arvo: bar!"
    assert rendered['body'] == "testiruumis, muuttujan arvo: baz!"
    assert rendered['html_body'] == "testi<b>hötömölö</b>ruumis, muuttujan arvo: foo <b>bar</b> baz!"


@pytest.mark.django_db
def test_notification_template_rendering_empty_text_body(notification_template):
    context = {
        'short_message_var': 'foo',
        'subject_var': 'bar',
        'body_var': 'baz',
        'html_body_var': 'foo <b>bar</b> baz',
    }

    with switch_language(notification_template, 'fi'):
        notification_template.body = ''
        notification_template.save()

    rendered = render_notification_template(NotificationType.TEST, context, 'fi')
    assert len(rendered) == 4
    assert rendered['short_message'] == "testilyhytviesti, muuttujan arvo: foo!"
    assert rendered['subject'] == "testiotsikko, muuttujan arvo: bar!"
    assert rendered['body'] == "testihötömölöruumis, muuttujan arvo: foo bar baz!"
    assert rendered['html_body'] == "testi<b>hötömölö</b>ruumis, muuttujan arvo: foo <b>bar</b> baz!"


@pytest.mark.django_db
def test_notification_template_rendering_empty_html_body(notification_template):
    context = {
        'short_message_var': 'foo',
        'subject_var': 'bar',
        'body_var': 'baz',
        'html_body_var': 'foo <b>bar</b> baz',
    }

    with switch_language(notification_template, 'fi'):
        notification_template.html_body = ''
        notification_template.save()

    rendered = render_notification_template(NotificationType.TEST, context, 'fi')
    assert len(rendered) == 4
    assert rendered['short_message'] == "testilyhytviesti, muuttujan arvo: foo!"
    assert rendered['subject'] == "testiotsikko, muuttujan arvo: bar!"
    assert rendered['body'] == "testiruumis, muuttujan arvo: baz!"
    assert rendered['html_body'] == ""
