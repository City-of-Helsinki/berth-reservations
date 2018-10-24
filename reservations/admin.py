import datetime

from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from .models import Reservation
from .utils import export_reservations_as_csv


class ReservationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'first_name', 'last_name')
    actions = ["export_reservations"]

    def export_reservations(self, request, queryset):
        response = HttpResponse(content_type='text/csv')

        filename = "berth_reservations_" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % filename

        export_reservations_as_csv(queryset, response)
        return response

    export_reservations.short_description = _("Download list of chosen reservations in CSV format")


admin.site.register(Reservation, ReservationAdmin)
