import django_filters
import graphene
import graphql_geojson
from django.utils.translation import gettext_lazy as _
from graphene import relay
from graphene_django.fields import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from users.decorators import view_permission_required
from utils.enum import graphene_enum
from utils.schema import CountConnection

from ..enums import BerthMooringType
from ..models import (
    AvailabilityLevel,
    Berth,
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
from .utils import resolve_piers

BerthMooringTypeEnum = graphene_enum(BerthMooringType)


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
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)
    number_of_places = graphene.Int(required=True)
    max_width = graphene.Float()
    max_length = graphene.Float()
    max_depth = graphene.Float()
    price_tier = graphene.Field("payments.schema.PriceTierEnum")

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
        connection_class = CountConnection


class BerthNodeFilterSet(django_filters.FilterSet):
    min_width = django_filters.NumberFilter(
        field_name="berth_type__width", lookup_expr="gte"
    )
    min_length = django_filters.NumberFilter(
        field_name="berth_type__length", lookup_expr="gte"
    )
    is_available = django_filters.BooleanFilter()

    class Meta:
        model = Berth
        fields = ["min_width", "min_length"]


class BerthNode(DjangoObjectType):
    leases = DjangoConnectionField(
        "leases.schema.BerthLeaseNode",
        description="**Requires permissions** to query this field.",
    )
    is_accessible = graphene.Boolean()
    is_available = graphene.Boolean(required=True)
    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)
    depth = graphene.Float(description=_("depth (m)"))
    mooring_type = BerthMooringTypeEnum(required=True)

    class Meta:
        model = Berth
        fields = (
            "id",
            "number",
            "pier",
            "comment",
            "is_active",
            "created_at",
            "modified_at",
        )
        interfaces = (relay.Node,)
        filterset_class = BerthNodeFilterSet
        connection_class = CountConnection

    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    def resolve_leases(self, info, **kwargs):
        return self.leases.all()

    def resolve_width(self, info, **kwargs):
        return self.berth_type.width

    def resolve_length(self, info, **kwargs):
        return self.berth_type.length

    def resolve_depth(self, info, **kwargs):
        return self.berth_type.depth

    def resolve_mooring_type(self, info, **kwargs):
        return self.berth_type.mooring_type


class AbstractMapType:
    url = graphene.String(required=True)

    def resolve_url(self, info, **kwargs):
        return info.context.build_absolute_uri(self.map_file.url)


class HarborMapType(DjangoObjectType, AbstractMapType):
    class Meta:
        model = HarborMap
        fields = (
            "id",
            "url",
        )


class WinterStorageAreaMapType(DjangoObjectType, AbstractMapType):
    class Meta:
        model = WinterStorageAreaMap
        fields = (
            "id",
            "url",
        )


class HarborFilter(django_filters.FilterSet):
    class Meta:
        model = Harbor
        fields = (
            "piers__mooring",
            "piers__electricity",
            "piers__water",
            "piers__waste_collection",
            "piers__gate",
            "piers__lighting",
            "piers__suitable_boat_types",
        )

    max_width = django_filters.NumberFilter()
    max_length = django_filters.NumberFilter()


class HarborNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = Harbor
        geojson_field = "location"
        interfaces = (relay.Node,)
        filterset_class = HarborFilter
        connection_class = CountConnection

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    maps = graphene.List(HarborMapType, required=True)
    max_width = graphene.Float()
    max_length = graphene.Float()
    max_depth = graphene.Float()
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)
    piers = DjangoFilterConnectionField(
        PierNode,
        min_berth_width=graphene.Float(),
        min_berth_length=graphene.Float(),
        for_application=graphene.ID(),
        description="To filter the piers suitable for an application, you can use the `forApplication` argument. "
        "\n\n**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* Filter `forApplication` with a user without enough permissions"
        "\n * Filter `forApplication` combined with either dimension (width, length) filter",
    )

    def resolve_image_file(self, info, **kwargs):
        return self.image_file_url

    def resolve_maps(self, info, **kwargs):
        return self.maps.all()

    def resolve_piers(self, info, **kwargs):
        return resolve_piers(info, **kwargs).filter(harbor_id=self.id)

    def resolve_max_width(self, info, **kwargs):
        return (
            max([pier.max_width or 0 for pier in self.piers.all()], default=0) or None
        )

    def resolve_max_length(self, info, **kwargs):
        return (
            max([pier.max_length or 0 for pier in self.piers.all()], default=0) or None
        )

    def resolve_max_depth(self, info, **kwargs):
        return (
            max([pier.max_depth or 0 for pier in self.piers.all()], default=0) or None
        )

    def resolve_number_of_free_places(self, info, **kwargs):
        return sum([pier.number_of_free_places or 0 for pier in self.piers.all()])

    def resolve_number_of_inactive_places(self, info, **kwargs):
        return sum([pier.number_of_inactive_places or 0 for pier in self.piers.all()])

    def resolve_number_of_places(self, info, **kwargs):
        return sum([pier.number_of_places or 0 for pier in self.piers.all()])


class WinterStoragePlaceNode(DjangoObjectType):
    leases = DjangoConnectionField(
        "leases.schema.WinterStorageLeaseNode",
        description="**Requires permissions** to query this field.",
    )
    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)

    class Meta:
        model = WinterStoragePlace
        fields = (
            "id",
            "number",
            "winter_storage_section",
            "is_active",
            "created_at",
            "modified_at",
        )
        interfaces = (relay.Node,)
        connection_class = CountConnection

    @view_permission_required(
        WinterStorageLease, WinterStorageApplication, CustomerProfile
    )
    def resolve_leases(self, info, **kwargs):
        return self.leases.all()

    def resolve_width(self, info, **kwargs):
        return self.place_type.width

    def resolve_length(self, info, **kwargs):
        return self.place_type.length


class WinterStoragePlaceTypeNode(DjangoObjectType):
    places = DjangoConnectionField(
        WinterStoragePlaceNode,
        description="**Requires permissions** to query this field.",
    )
    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)

    class Meta:
        model = WinterStoragePlaceType
        fields = (
            "id",
            "created_at",
            "modified_at",
        )
        interfaces = (relay.Node,)
        connection_class = CountConnection

    def resolve_places(self, info, **kwargs):
        return self.places.all()


class WinterStorageSectionNode(graphql_geojson.GeoJSONType):
    max_width = graphene.Float()
    max_length = graphene.Float()
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)
    leases = DjangoConnectionField(
        "leases.schema.WinterStorageLeaseNode",
        description="**Requires permissions** to query this field.",
    )

    class Meta:
        model = WinterStorageSection
        filter_fields = [
            "repair_area",
            "electricity",
            "gate",
            "water",
            "summer_storage_for_docking_equipment",
            "summer_storage_for_trailers",
            "summer_storage_for_boats",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)
        connection_class = CountConnection

    @view_permission_required(
        WinterStorageLease, WinterStorageApplication, CustomerProfile
    )
    def resolve_leases(self, info, **kwargs):
        return self.leases.all()


class WinterStorageAreaFilter(django_filters.FilterSet):
    class Meta:
        model = WinterStorageArea
        fields = (
            "sections__repair_area",
            "sections__electricity",
            "sections__water",
            "sections__summer_storage_for_docking_equipment",
            "sections__summer_storage_for_trailers",
            "sections__summer_storage_for_boats",
            "max_length_of_section_spaces",
        )

    max_width = django_filters.NumberFilter()
    max_length = django_filters.NumberFilter()


class WinterStorageAreaNode(graphql_geojson.GeoJSONType):
    class Meta:
        model = WinterStorageArea
        geojson_field = "location"
        interfaces = (relay.Node,)
        exclude = ("harbors_area",)
        filterset_class = WinterStorageAreaFilter
        connection_class = CountConnection

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    maps = graphene.List(WinterStorageAreaMapType, required=True)
    max_width = graphene.Float()
    max_length = graphene.Float()
    product = graphene.Field("payments.schema.WinterStorageProductNode")
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)

    def resolve_image_file(self, info, **kwargs):
        return self.image_file_url

    def resolve_maps(self, info, **kwargs):
        return self.maps.all()

    def resolve_max_width(self, info, **kwargs):
        return (
            max([section.max_width or 0 for section in self.sections.all()], default=0)
            or None
        )

    def resolve_max_length(self, info, **kwargs):
        return (
            max([section.max_length or 0 for section in self.sections.all()], default=0)
            or None
        )

    def resolve_number_of_free_places(self, info, **kwargs):
        return sum(
            [section.number_of_free_places or 0 for section in self.sections.all()]
        )

    def resolve_number_of_inactive_places(self, info, **kwargs):
        return sum(
            [section.number_of_inactive_places or 0 for section in self.sections.all()]
        )

    def resolve_number_of_places(self, info, **kwargs):
        return sum([section.number_of_places or 0 for section in self.sections.all()])
