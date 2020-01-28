from django.contrib import admin

from .models import Boat, CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    fk_name = "user"
    extra = 0


class BoatAdmin(admin.ModelAdmin):
    pass


admin.site.register(Boat, BoatAdmin)
