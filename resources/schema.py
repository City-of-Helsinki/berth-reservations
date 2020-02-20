import django_filters
import graphene
import graphql_geojson
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.db.utils import IntegrityError
from django.utils.translation import get_language, ugettext_lazy as _
from graphene import relay
from graphene_django.fields import DjangoConnectionField, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required, superuser_required
from graphql_relay import from_global_id
from munigeo.models import Municipality

from applications.models import BerthApplication
from berth_reservations.exceptions import VenepaikkaGraphQLError

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


def update_object(obj, data):
    if not data:
        return
    for k, v in data.items():
        setattr(obj, k, v)
    obj.save()


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
        if user.is_authenticated and user.is_superuser:
            application_id = from_global_id(application_global_id)[1]
            try:
                application = BerthApplication.objects.get(pk=application_id)
            except BerthApplication.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

            min_width = application.boat_width
            min_length = application.boat_length

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

    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)
    depth = graphene.Float(description=_("depth (m)"))
    mooring_type = BerthMooringTypeEnum(required=True)


class BerthNodeFilterSet(django_filters.FilterSet):
    min_width = django_filters.NumberFilter(
        field_name="berth_type__width", lookup_expr="gte"
    )
    min_length = django_filters.NumberFilter(
        field_name="berth_type__length", lookup_expr="gte"
    )

    class Meta:
        model = Berth
        fields = ["min_width", "min_length"]


class BerthNode(DjangoObjectType):
    class Meta:
        model = Berth
        fields = ("id", "number", "pier", "berth_type", "comment")
        interfaces = (relay.Node,)
        filterset_class = BerthNodeFilterSet


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
    piers = DjangoFilterConnectionField(
        PierNode,
        min_berth_width=graphene.Float(),
        min_berth_length=graphene.Float(),
        for_application=graphene.ID(),
        description="To filter the piers suitable for an application, you can use the `forApplication` argument. "
        "For this, you must have a user with permissions to access applications. "
        "You cannot use the `Application` filter combined with the dimensions (width, length) one. "
        "If you do, you will get a `VenepaikkaGraphQLError`.",
    )

    def resolve_image_file(self, info, **kwargs):
        if self.image_file:
            return info.context.build_absolute_uri(self.image_file.url)
        else:
            return None

    def resolve_piers(self, info, **kwargs):
        return _resolve_piers(info, **kwargs).filter(harbor_id=self.id)


class WinterStoragePlaceTypeNode(DjangoObjectType):
    class Meta:
        model = WinterStoragePlaceType
        interfaces = (relay.Node,)

    width = graphene.Float(description=_("width (m)"), required=True)
    length = graphene.Float(description=_("length (m)"), required=True)


class WinterStoragePlaceNode(DjangoObjectType):
    class Meta:
        model = WinterStoragePlace
        fields = ("id", "number", "winter_storage_section", "place_type")
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


class CreateBerthMutation(graphene.ClientIDMutation):
    class Input:
        number = graphene.String(required=True)
        comment = graphene.String()
        pier_id = graphene.ID(required=True)
        berth_type_id = graphene.ID(required=True)

    berth = graphene.Field(BerthNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        berth = Berth.objects.create(
            number=input.get("number"),
            comment=input.get("comment", ""),
            pier_id=from_global_id(input.get("pier_id"))[1],
            berth_type_id=from_global_id(input.get("berth_type_id"))[1],
        )
        return CreateBerthMutation(berth=berth)


class UpdateBerthMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        number = graphene.String()
        comment = graphene.String()
        pier_id = graphene.ID()
        berth_type_id = graphene.ID()

    berth = graphene.Field(BerthNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # modify the specific resource
        # GQL IDs have to be translated to Django model UUIDs
        id = from_global_id(input.pop("id"))[1]

        if input.get("pier_id"):
            input["pier_id"] = from_global_id(input.get("pier_id"))[1]

        if input.get("berth_type_id"):
            input["berth_type_id"] = from_global_id(input.get("berth_type_id"))[1]

        try:
            berth = Berth.objects.get(pk=id)
        except Berth.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        update_object(berth, input)

        return UpdateBerthMutation(berth=berth)


class DeleteBerthMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.get("id"))[1]

        try:
            berth = Berth.objects.get(pk=id)
        except Berth.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        berth.delete()

        return DeleteBerthMutation()


class CreateBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        mooring_type = BerthMooringTypeEnum(required=True)
        width = graphene.Float(required=True)
        length = graphene.Float(required=True)
        depth = graphene.Float()

    berth_type = graphene.Field(BerthTypeNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource

        berth_type = BerthType.objects.create(
            mooring_type=input.get("mooring_type"),
            width=input.get("width"),
            length=input.get("length"),
        )
        return CreateBerthTypeMutation(berth_type=berth_type)


class UpdateBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        mooring_type = BerthMooringTypeEnum()
        width = graphene.Float()
        length = graphene.Float()
        depth = graphene.Float()

    berth_type = graphene.Field(BerthTypeNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # modify the specific resource
        # GQL IDs have to be translated to Django model UUIDs
        id = from_global_id(input.pop("id"))[1]

        try:
            berth_type = BerthType.objects.get(pk=id)
        except BerthType.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        update_object(berth_type, input)

        return UpdateBerthTypeMutation(berth_type=berth_type)


class DeleteBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.get("id"))[1]

        try:
            berth_type = BerthType.objects.get(pk=id)
        except BerthType.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        berth_type.delete()

        return DeleteBerthTypeMutation()


class HarborInput(AbstractAreaInput):
    municipality_id = graphene.String()
    image_file = graphene.String()
    availability_level_id = graphene.ID()
    number_of_places = graphene.Int()
    maximum_width = graphene.Int()
    maximum_length = graphene.Int()
    maximum_depth = graphene.Int()
    name = graphene.String()
    street_address = graphene.String()


class CreateHarborMutation(graphene.ClientIDMutation):
    class Input(HarborInput):
        pass

    harbor = graphene.Field(HarborNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        lang = get_language()

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

        harbor = Harbor.objects.language(lang).create(**input)

        return CreateHarborMutation(harbor=harbor)


class UpdateHarborMutation(graphene.ClientIDMutation):
    class Input(HarborInput):
        id = graphene.ID(required=True)

    harbor = graphene.Field(HarborNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.pop("id"))[1]

        lang = get_language()

        try:
            harbor = Harbor.objects.language(lang).get(pk=id)

            availability_level_id = input.pop("availability_level_id", None)
            if availability_level_id:
                input["availability_level"] = AvailabilityLevel.objects.language(
                    lang
                ).get(pk=availability_level_id)

            municipality_id = input.pop("municipality_id", None)
            if municipality_id:
                input["municipality"] = Municipality.objects.get(id=municipality_id)
        except (
            Harbor.DoesNotExist,
            AvailabilityLevel.DoesNotExist,
            Municipality.DoesNotExist,
        ) as e:
            raise VenepaikkaGraphQLError(e)

        update_object(harbor, input)

        return UpdateHarborMutation(harbor=harbor)


class DeleteHarborMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.get("id"))[1]

        try:
            harbor = Harbor.objects.get(pk=id)
        except Harbor.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        harbor.delete()

        return DeleteHarborMutation()


class PierInput(AbstractAreaSectionInput):
    harbor_id = graphene.ID()
    suitable_boat_types = graphene.List(graphene.ID)
    mooring = graphene.Boolean()
    waste_collection = graphene.Boolean()
    lighting = graphene.Boolean()


class CreatePierMutation(graphene.ClientIDMutation):
    class Input(PierInput):
        harbor_id = graphene.ID(required=True)

    pier = graphene.Field(PierNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        suitable_boat_types = input.pop("suitable_boat_types", [])

        harbor_global_id = input.pop("harbor_id", None)
        if harbor_global_id:
            harbor_id = from_global_id(harbor_global_id)[1]
            try:
                input["harbor"] = Harbor.objects.get(pk=harbor_id)
            except Harbor.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

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
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.pop("id"))[1]

        try:
            harbor_global_id = input.pop("harbor_id", None)
            if harbor_global_id:
                harbor_id = from_global_id(harbor_global_id)[1]
                input["harbor"] = Harbor.objects.get(pk=harbor_id)

            pier = Pier.objects.get(pk=id)
        except (Pier.DoesNotExist, Harbor.DoesNotExist,) as e:
            raise VenepaikkaGraphQLError(e)

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
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(input.get("id"))[1]

        try:
            pier = Pier.objects.get(pk=id)
        except Pier.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        pier.delete()

        return DeletePierMutation()


class Query:
    availability_levels = DjangoListField(AvailabilityLevelType)
    boat_types = DjangoListField(BoatTypeType)

    berth_type = relay.Node.Field(BerthTypeNode)
    berth_types = DjangoConnectionField(BerthTypeNode)

    berth = relay.Node.Field(BerthNode)
    berths = DjangoFilterConnectionField(BerthNode)

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
        "For this, you must have a user with permissions to access applications. "
        "You cannot use the `Application` filter combined with the dimensions (width, length) one. "
        "If you do, you will get a `VenepaikkaGraphQLError`.",
    )

    harbor = relay.Node.Field(HarborNode)
    harbor_by_servicemap_id = graphene.Field(
        HarborNode, servicemap_id=graphene.String(required=True)
    )
    harbors = DjangoFilterConnectionField(
        HarborNode, servicemap_ids=graphene.List(graphene.String)
    )

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
    create_berth = CreateBerthMutation.Field()
    delete_berth = DeleteBerthMutation.Field()
    update_berth = UpdateBerthMutation.Field()

    # BerthType
    create_berth_type = CreateBerthTypeMutation.Field()
    delete_berth_type = DeleteBerthTypeMutation.Field()
    update_berth_type = UpdateBerthTypeMutation.Field()

    # Harbors
    create_harbor = CreateHarborMutation.Field()
    delete_harbor = DeleteHarborMutation.Field()
    update_harbor = UpdateHarborMutation.Field()

    # Piers
    create_pier = CreatePierMutation.Field()
    delete_pier = DeletePierMutation.Field()
    update_pier = UpdatePierMutation.Field()
