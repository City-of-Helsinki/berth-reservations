from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline

from contracts.models import VismaBerthContract, VismaWinterStorageContract
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

    def has_contract(self, obj):
        return obj.contract is not None

    has_contract.boolean = True

    list_filter = ("status",)

    date_hierarchy = "start_date"


class GenericOrderInline(GenericStackedInline):
    ct_field = "_lease_content_type"
    ct_fk_field = "_lease_object_id"
    model = Order
    extra = 0
    exclude = ("_product_content_type", "_lease_content_type")


class VismaBerthContractInline(admin.StackedInline):
    model = VismaBerthContract


class BerthLeaseAdmin(BaseLeaseAdmin):
    inlines = (BerthLeaseChangeInline, GenericOrderInline, VismaBerthContractInline)
    raw_id_fields = ("berth", "application")
    list_display = (
        "id",
        "created_at",
        "harbor",
        "pier",
        "berth_number",
        "start_date",
        "end_date",
        "first_name",
        "last_name",
        "application_id",
        "status",
        "has_contract",
    )
    search_fields = (
        "id",
        "application__id",
        "application__first_name",
        "application__last_name",
        "customer__id",
        "berth__pier__harbor__translations__name",
        "berth__pier__identifier",
        "berth__number",
    )

    def harbor(self, obj):
        return obj.berth.pier.harbor

    def pier(self, obj):
        return obj.berth.pier.identifier

    def berth_number(self, obj):
        return obj.berth.number


class GenericOrderInline(GenericStackedInline):
    readonly_fields = ("pk",)
    ct_field = "_lease_content_type"
    ct_fk_field = "_lease_object_id"
    model = Order
    extra = 0
    exclude = ("_product_content_type", "_lease_content_type")


class WinterStorageLeaseInline(admin.StackedInline):
    model = WinterStorageLease
    fk_name = "customer"
    raw_id_fields = ("application",)
    extra = 0


class VismaWinterStorageContractInline(admin.StackedInline):
    model = VismaWinterStorageContract


class WinterStorageLeaseAdmin(BaseLeaseAdmin):
    inlines = (
        WinterStorageLeaseChangeInline,
        GenericOrderInline,
        VismaWinterStorageContractInline,
    )
    raw_id_fields = ("place", "section", "application")
    list_display = (
        "id",
        "created_at",
        "area",
        "section",
        "place_number",
        "start_date",
        "end_date",
        "first_name",
        "last_name",
        "application_id",
        "status",
        "has_contract",
    )
    search_fields = (
        "id",
        "application__id",
        "application__first_name",
        "application__last_name",
        "customer__id",
        "place__winter_storage_section__area__translations__name",
        "place__winter_storage_section__identifier",
        "place__number",
        "section__identifier",
    )

    def area(self, obj):
        section = obj.section or obj.place.winter_storage_section
        return section.area

    def section(self, obj):
        section = obj.section or obj.place.winter_storage_section
        return section.identifier

    def place_number(self, obj):
        return obj.place.number if obj.place else None


admin.site.register(BerthLease, BerthLeaseAdmin)
admin.site.register(WinterStorageLease, WinterStorageLeaseAdmin)
