from django.contrib import admin
from django.forms import TypedChoiceField, UUIDField
from django.utils import timezone
from django.utils.datetime_safe import strftime
from django.utils.translation import gettext_lazy as _

from leases.models import BerthLease, WinterStorageLease

from .enums import LeaseOrderType
from .models import (
    AdditionalProduct,
    BerthProduct,
    BerthSwitchOffer,
    BerthSwitchOfferLogEntry,
    Order,
    OrderLine,
    OrderLogEntry,
    OrderRefund,
    OrderRefundLogEntry,
    OrderToken,
    WinterStorageProduct,
)
from .utils import currency, percentage


class AdditionalProductAdmin(admin.ModelAdmin):
    readonly_fields = (
        "product_type",
        "pretax_price",
    )

    @currency
    def pretax_price(self, obj):
        return obj.pretax_price if obj.price and obj.tax_percentage else None

    def product_type(self, obj):
        return obj.product_type

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"

    product_type.short_description = _("Product type")
    product_type.admin_order_field = "product_type"


class BerthProductAdmin(admin.ModelAdmin):
    list_display = (
        "min_width",
        "max_width",
        "tier_1_price",
        "tier_2_price",
        "tier_3_price",
    )


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    fk_name = "order"
    extra = 0
    readonly_fields = ("pretax_price",)

    @currency
    def pretax_price(self, obj):
        return obj.pretax_price if obj.price and obj.tax_percentage else None

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"


class OrderLogEntryInline(admin.StackedInline):
    model = OrderLogEntry
    fk_name = "order"
    extra = 0
    readonly_fields = ("created_at",)


class OrderRefundInline(admin.StackedInline):
    model = OrderRefund
    fk_name = "order"
    extra = 0
    readonly_fields = ("created_at",)


class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = "due_date"
    inlines = (OrderLineInline, OrderRefundInline, OrderLogEntryInline)
    exclude = ("_product_content_type", "_lease_content_type")
    readonly_fields = (
        "pretax_price",
        "total_pretax_price",
        "total_tax_percentage",
        "total_price",
        "order_number",
        "lease_order_type",
        "order_type",
        "place",
        "paid_at",
        "rejected_at",
        "cancelled_at",
    )
    list_display = (
        "id",
        "created_at",
        "order_number",
        "total_price",
        "status",
        "customer_name",
        "customer",
        "lease_id",
        "place",
        "product",
        "lease_order_type",
        "order_type",
    )
    list_filter = ("status", "order_type")
    search_fields = (
        "order_number",
        "customer__id",
        "customer_first_name",
        "customer_last_name",
        "customer_email",
    )

    def lease_order_type(self, obj):
        return LeaseOrderType(obj.lease_order_type).label

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "_product_object_id":
            bp_qs = BerthProduct.objects.all()
            wsp_qs = WinterStorageProduct.objects.all()
            choices = [
                (None, "----"),
                *[(product.id, str(product)) for product in list(bp_qs) + list(wsp_qs)],
            ]

            return TypedChoiceField(
                choices=choices,
                label=db_field.verbose_name.title(),
                required=False,
                empty_value=None,
            )
        if db_field.name == "_lease_object_id":
            kwargs["form_class"] = UUIDField
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @currency
    def pretax_price(self, obj):
        return (
            obj.pretax_price
            if obj.price is not None and obj.tax_percentage is not None
            else None
        )

    @currency
    def total_price(self, obj):
        return (
            obj.total_price
            if obj.price is not None and obj.tax_percentage is not None
            else None
        )

    @currency
    def total_pretax_price(self, obj):
        return (
            obj.total_pretax_price
            if obj.price is not None and obj.tax_percentage is not None
            else None
        )

    @percentage
    def total_tax_percentage(self, obj):
        return (
            obj.total_tax_percentage
            if obj.price is not None and obj.tax_percentage is not None
            else None
        )

    def lease_id(self, obj):
        return obj.lease.id if obj.lease else None

    def place(self, obj):
        if obj.lease:
            if isinstance(obj.lease, BerthLease):
                return obj.lease.berth
            elif isinstance(obj.lease, WinterStorageLease):
                return obj.lease.place or obj.lease.section
        return None

    def customer_name(self, obj):
        if obj.customer_first_name or obj.customer_last_name:
            return f"{obj.customer_first_name or ''} {obj.customer_last_name or ''}"

    def paid_at(self, obj):
        return strftime(timezone.localtime(obj.paid_at), "%d-%m-%Y %H:%M:%S",)

    def cancelled_at(self, obj):
        return strftime(timezone.localtime(obj.cancelled_at), "%d-%m-%Y %H:%M:%S",)

    def rejected_at(self, obj):
        return strftime(timezone.localtime(obj.rejected), "%d-%m-%Y %H:%M:%S",)

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"

    total_price.short_description = _("Total order price")
    total_price.admin_order_field = "total_price"

    total_pretax_price.short_description = _("Total order pretax price")
    total_pretax_price.admin_order_field = "total_pretax_price"

    total_tax_percentage.short_description = _("Total order tax percentage")
    total_tax_percentage.admin_order_field = "total_tax_percentage"

    place.short_description = _("Place")
    place.admin_order_field = "place"


class OrderRefundLogEntryInline(admin.StackedInline):
    model = OrderRefundLogEntry
    fk_name = "refund"
    extra = 0
    readonly_fields = ("created_at",)


class OrderRefundAdmin(admin.ModelAdmin):
    inlines = (OrderRefundLogEntryInline,)
    date_hierarchy = "created_at"
    list_display = (
        "id",
        "created_at",
        "refund_id",
        "order",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "refund_id",
        "order__customer__id",
    )


class OrderRefundLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "refund_id",
        "order_id",
        "from_status",
        "to_status",
        "created_at",
    )
    list_filter = ("from_status", "to_status")
    readonly_fields = ("created_at",)

    def order_id(self, obj):
        return obj.refund.order_id


class OrderTokenAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "order_number",
        "cancelled",
    )
    list_filter = ("cancelled",)
    search_fields = ("order__order_number",)
    actions = ("invalidate_tokens",)

    def order_number(self, obj):
        return obj.order.order_number

    order_number.short_description = _("Order number")

    def invalidate_tokens(self, request, queryset):
        queryset.update(cancelled=True)

    invalidate_tokens.short_description = _("Invalidate selected tokens")


class OrderInline(admin.StackedInline):
    model = Order
    extra = 0
    exclude = ("_product_content_type", "_lease_content_type")


class OrderLogEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "order_id", "from_status", "to_status", "created_at")
    list_filter = ("from_status", "to_status")
    search_fields = ("order__id",)
    readonly_fields = ("created_at",)

    def order_id(self, obj):
        return obj.order.id


class BerthSwitchOfferLogEntryInline(admin.StackedInline):
    model = BerthSwitchOfferLogEntry
    fk_name = "offer"
    extra = 0
    readonly_fields = ("created_at",)


class BerthSwitchOfferAdmin(admin.ModelAdmin):
    list_display = ("customer", "name", "application", "berth", "lease", "status")
    list_filter = ("status",)
    inlines = (BerthSwitchOfferLogEntryInline,)
    search_fields = (
        "application__id",
        "berth__id",
        "berth__number",
        "berth__pier__harbor__translations__name",
        "lease__id",
        "customer_first_name",
        "customer_last_name",
    )
    autocomplete_fields = ("customer", "application", "lease", "berth")
    date_hierarchy = "due_date"

    def name(self, obj):
        return f"{obj.customer_first_name} {obj.customer_last_name}"


class BerthSwitchOfferLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "from_status",
        "to_status",
        "created_at",
    )
    list_filter = ("from_status", "to_status")
    search_fields = ("refund__id", "refund__order__id")
    readonly_fields = ("created_at",)


admin.site.register([WinterStorageProduct, OrderLine])
admin.site.register(BerthProduct, BerthProductAdmin)
admin.site.register(AdditionalProduct, AdditionalProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLogEntry, OrderLogEntryAdmin)
admin.site.register(OrderRefund, OrderRefundAdmin)
admin.site.register(OrderRefundLogEntry, OrderRefundLogEntryAdmin)
admin.site.register(OrderToken, OrderTokenAdmin)
admin.site.register(BerthSwitchOfferLogEntry, BerthSwitchOfferLogEntryAdmin)
admin.site.register(BerthSwitchOffer, BerthSwitchOfferAdmin)
