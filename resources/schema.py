import django_filters
import graphene
import graphql_geojson
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _
from graphene import relay
from graphene_django.fields import DjangoConnectionField, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from munigeo.models import Municipality

from applications.models import BerthApplication, WinterStorageApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from leases.enums import LeaseStatus
from leases.models import BerthLease, WinterStorageLease
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from users.utils import user_has_view_permission
from utils.enum import graphene_enum
from utils.relay import get_node_from_global_id
from utils.schema import CountConnection, update_object
from utils.urls import get_image_file_url

from .enums import BerthMooringType
from .models import (
    AvailabilityLevel,
    Berth,
    BerthType,
    BoatType,
    Harbor,
    HarborMap,
    Pier,
    WinterStorageArea,
    WinterStorageAreaMap,
    WinterStoragePlace,
    WinterStorageSection,
)

BerthMooringTypeEnum = graphene_enum(BerthMooringType)


def _resolve_piers(info, **kwargs):
    min_width = kwargs.get("min_berth_width", 0)
    min_length = kwargs.get("min_berth_length", 0)
    application_global_id = kwargs.get("for_application")

    # Filter out piers with no berths that fit the
    # passed dimensions only if the dimensions were given.
    # Otherwise, return the whole list of piers.
    has_dimensions_filter = any(
        ["min_berth_width" in kwargs, "min_berth_length" in kwargs]
    )

    if has_dimensions_filter and application_global_id:
        raise VenepaikkaGraphQLError(
            _(
                "You cannot filter by dimension (width, length) and application a the same time."
            )
        )

    if application_global_id:
        user = info.context.user
        if (
            user
            and user.is_authenticated
            and user_has_view_permission(user, BerthApplication)
        ):
            application = get_node_from_global_id(
                info, application_global_id, only_type=BerthApplicationNode
            )

            min_width = application.boat_width
            min_length = application.boat_length
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action")
            )

    suitable_berth_types = BerthType.objects.filter(
        width__gte=min_width, length__gte=min_length
    )
    berth_queryset = Berth.objects.select_related("berth_type").filter(
        berth_type__in=suitable_berth_types
    )

    query = Pier.objects.prefetch_related(
        Prefetch("berths", queryset=berth_queryset),
        "suitable_boat_types",
        "harbor__translations",
        "harbor__availability_level__translations",
        "harbor__municipality__translations",
    ).select_related("harbor", "harbor__availability_level", "harbor__municipality")

    if has_dimensions_filter:
        query = query.annotate(
            berth_count=Count(
                "berths",
                filter=Q(berths__berth_type__width__gte=min_width)
                & Q(berths__berth_type__length__gte=min_length),
            )
        ).filter(berth_count__gt=0)

    return query


def delete_inactive_leases(lookup, model_name):
    # Get all the leases related to the resource
    leases = BerthLease.objects.filter(lookup)
    # If there's any active lease, raise an error
    if leases.filter(status=LeaseStatus.PAID).count() > 0:
        raise VenepaikkaGraphQLError(
            _(f"Cannot delete {model_name} because it has some related leases")
        )

    # Delete all the leases associated to the Harbor
    leases.delete()


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
    image_file = graphene.String()
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
        if self.image_file:
            return get_image_file_url(self.image_file)
        else:
            return None

    def resolve_maps(self, info, **kwargs):
        return self.maps.all()

    def resolve_piers(self, info, **kwargs):
        return _resolve_piers(info, **kwargs).filter(harbor_id=self.id)

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
    image_file = graphene.String()
    maps = graphene.List(WinterStorageAreaMapType, required=True)
    max_width = graphene.Float()
    max_length = graphene.Float()
    product = graphene.Field("payments.schema.WinterStorageProductNode")
    number_of_places = graphene.Int(required=True)
    number_of_free_places = graphene.Int(required=True)
    number_of_inactive_places = graphene.Int(required=True)

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return get_image_file_url(self.image_file)
        else:
            return None

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


class AbstractAreaInput:
    servicemap_id = graphene.String()
    zip_code = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    www_url = graphene.String()
    location = graphql_geojson.Geometry()
    image_link = graphene.String()


class AbstractAreaSectionInput:
    identifier = graphene.String()
    location = graphql_geojson.Geometry()
    electricity = graphene.Boolean()
    water = graphene.Boolean()
    gate = graphene.Boolean()


class AbstractBoatPlaceInput:
    is_active = graphene.Boolean()


class BerthInput(AbstractBoatPlaceInput):
    number = graphene.String()
    pier_id = graphene.ID()
    comment = graphene.String()
    is_accessible = graphene.Boolean()
    width = graphene.Float(description=_("width (m)"))
    length = graphene.Float(description=_("length (m)"))
    depth = graphene.Float(description=_("depth (m)"))
    mooring_type = BerthMooringTypeEnum()


class CreateBerthMutation(graphene.ClientIDMutation):
    class Input(BerthInput):
        number = graphene.String(required=True)
        pier_id = graphene.ID(required=True)
        width = graphene.Float(description=_("width (m)"), required=True)
        length = graphene.Float(description=_("length (m)"), required=True)
        mooring_type = BerthMooringTypeEnum(required=True)

    berth = graphene.Field(BerthNode)

    @classmethod
    @add_permission_required(Berth)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        width = input.pop("width", None)
        length = input.pop("length", None)
        depth = input.pop("depth", None)
        mooring_type = input.pop("mooring_type", None)

        berth_type, created = BerthType.objects.get_or_create(
            width=width, length=length, depth=depth, mooring_type=mooring_type
        )
        input["berth_type"] = berth_type

        input["pier"] = get_node_from_global_id(
            info, input.pop("pier_id"), only_type=PierNode, nullable=False,
        )
        berth = Berth.objects.create(**input)
        return CreateBerthMutation(berth=berth)


class UpdateBerthMutation(graphene.ClientIDMutation):
    class Input(BerthInput):
        id = graphene.ID(required=True)

    berth = graphene.Field(BerthNode)

    @classmethod
    @change_permission_required(Berth)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        berth = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthNode, nullable=False,
        )

        width = input.pop("width", None)
        length = input.pop("length", None)
        depth_in_input = "depth" in input
        mooring_type = input.pop("mooring_type", None)
        berth_type = None

        if any([width, length, depth_in_input, mooring_type]):
            old_berth_type = berth.berth_type
            berth_type, created = BerthType.objects.get_or_create(
                width=width or old_berth_type.width,
                length=length or old_berth_type.length,
                # Checking directly if it's in the input keys because it allows null values
                depth=input.pop("depth") if depth_in_input else old_berth_type.depth,
                mooring_type=mooring_type or old_berth_type.mooring_type,
            )

        if berth_type:
            input["berth_type"] = berth_type

        if input.get("pier_id"):
            input["pier"] = get_node_from_global_id(
                info, input.pop("pier_id"), only_type=PierNode, nullable=False,
            )

        update_object(berth, input)

        return UpdateBerthMutation(berth=berth)


class DeleteBerthMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(Berth)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        berth = get_node_from_global_id(
            info, input.get("id"), only_type=BerthNode, nullable=False,
        )

        delete_inactive_leases(Q(berth=berth), "Berth")

        berth.delete()

        return DeleteBerthMutation()


class HarborInput(AbstractAreaInput):
    municipality_id = graphene.String()
    image_file = Upload()
    add_map_files = graphene.List(
        Upload,
        description="List of map files that will be added to the existing ones belonging to the Harbor.",
    )
    availability_level_id = graphene.ID()
    name = graphene.String()
    street_address = graphene.String()


def add_map_files(model, map_files, instance):
    try:
        for map_file in map_files:
            map_instance = model(map_file=map_file)
            instance.maps.add(map_instance, bulk=False)
    except IntegrityError as e:
        raise VenepaikkaGraphQLError(e)


def remove_map_files(model, map_files):
    try:
        for file_id in map_files:
            model.objects.get(pk=file_id).delete()
    except model.DoesNotExist as e:
        raise VenepaikkaGraphQLError(e)


class CreateHarborMutation(graphene.ClientIDMutation):
    class Input(HarborInput):
        pass

    harbor = graphene.Field(HarborNode)

    @classmethod
    @add_permission_required(Harbor)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        availability_level_id = input.pop("availability_level_id", None)
        if availability_level_id:
            try:
                input["availability_level"] = AvailabilityLevel.objects.get(
                    pk=availability_level_id
                )
            except AvailabilityLevel.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

        municipality_id = input.pop("municipality_id", None)
        if municipality_id:
            try:
                input["municipality"] = Municipality.objects.get(id=municipality_id)
            except Municipality.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

        harbor = Harbor.objects.create(**input)
        add_map_files(HarborMap, input.pop("add_map_files", []), harbor)

        return CreateHarborMutation(harbor=harbor)


class UpdateHarborMutation(graphene.ClientIDMutation):
    class Input(HarborInput):
        id = graphene.ID(required=True)
        remove_map_files = graphene.List(
            graphene.ID, description="List of IDs of the maps to be removed."
        )

    harbor = graphene.Field(HarborNode)

    @classmethod
    @change_permission_required(Harbor)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        harbor = get_node_from_global_id(
            info, input.pop("id"), only_type=HarborNode, nullable=False,
        )

        try:
            availability_level_id = input.pop("availability_level_id", None)
            if availability_level_id:
                input["availability_level"] = AvailabilityLevel.objects.get(
                    pk=availability_level_id
                )

            municipality_id = input.pop("municipality_id", None)
            if municipality_id:
                input["municipality"] = Municipality.objects.get(id=municipality_id)
        except (AvailabilityLevel.DoesNotExist, Municipality.DoesNotExist,) as e:
            raise VenepaikkaGraphQLError(e)

        add_map_files(HarborMap, input.pop("add_map_files", []), harbor)
        remove_map_files(HarborMap, input.pop("remove_map_files", []))
        update_object(harbor, input)

        return UpdateHarborMutation(harbor=harbor)


class DeleteHarborMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(Harbor)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        harbor = get_node_from_global_id(
            info, input.pop("id"), only_type=HarborNode, nullable=False,
        )

        delete_inactive_leases(Q(berth__pier__harbor=harbor), "Harbor")

        harbor.delete()

        return DeleteHarborMutation()


class PierInput(AbstractAreaSectionInput):
    harbor_id = graphene.ID()
    suitable_boat_types = graphene.List(graphene.ID)
    mooring = graphene.Boolean()
    waste_collection = graphene.Boolean()
    lighting = graphene.Boolean()
    personal_electricity = graphene.Boolean()


class CreatePierMutation(graphene.ClientIDMutation):
    class Input(PierInput):
        harbor_id = graphene.ID(required=True)

    pier = graphene.Field(PierNode)

    @classmethod
    @add_permission_required(Pier)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        suitable_boat_types = input.pop("suitable_boat_types", [])

        if input.get("harbor_id"):
            harbor = get_node_from_global_id(
                info, input.pop("harbor_id"), only_type=HarborNode, nullable=False,
            )
            input["harbor"] = harbor

        boat_types = set()
        for boat_type_id in suitable_boat_types:
            try:
                boat_type = BoatType.objects.get(pk=boat_type_id)
            except BoatType.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)
            boat_types.add(boat_type)

        try:
            pier = Pier.objects.create(**input)
            pier.suitable_boat_types.set(boat_types)
        except IntegrityError as e:
            raise VenepaikkaGraphQLError(e)

        return CreatePierMutation(pier=pier)


class UpdatePierMutation(graphene.ClientIDMutation):
    class Input(PierInput):
        id = graphene.ID(required=True)

    pier = graphene.Field(PierNode)

    @classmethod
    @change_permission_required(Pier)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        pier = get_node_from_global_id(
            info, input.pop("id"), only_type=PierNode, nullable=False,
        )

        if input.get("harbor_id"):
            harbor = get_node_from_global_id(
                info, input.pop("harbor_id"), only_type=HarborNode, nullable=False,
            )
            input["harbor"] = harbor

        boat_types = set()
        for boat_type_id in input.pop("suitable_boat_types", []):
            try:
                boat_type = BoatType.objects.get(pk=boat_type_id)
            except BoatType.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)
            boat_types.add(boat_type)

        try:
            update_object(pier, input)
            pier.suitable_boat_types.set(boat_types)
        except IntegrityError as e:
            raise VenepaikkaGraphQLError(e)

        return UpdatePierMutation(pier=pier)


class DeletePierMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(Pier)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        pier = get_node_from_global_id(
            info, input.pop("id"), only_type=PierNode, nullable=False,
        )

        delete_inactive_leases(Q(berth__pier=pier), "Pier")

        pier.delete()

        return DeletePierMutation()


class Query:
    availability_levels = DjangoListField(AvailabilityLevelType)
    boat_types = DjangoListField(BoatTypeType)

    berth = relay.Node.Field(BerthNode)
    berths = DjangoFilterConnectionField(
        BerthNode,
        description="**Requires permissions** to query `leases` field. "
        "Otherwise, everything is available",
    )

    pier = relay.Node.Field(PierNode)
    piers = DjangoFilterConnectionField(
        PierNode,
        min_berth_width=graphene.Float(),
        min_berth_length=graphene.Float(),
        for_application=graphene.ID(),
        description="`Piers` allows to filter, among other fields, by `minBerthWidth` and `minBerthLength`.\n\n"
        "This filter is recommended over the filter in `berths`, because it yields better results. "
        "It will only return the `pier`s which contain `berth`s matching the filter, when the other will "
        "return all the available `pier`s with an empty list of `berth`s in case there's no matches.\n\n"
        "If you use both filters in the same query, you might get some empty `berth` results where both "
        "queries overlap.\n\n"
        "To filter the piers suitable for an application, you can use the `forApplication` argument. "
        "**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* Filter `forApplication` with a user without enough permissions"
        "\n * Filter `forApplication` combined with either dimension (width, length) filter",
    )

    harbor = relay.Node.Field(HarborNode)
    harbor_by_servicemap_id = graphene.Field(
        HarborNode, servicemap_id=graphene.String(required=True)
    )
    harbors = DjangoFilterConnectionField(
        HarborNode, servicemap_ids=graphene.List(graphene.String)
    )

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
        return _resolve_piers(info, **kwargs)

    def resolve_harbor_by_servicemap_id(self, info, **kwargs):
        return Harbor.objects.filter(servicemap_id=kwargs.get("servicemap_id")).first()

    def resolve_harbors(self, info, **kwargs):
        # TODO: optimize this further
        # currently, still results in too many DB queries
        # although, django-graphene might introduce fixes for this
        # so, check the state of this against a newer version later

        servicemap_ids = kwargs.get("servicemap_ids", None)
        qs = (
            Harbor.objects.filter(servicemap_id__in=servicemap_ids)
            if servicemap_ids
            else Harbor.objects.all()
        )
        return qs.prefetch_related(
            "translations",
            Prefetch(
                "piers",
                queryset=Pier.objects.prefetch_related(
                    Prefetch("berths", queryset=Berth.objects.all())
                ),
            ),
            "piers__suitable_boat_types",
        ).select_related("availability_level", "municipality")

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


class Mutation:
    # Berths
    create_berth = CreateBerthMutation.Field(
        description="Creates a `Berth` object."
        "\n\n**Requires permissions** to create resources."
        "\n\nIt can receive either a `BerthType` ID or dimensions and `BerthMooringType`. "
        "If dimensions are passed, it will try to find an existing `BerthType` that fits. "
        "Otherwise, it will create a new `BerthType`."
        "\n\nErrors:"
        "\n* Both BerthType ID and BerthType dimensions are passed"
        "\n* BerthType dimensions or BerthMooringType are missing"
    )
    delete_berth = DeleteBerthMutation.Field(
        description="Deletes a `Berth` object."
        "\n\n**Requires permissions** to remove resources."
    )
    update_berth = UpdateBerthMutation.Field(
        description="Updates a `Berth` object."
        "\n\n**Requires permissions** to edit resources."
        "\n\nIt can receive either a `BerthType` ID or dimensions and `BerthMooringType`. "
        "If dimensions are passed, it will try to find an existing `BerthType` that fits. "
        "Otherwise, it will create a new `BerthType`."
        "\n\nErrors:"
        "\n* Both BerthType ID and BerthType dimensions are passed"
        "\n* BerthType dimensions or BerthMooringType are missing"
    )

    # Harbors
    create_harbor = CreateHarborMutation.Field(
        description="The `imageFile` field takes an image as input. "
        "To provide the file, you have to perform the request with a client "
        "that conforms to the [GraphQL Multipart Request Spec]"
        "(https://github.com/jaydenseric/graphql-multipart-request-spec)."
    )
    delete_harbor = DeleteHarborMutation.Field()
    update_harbor = UpdateHarborMutation.Field(
        description="The `imageFile` field takes an image as input. "
        "To provide the file, you have to perform the request with a client "
        "that conforms to the [GraphQL Multipart Request Spec]"
        "(https://github.com/jaydenseric/graphql-multipart-request-spec)."
    )

    # Piers
    create_pier = CreatePierMutation.Field()
    delete_pier = DeletePierMutation.Field()
    update_pier = UpdatePierMutation.Field()
