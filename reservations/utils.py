from csv import DictWriter

from django.conf import settings
from django.utils import dateformat, formats, timezone, translation


def export_reservations_as_csv(reservations, stream):
    fieldnames = [
        'reservation_date',
        'first_name',
        'last_name',
        'email',
        'data'
    ]
    writer = DictWriter(stream, fieldnames=fieldnames)
    writer.writer.writerow(['sep=,'])
    writer.writeheader()
    for reservation in reservations:
        writer.writerow({
            'reservation_date': reservation.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
            'first_name': reservation.first_name,
            'last_name': reservation.last_name,
            'email': reservation.email,
            'data': reservation.data
        })
    return stream


def localize_datetime(dt, language=settings.LANGUAGES[0][0]):
    translation.activate(language)
    return dateformat.format(
        timezone.localtime(dt), formats.get_format('DATETIME_FORMAT', lang=language))
