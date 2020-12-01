from django.contrib import admin
from django.forms import ChoiceField, UUIDField
from django.utils.translation import gettext_lazy as _

from .enums import LeaseOrderType
from .models import (
    AdditionalProduct,
    BerthProduct,
    Order,
    OrderLine,
    OrderLogEntry,
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


class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderLineInline,)
    exclude = ("_product_content_type", "_lease_content_type")
    readonly_fields = (
        "pretax_price",
        "total_pretax_price",
        "total_tax_percentage",
        "total_price",
        "order_number",
        "lease_order_type",
        "order_type",
    )
    list_display = (
        "id",
        "created_at",
        "order_number",
        "total_price",
        "status",
        "customer",
        "lease",
        "product",
        "lease_order_type",
        "order_type",
    )
    list_filter = ("status", "order_type")
    search_fields = ("order_number", "customer__id")

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

            return ChoiceField(choices=choices, label=db_field.verbose_name.title())
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

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"

    total_price.short_description = _("Total order price")
    total_price.admin_order_field = "total_price"

    total_pretax_price.short_description = _("Total order pretax price")
    total_pretax_price.admin_order_field = "total_pretax_price"

    total_tax_percentage.short_description = _("Total order tax percentage")
    total_tax_percentage.admin_order_field = "total_tax_percentage"


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


admin.site.register([WinterStorageProduct, OrderLine, OrderLogEntry])
admin.site.register(BerthProduct, BerthProductAdmin)
admin.site.register(AdditionalProduct, AdditionalProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderToken, OrderTokenAdmin)
