from django.contrib import admin

from .models import VismaBerthContract, VismaWinterStorageContract


class ContractAdmin(admin.ModelAdmin):
    search_fields = ("lease__id",)
    list_filter = ("status",)
    list_display = ("id", "created_at", "document_id", "lease_id", "status")

    def lease_id(self, obj):
        return obj.lease.id if obj.lease else None


admin.site.register(VismaBerthContract, ContractAdmin)
admin.site.register(VismaWinterStorageContract, ContractAdmin)
