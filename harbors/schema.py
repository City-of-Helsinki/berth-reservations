import graphene
import graphql_geojson
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from .models import AvailabilityLevel, BoatType, Harbor


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

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()


class Query:
    availability_levels = graphene.List(AvailabilityLevelType)
    boat_types = graphene.List(BoatTypeType)
    harbor = relay.Node.Field(HarborType)
    harbors = DjangoFilterConnectionField(HarborType)

    def resolve_availability_levels(self, info, **kwargs):
        return AvailabilityLevel.objects.all()

    def resolve_boat_types(self, info, **kwargs):
        return BoatType.objects.all()

    def resolve_harbors(self, info, **kwargs):
        return Harbor.objects.all()
