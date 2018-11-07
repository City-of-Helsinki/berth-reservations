from django.contrib.gis import admin
from parler.admin import TranslatableAdmin

from .models import BoatType, Harbor


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(TranslatableAdmin, admin.OSMGeoAdmin):
    pass


admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Harbor, HarborAdmin)
