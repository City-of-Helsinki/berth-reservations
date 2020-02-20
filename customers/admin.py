from django.contrib import admin

from .models import Boat, Company, CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    fk_name = "user"
    extra = 0


class BoatAdmin(admin.ModelAdmin):
    pass


class CompanyAdmin(admin.ModelAdmin):
    pass


admin.site.register(Boat, BoatAdmin)
admin.site.register(Company, CompanyAdmin)
