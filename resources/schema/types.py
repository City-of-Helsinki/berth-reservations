import django_filters
import graphene
import graphql_geojson
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from graphene import relay
from graphene_django.fields import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from payments.models import BerthSwitchOffer
from users.decorators import view_permission_required
from utils.enum import graphene_enum
from utils.schema import CountConnection

from ..enums import BerthMooringType
from ..models import (
    AvailabilityLevel,
    Berth,
    BoatType,
    Harbor,
    Pier,
    WinterStorageArea,
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
    suitable_boat_types = graphene.NonNull(
        graphene.List(graphene.NonNull("resources.schema.BoatTypeType"))
    )
    berths = DjangoConnectionField(
        "resources.schema.BerthNode", is_available=graphene.Boolean(), required=True
    )

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
            "harbor",
        ]
        geojson_field = "location"
        interfaces = (relay.Node,)
        connection_class = CountConnection

    def resolve_berths(self, info, **kwargs):
        filters = Q()
        if "is_available" in kwargs:
            filters &= Q(is_available=kwargs.get("is_available"))

        return info.context.berth_loader.load_many(
            keys=self.berths.filter(filters).values_list("id", flat=True)
        )

    def resolve_suitable_boat_types(self, info, **kwargs):
        return info.context.suitable_boat_type_loader.load_many(
            keys=self.suitable_boat_types.values_list("id", flat=True)
        )


class BerthNode(DjangoObjectType):
    leases = DjangoConnectionField(
        "leases.schema.BerthLeaseNode",
        description="**Requires permissions** to query this field.",
    )
    prev_season_lease = graphene.Field(
        "leases.schema.BerthLeaseNode",
        description="The last lease from the previous season. **Requires permissions** to query this field.",
    )
    pending_switch_offer = graphene.Field(
        "payments.schema.BerthSwitchOfferNode",
        description="""The pending berth switch offer for this berth.
        The pending means the latest berth switch offer which has the `status=OFFERED` and
        the due date is in future (`due_date__gte=date.today()`)
        """,
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
            "is_invoiceable",
        )
        interfaces = (relay.Node,)
        connection_class = CountConnection

    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    def resolve_leases(self, info, **kwargs):
        return info.context.leases_for_berth_loader.load(self.id)

    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    def resolve_prev_season_lease(self, info, **kwargs):
        try:
            return self.leases.filter_prev_season_leases().latest("end_date")
        except BerthLease.DoesNotExist:
            return None

    @view_permission_required(BerthSwitchOffer, BerthApplication, CustomerProfile)
    def resolve_pending_switch_offer(self, info, **kwargs):
        return info.context.offered_switch_offer_for_berth_loader.load(self.id)

    def resolve_pier(self, info, **kwargs):
        return info.context.pier_loader.load(self.pier_id)

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

    order_by = django_filters.OrderingFilter(
        fields=(("translations__name", "name"),),
        label="Supports only `name` and `-name`, defaults to `name`.",
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
    max_width = graphene.Float()
    max_length = graphene.Float()
    max_depth = graphene.Float()
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
    # Annotated fields depending on the Piers on the harbor
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)
    mooring = graphene.Boolean(required=True)
    electricity = graphene.Boolean(required=True)
    water = graphene.Boolean(required=True)
    waste_collection = graphene.Boolean(required=True)
    gate = graphene.Boolean(required=True)
    lighting = graphene.Boolean(required=True)
    suitable_boat_types = graphene.List("resources.schema.BoatTypeType", required=True)

    def resolve_image_file(self, info, **kwargs):
        return self.image_file_url

    def resolve_piers(self, info, **kwargs):
        return resolve_piers(info, **kwargs).filter(harbor_id=self.id)

    def resolve_max_width(self, info, **kwargs):
        return self.max_width or 0

    def resolve_max_length(self, info, **kwargs):
        return self.max_length or 0

    def resolve_max_depth(self, info, **kwargs):
        return self.max_depth or 0

    def resolve_number_of_free_places(self, info, **kwargs):
        return self.number_of_free_places or 0

    def resolve_number_of_inactive_places(self, info, **kwargs):
        return self.number_of_inactive_places or 0

    def resolve_number_of_places(self, info, **kwargs):
        return self.number_of_places or 0

    def resolve_suitable_boat_types(self, info, **kwargs):
        type_ids = (
            self.piers.order_by("suitable_boat_types__id")
            .distinct("suitable_boat_types__id")
            .values_list("suitable_boat_types", flat=True)
        )
        filtered_ids = list(filter(None, type_ids))
        return info.context.suitable_boat_type_loader.load_many(keys=filtered_ids)


class WinterStoragePlaceNode(DjangoObjectType):
    leases = DjangoConnectionField(
        "leases.schema.WinterStorageLeaseNode",
        description="**Requires permissions** to query this field.",
    )
    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)

    is_available = graphene.Boolean(required=True)

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
        filterset_class = WinterStorageAreaFilter
        connection_class = CountConnection

    name = graphene.String()
    street_address = graphene.String()
    municipality = graphene.String()
    max_width = graphene.Float()
    max_length = graphene.Float()
    product = graphene.Field("payments.schema.WinterStorageProductNode")
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)
    electricity = graphene.Boolean(required=True)
    water = graphene.Boolean(required=True)
    gate = graphene.Boolean(required=True)
    summer_storage_for_docking_equipment = graphene.Boolean(required=True)
    summer_storage_for_trailers = graphene.Boolean(required=True)
    summer_storage_for_boats = graphene.Boolean(required=True)

    def resolve_image_file(self, info, **kwargs):
        return self.image_file_url

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
