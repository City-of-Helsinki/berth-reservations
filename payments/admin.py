from django.contrib import admin
from django.forms import TypedChoiceField, UUIDField
from django.utils import timezone
from django.utils.datetime_safe import strftime
from django.utils.translation import gettext_lazy as _

from leases.models import BerthLease, WinterStorageLease

from .enums import LeaseOrderType, ProductServiceType
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
from .utils import currency, get_talpa_product_id, percentage, resolve_area


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
        "pricing_category",
    )
    list_filter = ("pricing_category",)
    ordering = (
        "pricing_category",
        "min_width",
        "max_width",
    )


class WinterStorageProductAdmin(admin.ModelAdmin):
    list_display = ("winter_storage_area", "price")

    @currency
    def price(self, obj):
        return obj.price_value

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(WinterStorageProductAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == "winter_storage_area":
            field.queryset = field.queryset.translated("fi")
        return field


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    fk_name = "order"
    extra = 0
    readonly_fields = (
        "pretax_price",
        "talpa_product_id",
    )

    @currency
    def pretax_price(self, obj):
        return obj.pretax_price if obj.price and obj.tax_percentage else None

    def talpa_product_id(self, obj):
        return (
            get_talpa_product_id(
                obj.product.id,
                resolve_area(obj.order),
                is_storage_on_ice=obj.product.service
                == ProductServiceType.STORAGE_ON_ICE,
            )
            if hasattr(obj, "product")
            else "-"
        )

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"

    talpa_product_id.short_description = _("Talpa product ID")
    talpa_product_id.admin_order_field = "talpa_product_id"


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
        "talpa_product_id",
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
    autocomplete_fields = ("customer",)
    ordering = ("-created_at",)
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

    def talpa_product_id(self, obj):
        return (
            get_talpa_product_id(obj.product.id, resolve_area(obj))
            if hasattr(obj, "product")
            else "-"
        )

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

    talpa_product_id.short_description = _("Talpa product ID")
    talpa_product_id.admin_order_field = "talpa_product_id"


class OrderRefundLogEntryInline(admin.StackedInline):
    model = OrderRefundLogEntry
    fk_name = "refund"
    extra = 0
    readonly_fields = ("created_at",)


class OrderRefundAdmin(admin.ModelAdmin):
    inlines = (OrderRefundLogEntryInline,)
    date_hierarchy = "created_at"
    autocomplete_fields = ("order",)
    list_display = (
        "id",
        "refund_id",
        "created_at",
        "time_settled",
        "order",
        "customer",
        "status",
        "amount",
    )
    list_filter = ("status",)
    ordering = ("-created_at",)
    search_fields = (
        "refund_id",
        "order__order_number",
        "order__customer__id",
        "order__customer_first_name",
        "order__customer_last_name",
        "order__customer_email",
    )
    readonly_fields = ("time_settled",)

    def time_settled(self, obj):
        entry = (
            obj.log_entries.filter(from_status="pending").order_by("created_at").first()
        )
        return entry.created_at if entry else None

    def customer(self, obj):
        if obj.order.customer_first_name or obj.order.customer_last_name:
            return f"{obj.order.customer_first_name  or ''} {obj.order.customer_last_name or ''}"


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
    autocomplete_fields = ("order",)

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
    list_display = (
        "id",
        "offer_number",
        "customer",
        "name",
        "application",
        "berth",
        "lease",
        "due_date",
        "status",
    )
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
        "offer_number",
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


class OrderLineAdmin(admin.ModelAdmin):
    autocomplete_fields = ("order",)
    readonly_fields = ("talpa_product_id",)

    def talpa_product_id(self, obj):
        return (
            get_talpa_product_id(
                obj.product.id,
                resolve_area(obj.order),
                is_storage_on_ice=obj.product.service
                == ProductServiceType.STORAGE_ON_ICE,
            )
            if hasattr(obj, "product")
            else "-"
        )

    talpa_product_id.short_description = _("Talpa product ID")
    talpa_product_id.admin_order_field = "talpa_product_id"


admin.site.register(WinterStorageProduct, WinterStorageProductAdmin)
admin.site.register(BerthProduct, BerthProductAdmin)
admin.site.register(AdditionalProduct, AdditionalProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLine, OrderLineAdmin)
admin.site.register(OrderLogEntry, OrderLogEntryAdmin)
admin.site.register(OrderRefund, OrderRefundAdmin)
admin.site.register(OrderRefundLogEntry, OrderRefundLogEntryAdmin)
admin.site.register(OrderToken, OrderTokenAdmin)
admin.site.register(BerthSwitchOfferLogEntry, BerthSwitchOfferLogEntryAdmin)
admin.site.register(BerthSwitchOffer, BerthSwitchOfferAdmin)
