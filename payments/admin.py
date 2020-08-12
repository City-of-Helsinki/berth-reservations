from django.contrib import admin
from django.forms import ChoiceField, UUIDField
from django.utils.translation import gettext_lazy as _

from .models import (
    AdditionalProduct,
    BerthPriceGroup,
    BerthProduct,
    Order,
    OrderLine,
    OrderLogEntry,
    WinterStorageProduct,
)
from .utils import currency, percentage


class BerthPriceGroupAdmin(admin.ModelAdmin):
    readonly_fields = ("berth_types",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .order_by("berth_types__width", "name")
            .distinct()
        )

    def berth_types(self, obj):
        return "\n".join(
            [
                str(bt)
                for bt in obj.berth_types.all().order_by(
                    "width", "length", "depth", "mooring_type"
                )
            ]
        )

    berth_types.short_description = _("Berth types")
    berth_types.admin_order_field = "berth_types"


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
    )

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
        return obj.pretax_price if obj.price and obj.tax_percentage else None

    @currency
    def total_price(self, obj):
        return obj.total_price if obj.price and obj.tax_percentage else None

    @currency
    def total_pretax_price(self, obj):
        return obj.total_pretax_price if obj.price and obj.tax_percentage else None

    @percentage
    def total_tax_percentage(self, obj):
        return obj.total_tax_percentage if obj.price and obj.tax_percentage else None

    pretax_price.short_description = _("Pretax price")
    pretax_price.admin_order_field = "pretax_price"

    total_price.short_description = _("Total order price")
    total_price.admin_order_field = "total_price"

    total_pretax_price.short_description = _("Total order pretax price")
    total_pretax_price.admin_order_field = "total_pretax_price"

    total_tax_percentage.short_description = _("Total order tax percentage")
    total_tax_percentage.admin_order_field = "total_tax_percentage"


admin.site.register([WinterStorageProduct, BerthProduct, OrderLine, OrderLogEntry])
admin.site.register(AdditionalProduct, AdditionalProductAdmin)
admin.site.register(BerthPriceGroup, BerthPriceGroupAdmin)
admin.site.register(Order, OrderAdmin)
