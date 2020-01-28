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


class BerthLeaseAdmin(admin.ModelAdmin):
    inlines = (BerthLeaseChangeInline,)


class WinterStorageLeaseAdmin(admin.ModelAdmin):
    inlines = (WinterStorageLeaseChangeInline,)


admin.site.register(BerthLease, BerthLeaseAdmin)
admin.site.register(WinterStorageLease, WinterStorageLeaseAdmin)
