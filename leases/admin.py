from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline

from payments.models import Order

from .models import (
    BerthLease,
    BerthLeaseChange,
    WinterStorageLease,
    WinterStorageLeaseChange,
)


class BerthLeaseChangeInline(admin.StackedInline):
    model = BerthLeaseChange
    fk_name = "lease"
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class WinterStorageLeaseChangeInline(admin.StackedInline):
    model = WinterStorageLeaseChange
    fk_name = "lease"
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BerthLeaseInline(admin.StackedInline):
    model = BerthLease
    fk_name = "customer"
    raw_id_fields = ("berth", "application")
    extra = 0


class BaseLeaseAdmin(admin.ModelAdmin):
    def application_id(self, obj):
        return obj.application.id if obj.application else "-"

    def first_name(self, obj):
        return obj.application.first_name if obj.application else "-"

    def last_name(self, obj):
        return obj.application.last_name if obj.application else "-"

    list_filter = ("status",)
    list_display = (
        "id",
        "created_at",
        "start_date",
        "end_date",
        "first_name",
        "last_name",
        "status",
    )
    search_fields = (
        "id",
        "application__id",
        "application__first_name",
        "application__last_name",
    )


class GenericOrderInline(GenericStackedInline):
    ct_field = "_lease_content_type"
    ct_fk_field = "_lease_object_id"
    model = Order
    extra = 0
    exclude = ("_product_content_type", "_lease_content_type")


class BerthLeaseAdmin(BaseLeaseAdmin):
    inlines = (BerthLeaseChangeInline, GenericOrderInline)
    raw_id_fields = ("berth", "application")


class WinterStorageLeaseInline(admin.StackedInline):
    model = WinterStorageLease
    fk_name = "customer"
    raw_id_fields = ("application",)
    extra = 0


class WinterStorageLeaseAdmin(BaseLeaseAdmin):
    inlines = (WinterStorageLeaseChangeInline, GenericOrderInline)
    raw_id_fields = ("place", "section", "application")


admin.site.register(BerthLease, BerthLeaseAdmin)
admin.site.register(WinterStorageLease, WinterStorageLeaseAdmin)
