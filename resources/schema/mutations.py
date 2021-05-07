import graphene
import graphql_geojson
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _
from graphene_file_upload.scalars import Upload
from munigeo.models import Municipality

from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.enums import LeaseStatus
from leases.models import BerthLease, WinterStorageLease
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import (
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
from .types import (
    BerthMooringTypeEnum,
    BerthNode,
    HarborNode,
    PierNode,
    WinterStorageAreaNode,
    WinterStoragePlaceNode,
    WinterStoragePlaceTypeNode,
    WinterStorageSectionNode,
)


def delete_inactive_leases(lease_class, lookup, model_name):
    # Get all the leases related to the resource
    leases = lease_class.objects.filter(lookup)
    # If there's any active lease, raise an error
    if leases.filter(status=LeaseStatus.PAID).count() > 0:
        raise VenepaikkaGraphQLError(
            _(f"Cannot delete {model_name} because it has some related leases")
        )

    # Delete all the leases associated to the Harbor
    leases.delete()


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
    is_invoiceable = graphene.Boolean()
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

        delete_inactive_leases(BerthLease, Q(berth=berth), "Berth")

        berth.delete()

        return DeleteBerthMutation()


class HarborInput(AbstractAreaInput):
    municipality_id = graphene.String()
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


class AbstractAreaMixin:
    @classmethod
    def validate_availability_level_id(cls, input):
        if availability_level_id := input.pop("availability_level_id", None):
            try:
                input["availability_level"] = AvailabilityLevel.objects.get(
                    pk=availability_level_id
                )
            except AvailabilityLevel.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)

    @classmethod
    def validate_municipality_id(cls, input):
        if municipality_id := input.pop("municipality_id", None):
            try:
                input["municipality"] = Municipality.objects.get(id=municipality_id)
            except Municipality.DoesNotExist as e:
                raise VenepaikkaGraphQLError(e)


class CreateHarborMutation(graphene.ClientIDMutation, AbstractAreaMixin):
    class Input(HarborInput):
        pass

    harbor = graphene.Field(HarborNode)

    @classmethod
    @add_permission_required(Harbor)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.validate_availability_level_id(input)
        cls.validate_municipality_id(input)
        harbor = Harbor.objects.create(**input)

        return CreateHarborMutation(harbor=harbor)


class UpdateHarborMutation(graphene.ClientIDMutation, AbstractAreaMixin):
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

        cls.validate_availability_level_id(input)
        cls.validate_municipality_id(input)
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

        delete_inactive_leases(BerthLease, Q(berth__pier__harbor=harbor), "Harbor")

        harbor.delete()

        return DeleteHarborMutation()


class WinterStorageAreaInput(AbstractAreaInput):
    municipality_id = graphene.String()
    add_map_files = graphene.List(
        Upload,
        description="List of map files that will be added to the existing ones belonging to the WinterStorageArea.",
    )
    availability_level_id = graphene.ID()
    name = graphene.String()
    street_address = graphene.String()
    estimated_number_of_section_spaces = graphene.Int()
    max_length_of_section_spaces = graphene.Decimal()
    estimated_number_of_unmarked_spaces = graphene.Int()


class CreateWinterStorageAreaMutation(graphene.ClientIDMutation, AbstractAreaMixin):
    class Input(WinterStorageAreaInput):
        pass

    winter_storage_area = graphene.Field(WinterStorageAreaNode)

    @classmethod
    @add_permission_required(WinterStorageArea)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):

        cls.validate_availability_level_id(input)
        cls.validate_municipality_id(input)
        winter_storage_area = WinterStorageArea.objects.create(**input)

        return CreateWinterStorageAreaMutation(winter_storage_area=winter_storage_area)


class DeleteWinterStorageAreaMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageArea)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_area = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageAreaNode, nullable=False,
        )

        delete_inactive_leases(
            WinterStorageLease,
            Q(place__winter_storage_section__area=winter_storage_area)
            | Q(section__area=winter_storage_area),
            "WinterStorageArea",
        )

        winter_storage_area.delete()

        return DeleteWinterStorageAreaMutation()


class UpdateWinterStorageAreaMutation(graphene.ClientIDMutation, AbstractAreaMixin):
    class Input(WinterStorageAreaInput):
        id = graphene.ID(required=True)
        remove_map_files = graphene.List(
            graphene.ID, description="List of IDs of the maps to be removed."
        )

    winter_storage_area = graphene.Field(WinterStorageAreaNode)

    @classmethod
    @change_permission_required(WinterStorageArea)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_area = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageAreaNode, nullable=False,
        )
        cls.validate_availability_level_id(input)
        cls.validate_municipality_id(input)
        update_object(winter_storage_area, input)

        return UpdateWinterStorageAreaMutation(winter_storage_area=winter_storage_area)


class AbstractPlaceTypeInput:
    width = graphene.Float(description=_("width (m)"))
    length = graphene.Float(description=_("length (m)"))


class WinterStoragePlaceTypeInput(AbstractPlaceTypeInput):
    pass


class CreateWinterStoragePlaceTypeMutation(graphene.ClientIDMutation):
    class Input(WinterStoragePlaceTypeInput):
        pass
        # width = graphene.Float(description=_("width (m)"), required=True)
        # length = graphene.Float(description=_("length (m)"), required=True)

    winter_storage_place_type = graphene.Field(WinterStoragePlaceTypeNode)

    @classmethod
    @add_permission_required(WinterStoragePlaceType)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_place_type = WinterStoragePlaceType.objects.create(**input)
        return CreateWinterStoragePlaceTypeMutation(
            winter_storage_place_type=winter_storage_place_type
        )


class UpdateWinterStoragePlaceTypeMutation(graphene.ClientIDMutation):
    class Input(WinterStoragePlaceTypeInput):
        id = graphene.ID(required=True)

    winter_storage_place_type = graphene.Field(WinterStoragePlaceTypeNode)

    @classmethod
    @change_permission_required(WinterStoragePlaceType)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_place_type = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStoragePlaceTypeNode, nullable=False,
        )
        update_object(winter_storage_place_type, input)

        return UpdateWinterStoragePlaceTypeMutation(
            winter_storage_place_type=winter_storage_place_type
        )


class DeleteWinterStoragePlaceTypeMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStoragePlaceType)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_place_type = get_node_from_global_id(
            info, input.get("id"), only_type=WinterStoragePlaceTypeNode, nullable=False,
        )
        if place_count := winter_storage_place_type.places.count():
            raise VenepaikkaGraphQLError(
                _(
                    f"Cannot delete WinterStoragePlaceType because it has {place_count} related places"
                )
            )

        winter_storage_place_type.delete()

        return DeleteWinterStoragePlaceTypeMutation()


class PierInput(AbstractAreaSectionInput):
    harbor_id = graphene.ID()
    suitable_boat_types = graphene.List(graphene.ID)
    mooring = graphene.Boolean()
    waste_collection = graphene.Boolean()
    lighting = graphene.Boolean()
    personal_electricity = graphene.Boolean()
    price_tier = graphene.Field("payments.schema.PriceTierEnum")


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

        delete_inactive_leases(BerthLease, Q(berth__pier=pier), "Pier")

        pier.delete()

        return DeletePierMutation()


class WinterStorageSectionInput(AbstractAreaSectionInput):
    area_id = graphene.ID()
    summer_storage_for_docking_equipment = graphene.Boolean()
    summer_storage_for_trailers = graphene.Boolean()
    summer_storage_for_boats = graphene.Boolean()


class CreateWinterStorageSectionMutation(graphene.ClientIDMutation):
    class Input(WinterStorageSectionInput):
        area_id = graphene.ID(required=True)

    winter_storage_section = graphene.Field(WinterStorageSectionNode)

    @classmethod
    @add_permission_required(WinterStorageSection)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):

        if input.get("area_id"):
            area = get_node_from_global_id(
                info,
                input.pop("area_id"),
                only_type=WinterStorageAreaNode,
                nullable=False,
            )
            input["area"] = area

        try:
            # identifier is unique within sections of WinterStorageArea
            winter_storage_section = WinterStorageSection.objects.create(**input)
        except IntegrityError as e:
            raise VenepaikkaGraphQLError(e)

        return CreateWinterStorageSectionMutation(
            winter_storage_section=winter_storage_section
        )


class UpdateWinterStorageSectionMutation(graphene.ClientIDMutation):
    class Input(WinterStorageSectionInput):
        id = graphene.ID(required=True)

    winter_storage_section = graphene.Field(WinterStorageSectionNode)

    @classmethod
    @change_permission_required(WinterStorageSection)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_section = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageSectionNode, nullable=False,
        )

        if input.get("area_id"):
            area = get_node_from_global_id(
                info,
                input.pop("area_id"),
                only_type=WinterStorageAreaNode,
                nullable=False,
            )
            input["area"] = area

        try:
            update_object(winter_storage_section, input)
        except IntegrityError as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateWinterStorageSectionMutation(
            winter_storage_section=winter_storage_section
        )


class DeleteWinterStorageSectionMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageSection)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_section = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageSectionNode, nullable=False,
        )

        delete_inactive_leases(
            WinterStorageLease,
            Q(place__winter_storage_section=winter_storage_section)
            | Q(section=winter_storage_section),
            "WinterStorageSection",
        )

        winter_storage_section.delete()

        return DeleteWinterStorageSectionMutation()


class WinterStoragePlaceInput(AbstractBoatPlaceInput):
    number = graphene.String()
    winter_storage_section_id = graphene.ID()
    comment = graphene.String()
    width = graphene.Float(description=_("width (m)"))
    length = graphene.Float(description=_("length (m)"))


class CreateWinterStoragePlaceMutation(graphene.ClientIDMutation):
    class Input(WinterStoragePlaceInput):
        number = graphene.String(required=True)
        winter_storage_section_id = graphene.ID(required=True)
        width = graphene.Float(description=_("width (m)"), required=True)

    winter_storage_place = graphene.Field(WinterStoragePlaceNode)

    @classmethod
    @add_permission_required(WinterStoragePlace)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        width = input.pop("width", None)
        length = input.pop("length", None)

        place_type, created = WinterStoragePlaceType.objects.get_or_create(
            width=width, length=length
        )
        input["place_type"] = place_type

        input["winter_storage_section"] = get_node_from_global_id(
            info,
            input.pop("winter_storage_section_id"),
            only_type=WinterStorageSectionNode,
            nullable=False,
        )
        winter_storage_place = WinterStoragePlace.objects.create(**input)
        return CreateWinterStoragePlaceMutation(
            winter_storage_place=winter_storage_place
        )


class UpdateWinterStoragePlaceMutation(graphene.ClientIDMutation):
    class Input(WinterStoragePlaceInput):
        id = graphene.ID(required=True)

    winter_storage_place = graphene.Field(WinterStoragePlaceNode)

    @classmethod
    @change_permission_required(WinterStoragePlace)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_place = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStoragePlaceNode, nullable=False,
        )

        width = input.pop("width", None)
        length = input.pop("length", None)
        place_type = None

        if any([width, length]):
            old_place_type = winter_storage_place.place_type
            place_type, created = WinterStoragePlaceType.objects.get_or_create(
                width=width or old_place_type.width,
                length=length or old_place_type.length,
            )

        if place_type:
            input["place_type"] = place_type

        if input.get("winter_storage_section_id"):
            input["winter_storage_section"] = get_node_from_global_id(
                info,
                input.pop("winter_storage_section_id"),
                only_type=WinterStorageSectionNode,
                nullable=False,
            )

        update_object(winter_storage_place, input)

        return UpdateWinterStoragePlaceMutation(
            winter_storage_place=winter_storage_place
        )


class DeleteWinterStoragePlaceMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStoragePlace)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        winter_storage_place = get_node_from_global_id(
            info, input.get("id"), only_type=WinterStoragePlaceNode, nullable=False,
        )

        delete_inactive_leases(
            WinterStorageLease, Q(place=winter_storage_place), "WinterStoragePlace"
        )

        winter_storage_place.delete()

        return DeleteWinterStoragePlaceMutation()


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
    create_harbor = CreateHarborMutation.Field()
    delete_harbor = DeleteHarborMutation.Field()
    update_harbor = UpdateHarborMutation.Field()

    # Piers
    create_pier = CreatePierMutation.Field()
    delete_pier = DeletePierMutation.Field()
    update_pier = UpdatePierMutation.Field()

    # Winter storage areas
    create_winter_storage_area = CreateWinterStorageAreaMutation.Field()
    delete_winter_storage_area = DeleteWinterStorageAreaMutation.Field()
    update_winter_storage_area = UpdateWinterStorageAreaMutation.Field()

    # Winter storage area types
    create_winter_storage_place_type = CreateWinterStoragePlaceTypeMutation.Field()
    delete_winter_storage_place_type = DeleteWinterStoragePlaceTypeMutation.Field()
    update_winter_storage_place_type = UpdateWinterStoragePlaceTypeMutation.Field()

    create_winter_storage_place = CreateWinterStoragePlaceMutation.Field()
    delete_winter_storage_place = DeleteWinterStoragePlaceMutation.Field()
    update_winter_storage_place = UpdateWinterStoragePlaceMutation.Field()

    create_winter_storage_section = CreateWinterStorageSectionMutation.Field()
    delete_winter_storage_section = DeleteWinterStorageSectionMutation.Field()
    update_winter_storage_section = UpdateWinterStorageSectionMutation.Field()
