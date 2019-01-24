import pytest

from berth_reservations.tests.conftest import *  # noqa


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.NOTIFICATIONS_ENABLED = True
