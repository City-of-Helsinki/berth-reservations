import datetime
import logging

from anymail.exceptions import AnymailError
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from pytz import timezone

from notifications.enums import NotificationType
from notifications.utils import send_notification

from .models import HarborChoice, Reservation
from .utils import export_reservations_as_xlsx

logger = logging.getLogger(__name__)


class HarborChoiceInline(admin.TabularInline):
    model = HarborChoice
    ordering = ('priority',)
    fields = ('priority', 'harbor',)
    extra = 10
    max_num = 10


class ReservationAdmin(admin.ModelAdmin):
    inlines = [HarborChoiceInline, ]
    readonly_fields = ['created_at', ]
    fieldsets = [
        (None, {
            'fields': [
                'created_at',
                'is_processed',
            ],
        }),
        (_('Contact information'), {
            'fields': [
                'first_name',
                'last_name',
                'email',
                'phone_number',
                'address',
                'zip_code',
                'municipality',
                'company_name',
                'business_id',
            ],
        }),
        (_('Main boat information'), {
            'fields': [
                'boat_type',
                'boat_registration_number',
                'boat_name',
                'boat_model',
                'boat_length',
                'boat_width',
                'boat_draught',
                'boat_weight',
                'accessibility_required',
            ],
        }),
        (_('Large vessel information'), {
            'fields': [
                'boat_propulsion',
                'boat_hull_material',
                'boat_intended_use',
                'renting_period',
                'rent_from',
                'rent_till',
                'boat_is_inspected',
                'boat_is_insured',
                'agree_to_terms',
            ],
        }),
        (_('Other information'), {
            'fields': [
                'language',
                'accept_boating_newsletter',
                'accept_fitness_news',
                'accept_library_news',
                'accept_other_culture_news',
                'information_accuracy_confirmed',
            ],
        }),
    ]
    list_display = ('created_at', 'first_name', 'last_name')
    actions = ["export_reservations", "resend_reservation_confirmation"]

    def export_reservations(self, request, queryset):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        local_datetime_now_as_str = (
            datetime.datetime
            .now(timezone(settings.TIME_ZONE))
            .strftime('%Y-%m-%d_%H-%M-%S')
        )
        filename = "berth_reservations_" + local_datetime_now_as_str
        response['Content-Disposition'] = 'attachment; filename=%s.xlsx' % filename

        response.content = export_reservations_as_xlsx(queryset)
        return response

    export_reservations.short_description = _("Download list of chosen reservations in Excel file")

    def resend_reservation_confirmation(self, request, queryset):
        resent_count = 0
        for reservation in queryset:
            try:
                send_notification(
                    reservation.email,
                    NotificationType.RESERVATION_CREATED,
                    reservation.get_notification_context(),
                    reservation.language
                )
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
    resend_reservation_confirmation.allowed_permissions = ('resend',)

    def has_resend_permission(self, request):
        opts = self.opts
        codename = get_permission_codename('resend', opts)
        return request.user.has_perm('%s.%s' % (opts.app_label, codename))


admin.site.register(Reservation, ReservationAdmin)

# Register Permission model for GUI management of permissions
admin.site.register(Permission)
