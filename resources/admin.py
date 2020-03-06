from django.contrib.gis import admin
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


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    list_display = ("name",)
    ordering = ("translations__name",)


class PierAdmin(admin.OSMGeoAdmin):
    filter_horizontal = ("suitable_boat_types",)


class WinterStorageAreaAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    ordering = ("translations__name",)


class WinterStorageSectionAdmin(admin.OSMGeoAdmin):
    pass


admin.site.register(AvailabilityLevel, AvailabilityLevelAdmin)
admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Berth)
admin.site.register(BerthType)
admin.site.register(Harbor, HarborAdmin)
admin.site.register(HarborMap)
admin.site.register(Pier, PierAdmin)
admin.site.register(WinterStorageArea, WinterStorageAreaAdmin)
admin.site.register(WinterStorageAreaMap)
admin.site.register(WinterStoragePlace)
admin.site.register(WinterStoragePlaceType)
admin.site.register(WinterStorageSection, WinterStorageSectionAdmin)
