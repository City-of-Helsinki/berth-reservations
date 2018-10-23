from django.contrib import admin

from reservations.models import Reservation


class ReservationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'first_name', 'last_name')


admin.site.register(Reservation, ReservationAdmin)
