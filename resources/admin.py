from django.contrib.gis import admin
from django.utils.translation import ugettext_lazy as _
from parler.admin import TranslatableAdmin

from .models import (
    AvailabilityLevel,
    Berth,
    BerthType,
    BoatType,
    Harbor,
    HarborMap,
    Pier,
    WinterStorageArea,
    WinterStorageAreaMap,
    WinterStoragePlace,
    WinterStoragePlaceType,
    WinterStorageSection,
)


class CustomTranslatableAdmin(TranslatableAdmin):
    """
    This admin class prefetches translations for the requests' language.
    """

    def get_queryset(self, request):
        language_code = self.get_queryset_language(request)
        return super().get_queryset(request).translated(language_code)


class AvailabilityLevelAdmin(TranslatableAdmin):
    pass


class BerthAdmin(admin.ModelAdmin):
    readonly_fields = ("is_available",)

    def is_available(self, obj):
        return obj.is_available

    is_available.short_description = _("Berth available")
    is_available.admin_order_field = "is_available"


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    ordering = ("translations__name",)
    readonly_fields = (
        "number_of_places",
        "max_width",
        "max_length",
        "max_depth",
    )

    def number_of_places(self, obj):
        return obj.number_of_places

    number_of_places.short_description = _("Number of places")
    number_of_places.admin_order_field = "number_of_places"

    def max_width(self, obj):
        return obj.max_width

    max_width.short_description = _("Maximum allowed width")
    max_width.admin_order_field = "max_width"

    def max_length(self, obj):
        return obj.max_length

    max_length.short_description = _("Maximum allowed length")
    max_length.admin_order_field = "max_length"

    def max_depth(self, obj):
        return obj.max_depth

    max_depth.short_description = _("Maximum allowed depth")
    max_depth.admin_order_field = "max_depth"


class PierAdmin(admin.OSMGeoAdmin):
    filter_horizontal = ("suitable_boat_types",)


class WinterStorageAreaAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    ordering = ("translations__name",)
    readonly_fields = (
        "number_of_marked_places",
        "max_width",
        "max_length",
    )

    def number_of_marked_places(self, obj):
        return obj.number_of_marked_places

    number_of_marked_places.short_description = _("Number of marked places")
    number_of_marked_places.admin_order_field = "number_of_marked_places"

    def max_width(self, obj):
        return obj.max_width

    max_width.short_description = _("Maximum allowed width")
    max_width.admin_order_field = "max_width"

    def max_length(self, obj):
        return obj.max_length

    max_length.short_description = _("Maximum allowed length")
    max_length.admin_order_field = "max_length"


class WinterStorageSectionAdmin(admin.OSMGeoAdmin):
    pass


admin.site.register(AvailabilityLevel, AvailabilityLevelAdmin)
admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Berth, BerthAdmin)
admin.site.register(BerthType)
admin.site.register(Harbor, HarborAdmin)
admin.site.register(HarborMap)
admin.site.register(Pier, PierAdmin)
admin.site.register(WinterStorageArea, WinterStorageAreaAdmin)
admin.site.register(WinterStorageAreaMap)
admin.site.register(WinterStoragePlace)
admin.site.register(WinterStoragePlaceType)
admin.site.register(WinterStorageSection, WinterStorageSectionAdmin)
