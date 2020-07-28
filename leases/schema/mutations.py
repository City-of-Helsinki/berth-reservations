import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from applications.enums import ApplicationStatus
from applications.models import BerthApplication, WinterStorageApplication
from applications.new_schema import BerthApplicationNode, WinterStorageApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from payments.models import BerthPriceGroup, BerthProduct, Order, WinterStorageProduct
from resources.schema import BerthNode, WinterStoragePlaceNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease
from .types import BerthLeaseNode, WinterStorageLeaseNode


class AbstractLeaseInput:
    boat_id = graphene.ID()
    start_date = graphene.Date()
    end_date = graphene.Date()
    comment = graphene.String()


class CreateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        application_id = graphene.ID(required=True)
        berth_id = graphene.ID(required=True)

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    @view_permission_required(BerthApplication, CustomerProfile)
    @add_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info,
            input.pop("application_id"),
            only_type=BerthApplicationNode,
            nullable=False,
        )

        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
            )

        berth = get_node_from_global_id(
            info, input.pop("berth_id"), only_type=BerthNode, nullable=False,
        )

        input["application"] = application
        input["berth"] = berth
        input["customer"] = application.customer

        if input.get("boat_id", False):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            lease = BerthLease.objects.create(**input)
            price_group = BerthPriceGroup.objects.get_or_create_for_width(
                berth.berth_type.width
            )
            price_group_products = BerthProduct.objects.filter(price_group=price_group)
            harbor_product = price_group_products.filter(harbor=berth.pier.harbor)

            product = (
                harbor_product.first()
                if harbor_product
                else price_group_products.get(harbor__isnull=True)
            )

            Order.objects.create(
                customer=input["customer"], lease=lease, product=product
            )
        except BerthProduct.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        application.status = ApplicationStatus.OFFER_GENERATED
        application.save()

        return CreateBerthLeaseMutation(berth_lease=lease)


class UpdateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        id = graphene.ID(required=True)
        application_id = graphene.ID()

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    @change_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthLeaseNode, nullable=False,
        )
        application_id = input.get("application_id")

        if application_id:
            # If the application id was passed, raise an error if it doesn't exist
            application = get_node_from_global_id(
                info, application_id, only_type=BerthApplicationNode, nullable=False,
            )
            if not application.customer:
                raise VenepaikkaGraphQLError(
                    _("Application must be connected to an existing customer first")
                )
            input["application"] = application
            input["customer"] = application.customer

        if input.get("boat_id", False):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            update_object(lease, input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return UpdateBerthLeaseMutation(berth_lease=lease)


class DeleteBerthLeaseMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthLeaseNode, nullable=False,
        )

        if lease.status != LeaseStatus.DRAFTED:
            raise VenepaikkaGraphQLError(
                _(f"Lease object is not DRAFTED anymore: {lease.status}")
            )

        if lease.application:
            lease.application.status = ApplicationStatus.PENDING
            lease.application.save()

        lease.delete()

        return DeleteBerthLeaseMutation()


class CreateWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        application_id = graphene.ID(required=True)
        place_id = graphene.ID(required=True)

    winter_storage_lease = graphene.Field(WinterStorageLeaseNode)

    @classmethod
    @view_permission_required(WinterStorageApplication, CustomerProfile)
    @add_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info,
            input.pop("application_id"),
            only_type=WinterStorageApplicationNode,
            nullable=False,
        )

        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
            )

        place = get_node_from_global_id(
            info,
            input.pop("place_id"),
            only_type=WinterStoragePlaceNode,
            nullable=False,
        )

        input["application"] = application
        input["place"] = place
        input["customer"] = application.customer

        if input.get("boat_id", None):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            lease = WinterStorageLease.objects.create(**input)
            product = WinterStorageProduct.objects.get(
                winter_storage_area=place.winter_storage_section.area
            )
            Order.objects.create(
                customer=input["customer"], lease=lease, product=product
            )
        except WinterStorageProduct.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        application.status = ApplicationStatus.OFFER_GENERATED
        application.save()

        return CreateWinterStorageLeaseMutation(winter_storage_lease=lease)


class UpdateWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        id = graphene.ID(required=True)
        application_id = graphene.ID()

    winter_storage_lease = graphene.Field(WinterStorageLeaseNode)

    @classmethod
    @change_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageLeaseNode, nullable=False,
        )
        application_id = input.get("application_id")

        if application_id:
            # If the application id was passed, raise an error if it doesn't exist
            application = get_node_from_global_id(
                info,
                application_id,
                only_type=WinterStorageApplicationNode,
                nullable=False,
            )
            if not application.customer:
                raise VenepaikkaGraphQLError(
                    _("Application must be connected to an existing customer first")
                )
            input["application"] = application
            input["customer"] = application.customer

        if input.get("boat_id", False):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            update_object(lease, input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return UpdateWinterStorageLeaseMutation(winter_storage_lease=lease)


class DeleteWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageLeaseNode, nullable=False,
        )

        if lease.status != LeaseStatus.DRAFTED:
            raise VenepaikkaGraphQLError(
                _(f"Lease object is not DRAFTED anymore: {lease.status}")
            )

        if lease.application:
            lease.application.status = ApplicationStatus.PENDING
            lease.application.save()

        lease.delete()

        return DeleteWinterStorageLeaseMutation()


class Mutation:
    create_berth_lease = CreateBerthLeaseMutation.Field(
        description="Creates a `BerthLease` associated with the `BerthApplication` and `Berth` passed. "
        "The lease is associated with the `CustomerProfile` that owns the application."
        "\n\nAn `Order` will be generated with this lease. A valid `BerthProduct` is required."
        "\n\n**Requires permissions** to access applications."
        "\n\nLeases have default start and end dates: 10.6. - 14.9. If a lease object is being created before 10.6, "
        "then the dates are in the same year. If the object is being created between those dates, "
        "then the start date is the date of creation and end date is 14.9 of the same year. "
        "If the object is being created after 14.9, then the dates are from next year."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
        "\n* There is no `BerthProduct` that can be associated to the `order`/`lease`"
    )
    update_berth_lease = UpdateBerthLeaseMutation.Field(
        description="Updates a `BerthLease` object."
        "\n\n**Requires permissions** to edit leases."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
    )
    delete_berth_lease = DeleteBerthLeaseMutation.Field(
        description="Deletes a `BerthLease` object."
        "\n\nIt **only** works for leases that haven't been assigned, i.e., leases that have "
        '\n`berth_lease.status == "DRAFTED"`.'
        "\n\n**Requires permissions** to access leases."
        "\n\nErrors:"
        "\n* A berth lease that is not `DRAFTED` anymore is passed"
        "\n* The passed lease ID doesn't exist"
    )

    create_winter_storage_lease = CreateWinterStorageLeaseMutation.Field(
        description="Creates a `WinterStorageLease` associated with the `WinterStorageApplication` "
        "and `WinterStoragePlace` passed. The lease is associated with the `CustomerProfile` that owns the application."
        "\n\nAn `Order` will be generated with this lease. A valid `WinterStorageProduct` is required."
        "\n\n**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
        "\n* There is no `WinterStorageProduct` that can be associated to the `order`/`lease`"
    )
    update_winter_storage_lease = UpdateWinterStorageLeaseMutation.Field(
        description="Updates a `WinterStorageLease` object."
        "\n\n**Requires permissions** to edit leases."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
    )
    delete_winter_storage_lease = DeleteWinterStorageLeaseMutation.Field(
        description="Deletes a `WinterStorageLease` object."
        "\n\nIt **only** works for leases that WinterStorage't been assigned, i.e., leases that have "
        '\n`winter_storage_lease.status == "DRAFTED"`.'
        "\n\n**Requires permissions** to access leases."
        "\n\nErrors:"
        "\n* A winter storage lease that is not `DRAFTED` anymore is passed"
        "\n* The passed lease ID doesn't exist"
    )
