import graphene
import graphql_geojson
from django.db.models import Prefetch
from graphene import relay
from graphene_django.fields import DjangoConnectionField, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from .enums import BerthMooringType
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

BerthMooringTypeEnum = graphene.Enum.from_enum(
    BerthMooringType, description=lambda e: e.label if e else ""
)


class AvailabilityLevelType(DjangoObjectType):
    class Meta:
        model = AvailabilityLevel
        exclude = ("harbors", "winter_storage_areas")

    title = graphene.String()
    description = graphene.String()


class BoatTypeType(DjangoObjectType):
    class Meta:
        model = BoatType
        exclude = ("piers", "boats")

    name = graphene.String()


class PierNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = Pier
        filter_fields = [
            "mooring",
            "electricity",
            "water",
            "waste_collection",
            "gate",
            "lighting",
            "suitable_boat_types",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)


class BerthTypeNode(DjangoObjectType):
    class Meta:
        model = BerthType
        interfaces = (relay.Node,)

    mooring_type = BerthMooringTypeEnum(required=True)


class BerthNode(DjangoObjectType):
    class Meta:
        model = Berth
        interfaces = (relay.Node,)


class HarborNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = Harbor
        filter_fields = [
            "piers__mooring",
            "piers__electricity",
            "piers__water",
            "piers__waste_collection",
            "piers__gate",
            "piers__lighting",
            "piers__suitable_boat_types",
            "maximum_width",
            "maximum_length",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    image_file = graphene.String()

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return info.context.build_absolute_uri(self.image_file.url)
        else:
            return None


class WinterStoragePlaceTypeNode(DjangoObjectType):
    class Meta:
        model = WinterStoragePlaceType
        interfaces = (relay.Node,)


class WinterStoragePlaceNode(DjangoObjectType):
    class Meta:
        model = WinterStoragePlace
        interfaces = (relay.Node,)


class WinterStorageSectionNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = WinterStorageSection
        filter_fields = [
            "repair_area",
            "electricity",
            "water",
            "summer_storage_for_docking_equipment",
            "summer_storage_for_trailers",
            "summer_storage_for_boats",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)


class WinterStorageAreaNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = WinterStorageArea
        filter_fields = [
            "sections__repair_area",
            "sections__electricity",
            "sections__water",
            "sections__summer_storage_for_docking_equipment",
            "sections__summer_storage_for_trailers",
            "sections__summer_storage_for_boats",
            "max_width",
            "max_length",
            "max_length_of_section_spaces",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    image_file = graphene.String()

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return info.context.build_absolute_uri(self.image_file.url)
        else:
            return None


class Query:
    availability_levels = DjangoListField(AvailabilityLevelType)
    boat_types = DjangoListField(BoatTypeType)

    berth_type = relay.Node.Field(BerthTypeNode)
    berth_types = DjangoConnectionField(BerthTypeNode)

    berth = relay.Node.Field(BerthNode)
    berths = DjangoConnectionField(BerthNode)

    pier = relay.Node.Field(PierNode)
    piers = DjangoFilterConnectionField(PierNode)

    harbor = relay.Node.Field(HarborNode)
    harbors = DjangoFilterConnectionField(HarborNode)

    winter_storage_place_type = relay.Node.Field(WinterStoragePlaceTypeNode)
    winter_storage_place_types = DjangoConnectionField(WinterStoragePlaceTypeNode)

    winter_storage_place = relay.Node.Field(WinterStoragePlaceNode)
    winter_storage_places = DjangoConnectionField(WinterStoragePlaceNode)

    winter_storage_section = relay.Node.Field(WinterStorageSectionNode)
    winter_storage_sections = DjangoFilterConnectionField(WinterStorageSectionNode)

    winter_storage_area = relay.Node.Field(WinterStorageAreaNode)
    winter_storage_areas = DjangoFilterConnectionField(WinterStorageAreaNode)

    def resolve_availability_levels(self, info, **kwargs):
        return AvailabilityLevel.objects.all()

    def resolve_boat_types(self, info, **kwargs):
        return BoatType.objects.all()

    def resolve_berths(self, info, **kwargs):
        return Berth.objects.prefetch_related(
            "pier__suitable_boat_types",
            "pier__harbor__translations",
            "pier__harbor__availability_level__translations",
            "pier__harbor__municipality__translations",
        ).select_related(
            "pier",
            "pier__harbor",
            "pier__harbor__availability_level",
            "pier__harbor__municipality",
        )

    def resolve_piers(self, info, **kwargs):
        return Pier.objects.prefetch_related(
            "berths",
            "suitable_boat_types",
            "harbor__translations",
            "harbor__availability_level__translations",
            "harbor__municipality__translations",
        ).select_related("harbor", "harbor__availability_level", "harbor__municipality")

    def resolve_harbors(self, info, **kwargs):
        # TODO: optimize this further
        # currently, still results in too many DB queries
        # although, django-graphene might introduce fixes for this
        # so, check the state of this against a newer version later

        return (
            Harbor.objects.all()
            .prefetch_related(
                "translations",
                Prefetch(
                    "piers",
                    queryset=Pier.objects.prefetch_related(
                        Prefetch("berths", queryset=Berth.objects.all())
                    ),
                ),
                "piers__suitable_boat_types",
            )
            .select_related("availability_level", "municipality")
        )

    def resolve_winter_storage_places(self, info, **kwargs):
        return WinterStoragePlace.objects.prefetch_related(
            "winter_storage_section__area__translations",
            "winter_storage_section__area__availability_level__translations",
            "winter_storage_section__area__municipality__translations",
        ).select_related(
            "winter_storage_section",
            "winter_storage_section__area",
            "winter_storage_section__area__availability_level",
            "winter_storage_section__area__municipality",
        )

    def resolve_winter_storage_sections(self, info, **kwargs):
        return WinterStorageSection.objects.prefetch_related(
            "places",
            "area__translations",
            "area__availability_level__translations",
            "area__municipality__translations",
        ).select_related("area", "area__availability_level", "area__municipality")

    def resolve_winter_storage_areas(self, info, **kwargs):
        # TODO: optimize this further
        # currently, still results in too many DB queries
        # although, django-graphene might introduce fixes for this
        # so, check the state of this against a newer version later

        return WinterStorageArea.objects.prefetch_related(
            "translations",
            Prefetch(
                "sections",
                queryset=WinterStorageSection.objects.prefetch_related(
                    Prefetch("places", queryset=WinterStoragePlace.objects.all())
                ),
            ),
        ).select_related("availability_level", "municipality")
