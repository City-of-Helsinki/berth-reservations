from django.contrib.gis import admin
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from .models import (
    AvailabilityLevel,
    Berth,
    BerthType,
    BoatType,
    Harbor,
    Pier,
    WinterStorageArea,
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
        return super().get_queryset(request).translated(language_code, "fi")


class AvailabilityLevelAdmin(TranslatableAdmin):
    pass


class BerthAdmin(admin.ModelAdmin):
    readonly_fields = ("is_available",)
    list_display = (
        "id",
        "number",
        "harbor",
        "pier_identifier",
        "is_active",
        "is_available",
        "berth_width",
        "berth_length",
    )
    search_fields = (
        "number",
        "id",
        "pier__id",
        "pier__identifier",
        "pier__harbor__translations__name",
        "pier__harbor__id",
    )
    list_filter = ("is_active",)

    def is_available(self, obj):
        return obj.is_available

    def harbor(self, obj):
        return obj.pier.harbor

    def pier_identifier(self, obj):
        return obj.pier.identifier

    def berth_width(self, obj):
        return obj.berth_type.width

    def berth_length(self, obj):
        return obj.berth_type.length

    is_available.boolean = True


class BoatTypeAdmin(TranslatableAdmin):
    pass


class HarborAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    list_display = (
        "id",
        "name",
        "servicemap_id",
    )
    ordering = ("translations__name",)
    readonly_fields = (
        "number_of_places",
        "max_width",
        "max_length",
        "max_depth",
    )
    search_fields = (
        "id",
        "translations__name",
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
    list_display = (
        "id",
        "harbor",
        "identifier",
        "number_of_places",
        "number_of_free_places",
        "number_of_inactive_places",
        "price_tier",
    )
    search_fields = (
        "id",
        "identifier",
        "harbor__translations__name",
        "harbor__id",
    )
    filter_horizontal = ("suitable_boat_types",)
    list_filter = ("price_tier",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "harbor":
            kwargs["queryset"] = Harbor.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def number_of_places(self, obj):
        return obj.number_of_places

    def number_of_free_places(self, obj):
        return obj.number_of_free_places

    def number_of_inactive_places(self, obj):
        return obj.number_of_inactive_places


class WinterStorageAreaAdmin(CustomTranslatableAdmin, admin.OSMGeoAdmin):
    list_display = (
        "id",
        "name",
        "servicemap_id",
        "estimated_number_of_unmarked_spaces",
        "estimated_number_of_section_spaces",
    )
    ordering = ("translations__name",)
    readonly_fields = (
        "max_width",
        "max_length",
    )
    search_fields = ("id",)

    def max_width(self, obj):
        return obj.max_width

    max_width.short_description = _("Maximum allowed width")
    max_width.admin_order_field = "max_width"

    def max_length(self, obj):
        return obj.max_length

    max_length.short_description = _("Maximum allowed length")
    max_length.admin_order_field = "max_length"


class WinterStorageSectionAdmin(admin.OSMGeoAdmin):
    list_display = (
        "id",
        "area",
        "identifier",
        "number_of_places",
        "number_of_free_places",
        "number_of_inactive_places",
    )
    search_fields = (
        "id",
        "identifier",
        "area__translations__name",
        "area__id",
    )

    def number_of_places(self, obj):
        return obj.number_of_places

    def number_of_free_places(self, obj):
        return obj.number_of_free_places

    def number_of_inactive_places(self, obj):
        return obj.number_of_inactive_places

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "area":
            kwargs["queryset"] = WinterStorageArea.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WinterStoragePlaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "number",
        "area",
        "section_identifier",
        "is_active",
        "is_available",
    )
    search_fields = (
        "id",
        "number",
        "winter_storage_section__area__translations__name",
        "winter_storage_section__area__id",
        "winter_storage_section__identifier",
        "winter_storage_section__area__translations__name",
        "winter_storage_section__area__id",
    )
    list_filter = ("is_active",)
    readonly_fields = ("is_available",)

    def is_available(self, obj):
        return obj.is_available

    def area(self, obj):
        return obj.winter_storage_section.area

    def section_identifier(self, obj):
        return obj.winter_storage_section.identifier

    is_available.boolean = True


admin.site.register(AvailabilityLevel, AvailabilityLevelAdmin)
admin.site.register(BoatType, BoatTypeAdmin)
admin.site.register(Berth, BerthAdmin)
admin.site.register(BerthType)
admin.site.register(Harbor, HarborAdmin)
admin.site.register(Pier, PierAdmin)
admin.site.register(WinterStorageArea, WinterStorageAreaAdmin)
admin.site.register(WinterStoragePlaceType)
admin.site.register(WinterStorageSection, WinterStorageSectionAdmin)
admin.site.register(WinterStoragePlace, WinterStoragePlaceAdmin)
