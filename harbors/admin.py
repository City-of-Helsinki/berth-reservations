from django.contrib.gis import admin
from parler.admin import TranslatableAdmin

from .models import AvailabilityLevel, BoatType, Harbor


class AvailabilityLevelAdmin(TranslatableAdmin):
    pass


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(TranslatableAdmin, admin.OSMGeoAdmin):
    filter_horizontal = ("suitable_boat_types",)


admin.site.register(AvailabilityLevel, AvailabilityLevelAdmin)
admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Harbor, HarborAdmin)
