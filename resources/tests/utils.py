# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core import mail
from django.test.testcases import SimpleTestCase
from django.utils.six import BytesIO
from django.utils.encoding import force_text
from PIL import Image

from resources.models import ResourceImage

UNSAFE_METHODS = ('post', 'put', 'patch', 'delete')


def get_test_image_data(size=(32, 32), color=(250, 250, 210), format="JPEG"):
    """
    Get binary image data with the given specs.

    :param size: Size tuple
    :type size: tuple[int, int]
    :param color: RGB color triple
    :type color: tuple[int, int, int]
    :param format: PIL image format specifier
    :type format: str
    :return: Binary data
    :rtype: bytes
    """
    img = Image.new(mode="RGB", size=size)
    img.paste(color)
    sio = BytesIO()
    img.save(sio, format=format, quality=75)
    return sio.getvalue()


def create_resource_image(resource, size=(32, 32), color=(250, 250, 210), format="JPEG", **instance_kwargs):
    """
    Create a ResourceImage object with image data with the given specs.

    :param resource: Resource to attach the ResourceImage to.
    :type resource: resources.models.Resource
    :param size: Size tuple
    :type size: tuple[int, int]
    :param color: RGB color triple
    :type color: tuple[int, int, int]
    :param format: PIL image format specifier
    :type format: str
    :param instance_kwargs: Other kwargs for `ResourceImage`. Some values are sanely prefilled.
    :type instance_kwargs: dict
    :return: Saved ResourceImage
    :rtype: resources.models.ResourceImage
    """
    instance_kwargs.setdefault("sort_order", resource.images.count() + 1)
    instance_kwargs.setdefault("type", "main")
    instance_kwargs.setdefault("image", ContentFile(
        get_test_image_data(size=size, color=color, format=format),
        name="%s.%s" % (instance_kwargs["sort_order"], format.lower())
    ))
    ri = ResourceImage(resource=resource, **instance_kwargs)
    ri.full_clean()
    ri.save()
    return ri


_dummy_test_case = SimpleTestCase()


def assert_response_contains(response, text, **kwargs):
    _dummy_test_case.assertContains(response=response, text=text, **kwargs)


def assert_response_does_not_contain(response, text, **kwargs):
    _dummy_test_case.assertNotContains(response=response, text=text, **kwargs)


def get_form_data(form, prepared=False):
    data = {}
    for name, field in form.fields.items():
        prefixed_name = form.add_prefix(name)
        data_value = field.widget.value_from_datadict(form.data, form.files, prefixed_name)

        if data_value:
            value = data_value
            data[prefixed_name] = value
        else:
            if not field.show_hidden_initial:
                initial_value = form.initial.get(name, field.initial)
                if callable(initial_value):
                    initial_value = initial_value()
            else:
                initial_prefixed_name = form.add_initial_prefix(name)
                hidden_widget = field.hidden_widget()
                try:
                    initial_value = field.to_python(hidden_widget.value_from_datadict(
                        form.data, form.files, initial_prefixed_name))
                except ValidationError:
                    form._changed_data.append(name)
                    continue
            value = initial_value
        if prepared:
            value = field.prepare_value(value)
            if value is None:
                continue
        data[prefixed_name] = value
    return data


def check_disallowed_methods(api_client, urls, disallowed_methods):
    """
    Check that given urls return http 405 (or 401 for unauthenticad users)

    :param api_client: API client that executes the requests
    :type api_client: DRF APIClient
    :param urls: urls to check
    :type urls: tuple [str]
    :param disallowed_methods: methods that should ne disallowed
    :type disallowed_methods: tuple [str]
    """

    # endpoints return 401 instead of 405 if there is no user
    expected_status_codes = (401, 405) if api_client.handler._force_user is None else (405, )
    for url in urls:
        for method in disallowed_methods:
            assert getattr(api_client, method)(url).status_code in expected_status_codes


def check_only_safe_methods_allowed(api_client, urls):
    check_disallowed_methods(api_client, urls, UNSAFE_METHODS)


def assert_non_field_errors_contain(response, text):
    """
    Check if any of the response's non field errors contain the given text.

    :type response: Response
    :type text: str
    """
    error_messages = [force_text(error_message) for error_message in response.data['non_field_errors']]
    assert any(text in error_message for error_message in error_messages)


def _mail_exists(subject, to, message):
    for mail_instance in mail.outbox:
        if subject not in mail_instance.subject:
            continue
        if set(mail_instance.to) != set([to]):
            continue
        mail_message = str(mail_instance.message())
        if message not in mail_message:
            continue
        return True
    return False


def check_received_mail_exists(subject, to, message, clear_outbox=True):
    assert _mail_exists(subject, to, message)
    if clear_outbox:
        mail.outbox = []


def get_field_errors(validation_error, field_name):
    """
    Return an individual field's validation error messages.

    :type validation_error: Django ValidationError
    :type field_name: str
    :rtype: list
    """
    error_dict = validation_error.error_dict
    assert field_name in error_dict
    return error_dict[field_name][0].messages
