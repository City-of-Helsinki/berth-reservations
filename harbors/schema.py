import graphene
import graphql_geojson
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from .models import AvailabilityLevel, BoatType, Harbor, WinterStorageArea


class AvailabilityLevelType(DjangoObjectType):
    class Meta:
        model = AvailabilityLevel

    title = graphene.String()
    description = graphene.String()


class BoatTypeType(DjangoObjectType):
    class Meta:
        model = BoatType

    name = graphene.String()


class HarborType(graphql_geojson.GeoJSONType):
    class Meta:
        model = Harbor
        filter_fields = [
            "mooring",
            "electricity",
            "water",
            "waste_collection",
            "gate",
            "lighting",
            "suitable_boat_types",
            "maximum_width",
            "maximum_length",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)
        fields = ("location",)

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    image_file = graphene.String()
    servicemap_id = graphene.String()
    zip_code = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    www_url = graphene.String()
    image_link = graphene.String()
    mooring = graphene.Boolean()
    electricity = graphene.Boolean()
    water = graphene.Boolean()
    waste_collection = graphene.Boolean()
    gate = graphene.Boolean()
    lighting = graphene.Boolean()
    suitable_boat_types = graphene.List(BoatTypeType)
    availability_level = graphene.Field(AvailabilityLevelType)
    maximum_width = graphene.Int()
    maximum_length = graphene.Int()
    maximum_depth = graphene.Int()
    number_of_places = graphene.Int()

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return info.context.build_absolute_uri(self.image_file.url)
        else:
            return None

    def resolve_suitable_boat_types(self, info):
        return self.suitable_boat_types.all()


class WinterStorageAreaType(graphql_geojson.GeoJSONType):
    class Meta:
        model = WinterStorageArea
        filter_fields = [
            "repair_area",
            "electricity",
            "water",
            "summer_storage_for_docking_equipment",
            "summer_storage_for_trailers",
            "summer_storage_for_boats",
            "max_width",
            "max_length",
            "max_length_of_section_spaces",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)
        fields = ("location",)

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    image_file = graphene.String()
    servicemap_id = graphene.String()
    zip_code = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    www_url = graphene.String()
    image_link = graphene.String()
    repair_area = graphene.Boolean()
    electricity = graphene.Boolean()
    water = graphene.Boolean()
    gate = graphene.Boolean()
    summer_storage_for_docking_equipment = graphene.Boolean()
    summer_storage_for_trailers = graphene.Boolean()
    summer_storage_for_boats = graphene.Boolean()
    max_length_of_section_spaces = graphene.Int()
    number_of_section_spaces = graphene.Int()
    number_of_unmarked_spaces = graphene.Int()

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return info.context.build_absolute_uri(self.image_file.url)
        else:
            return None


class Query:
    availability_levels = graphene.List(AvailabilityLevelType)
    boat_types = graphene.List(BoatTypeType)
    harbor = relay.Node.Field(HarborType)
    harbors = DjangoFilterConnectionField(HarborType)
    winter_storage_area = relay.Node.Field(WinterStorageAreaType)
    winter_storage_areas = DjangoFilterConnectionField(WinterStorageAreaType)

    def resolve_availability_levels(self, info, **kwargs):
        return AvailabilityLevel.objects.all()

    def resolve_boat_types(self, info, **kwargs):
        return BoatType.objects.all()

    def resolve_harbors(self, info, **kwargs):
        return Harbor.objects.filter(disabled=False)

    def resolve_winter_storage_areas(self, info, **kwargs):
        return WinterStorageArea.objects.filter(disabled=False)
