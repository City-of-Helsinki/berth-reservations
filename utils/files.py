import logging
import os

from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)


def remove_file(instance, field_name):
    file = getattr(instance, field_name, None)
    if file:
        try:
            os.unlink(file.path)
        except FileNotFoundError as e:
            logger.error(e, exc_info=True)
            capture_exception(e)
