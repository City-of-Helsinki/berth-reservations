from django.db import ProgrammingError
from django_ilmoitin.registry import notifications

from .dummy_context import load_dummy_context
from .types import NotificationType

notifications.register(
    NotificationType.ORDER_APPROVED.value, NotificationType.ORDER_APPROVED.label,
)

try:
    load_dummy_context()
except ProgrammingError as e:
    if "django_content_type" in str(e):
        pass
    else:
        raise e


__all__ = ["NotificationType"]
