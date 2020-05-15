from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from payments.models import (
    AdditionalProduct,
    BerthPriceGroup,
    BerthProduct,
    WinterStorageProduct,
)


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
    readonly_fields = ("product_type",)

    def product_type(self, obj):
        return obj.product_type

    product_type.short_description = _("Product type")
    product_type.admin_order_field = "product_type"


admin.site.register([WinterStorageProduct, BerthProduct])
admin.site.register(AdditionalProduct, AdditionalProductAdmin)
admin.site.register(BerthPriceGroup, BerthPriceGroupAdmin)
