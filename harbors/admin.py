from django.contrib.gis import admin
from parler.admin import TranslatableAdmin

from .models import AvailabilityLevel, BoatType, Harbor, WinterStorageArea


class AvailabilityLevelAdmin(TranslatableAdmin):
    pass


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(TranslatableAdmin, admin.OSMGeoAdmin):
    list_display = ("id", "__str__", "resources_harbor", "piers")
    filter_horizontal = ("suitable_boat_types",)

    def piers(self, obj):
        return ", ".join([str(pier) for pier in obj.resources_pier.all()])


class WinterStorageAreaAdmin(TranslatableAdmin, admin.OSMGeoAdmin):
    pass


admin.site.register(AvailabilityLevel, AvailabilityLevelAdmin)
admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Harbor, HarborAdmin)
admin.site.register(WinterStorageArea, WinterStorageAreaAdmin)
