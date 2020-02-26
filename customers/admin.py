from django.contrib import admin

from applications.admin import BerthApplicationInline
from leases.admin import BerthLeaseInline

from .models import Boat, Company, CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    fk_name = "user"
    extra = 0


class BoatInline(admin.StackedInline):
    model = Boat
    fk_name = "owner"
    extra = 0


class CompanyInline(admin.StackedInline):
    model = Company
    fk_name = "customer"
    extra = 0


class BoatAdmin(admin.ModelAdmin):
    pass


class CompanyAdmin(admin.ModelAdmin):
    pass


class CustomerProfileAdmin(admin.ModelAdmin):
    inlines = (BoatInline, CompanyInline, BerthApplicationInline, BerthLeaseInline)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Mark id field as readonly for existing objects
            return self.readonly_fields + ("id",)
        return self.readonly_fields


admin.site.register(Boat, BoatAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(CustomerProfile, CustomerProfileAdmin)
