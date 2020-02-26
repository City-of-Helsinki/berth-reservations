from django.contrib import admin

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


class BerthLeaseAdmin(admin.ModelAdmin):
    inlines = (BerthLeaseChangeInline,)
    raw_id_fields = ("berth", "application")


class WinterStorageLeaseAdmin(admin.ModelAdmin):
    inlines = (WinterStorageLeaseChangeInline,)
    raw_id_fields = ("place", "application")


admin.site.register(BerthLease, BerthLeaseAdmin)
admin.site.register(WinterStorageLease, WinterStorageLeaseAdmin)
