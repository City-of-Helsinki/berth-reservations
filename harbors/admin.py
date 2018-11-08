from django.contrib.gis import admin
from parler.admin import TranslatableAdmin

from .models import BoatType, Harbor


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(TranslatableAdmin, admin.OSMGeoAdmin):
    filter_horizontal = ('suitable_boat_types',)


admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Harbor, HarborAdmin)
