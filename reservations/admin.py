import datetime
import logging

from anymail.exceptions import AnymailError
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from notifications.enums import NotificationType
from notifications.utils import send_notification

from .models import Reservation
from .utils import export_reservations_as_csv

logger = logging.getLogger(__name__)


class ReservationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'first_name', 'last_name')
    actions = ["export_reservations", "resend_reservation_confirmation"]

    def export_reservations(self, request, queryset):
        response = HttpResponse(content_type='text/csv')

        filename = "berth_reservations_" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % filename

        export_reservations_as_csv(queryset, response)
        return response

    export_reservations.short_description = _("Download list of chosen reservations in CSV format")

    def resend_reservation_confirmation(self, request, queryset):
        resent_count = 0
        for reservation in queryset:
            try:
                send_notification(reservation.email, NotificationType.RESERVATION_CREATED)
                resent_count += 1
            except (OSError, AnymailError):
                logger.error(
                    'Failed to resend confirmation for reservation {}'.format(reservation.id)
                )

        self.message_user(
            request,
            _("Resent confirmation for %d reservation(s)") % resent_count,
            messages.SUCCESS)

    resend_reservation_confirmation.short_description = _("Send confirmation again for chosen reservation")


admin.site.register(Reservation, ReservationAdmin)
