from django.conf import settings
from django.utils import dateformat, formats, timezone, translation


def localize_datetime(dt, language=settings.LANGUAGES[0][0]):
    with translation.override(language):
        return dateformat.format(
            timezone.localtime(dt), formats.get_format("DATETIME_FORMAT", lang=language)
        )
