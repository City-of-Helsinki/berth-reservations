import graphene
import graphql_geojson
from django.db import transaction
from django.db.models import Prefetch
from django.db.utils import IntegrityError
from django.utils.translation import get_language
from graphene import relay
from graphene_django.fields import DjangoConnectionField, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required, superuser_required
from graphql_relay import from_global_id
from munigeo.models import Municipality

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
    def mutate_and_get_payload(cls, root, info, **kwargs):
        berth = Berth.objects.create(
            number=kwargs.get("number"),
            comment=kwargs.get("comment", ""),
            pier_id=from_global_id(kwargs.get("pier_id"))[1],
            berth_type_id=from_global_id(kwargs.get("berth_type_id"))[1],
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
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # modify the specific resource
        # GQL IDs have to be translated to Django model UUIDs
        id = from_global_id(kwargs.pop("id"))[1]

        if kwargs.get("pier_id"):
            kwargs["pier_id"] = from_global_id(kwargs.get("pier_id"))[1]

        if kwargs.get("berth_type_id"):
            kwargs["berth_type_id"] = from_global_id(kwargs.get("berth_type_id"))[1]

        try:
            berth = Berth.objects.get(pk=id)
        except Berth.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        update_object(berth, kwargs)

        return UpdateBerthMutation(berth=berth)


class DeleteBerthMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(kwargs.get("id"))[1]

        try:
            berth = Berth.objects.get(pk=id)
        except Berth.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        berth.delete()

        return DeleteBerthMutation()


class CreateBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        mooring_type = BerthMooringTypeEnum(required=True)
        width = graphene.Int(required=True)
        length = graphene.Int(required=True)

    berth_type = graphene.Field(BerthTypeNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource

        berth_type = BerthType.objects.create(
            mooring_type=kwargs.get("mooring_type"),
            width=kwargs.get("width"),
            length=kwargs.get("length"),
        )
        return CreateBerthTypeMutation(berth_type=berth_type)


class UpdateBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        mooring_type = BerthMooringTypeEnum()
        width = graphene.Int()
        length = graphene.Int()

    berth_type = graphene.Field(BerthTypeNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # modify the specific resource
        # GQL IDs have to be translated to Django model UUIDs
        id = from_global_id(kwargs.pop("id"))[1]

        try:
            berth_type = BerthType.objects.get(pk=id)
        except BerthType.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        update_object(berth_type, kwargs)

        return UpdateBerthTypeMutation(berth_type=berth_type)


class DeleteBerthTypeMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(kwargs.get("id"))[1]

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
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        lang = get_language()

        availability_level_id = kwargs.pop("availability_level_id", None)
        if availability_level_id:
            try:
                kwargs["availability_level"] = AvailabilityLevel.objects.get(
                    pk=availability_level_id
                )
            except AvailabilityLevel.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

        municipality_id = kwargs.pop("municipality_id", None)
        if municipality_id:
            try:
                kwargs["municipality"] = Municipality.objects.get(id=municipality_id)
            except Municipality.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

        harbor = Harbor.objects.language(lang).create(**kwargs)

        return CreateHarborMutation(harbor=harbor)


class UpdateHarborMutation(graphene.ClientIDMutation):
    class Input(HarborInput):
        id = graphene.ID(required=True)

    harbor = graphene.Field(HarborNode)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(kwargs.pop("id"))[1]

        lang = get_language()

        try:
            harbor = Harbor.objects.language(lang).get(pk=id)

            availability_level_id = kwargs.pop("availability_level_id", None)
            if availability_level_id:
                kwargs["availability_level"] = AvailabilityLevel.objects.language(
                    lang
                ).get(pk=availability_level_id)

            municipality_id = kwargs.pop("municipality_id", None)
            if municipality_id:
                kwargs["municipality"] = Municipality.objects.get(id=municipality_id)
        except (
            Harbor.DoesNotExist,
            AvailabilityLevel.DoesNotExist,
            Municipality.DoesNotExist,
        ) as e:
            raise VenepaikkaGraphQLError(e)

        update_object(harbor, kwargs)

        return UpdateHarborMutation(harbor=harbor)


class DeleteHarborMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        id = from_global_id(kwargs.get("id"))[1]

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
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        suitable_boat_types = kwargs.pop("suitable_boat_types", [])

        harbor_global_id = kwargs.pop("harbor_id", None)
        if harbor_global_id:
            harbor_id = from_global_id(harbor_global_id)[1]
            try:
                kwargs["harbor"] = Harbor.objects.get(pk=harbor_id)
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
            pier = Pier.objects.create(**kwargs)
            pier.suitable_boat_types.set(boat_types)
        except IntegrityError as e:
            raise VenepaikkaGraphQLError(e)

        return CreatePierMutation(pier=pier)


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
