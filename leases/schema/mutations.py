import threading
from datetime import date, datetime

import graphene
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from applications.enums import ApplicationAreaType, ApplicationStatus
from applications.models import BerthApplication, WinterStorageApplication
from applications.schema import BerthApplicationNode, WinterStorageApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from contracts.services import get_contract_service
from customers.models import CustomerProfile
from leases.utils import exchange_berth_for_lease
from payments.enums import OrderStatus
from payments.models import BerthProduct, Order, WinterStorageProduct
from resources.schema import BerthNode, WinterStoragePlaceNode, WinterStorageSectionNode
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
from ..services import BerthInvoicingService, WinterStorageInvoicingService
from ..stickers import get_next_sticker_number
from ..utils import calculate_berth_lease_start_date, terminate_lease
from .types import BerthLeaseNode, WinterStorageLeaseNode
from .utils import lookup_or_create_boat


class AbstractLeaseInput:
    boat_id = graphene.ID()
    start_date = graphene.Date()
    end_date = graphene.Date()
    comment = graphene.String()


def _lookup_application_and_customer(info, input, application_node_type):
    from customers.schema import ProfileNode  # import here avoid circular import

    if application_id := input.pop("application_id", None):
        if "customer_id" in input:
            raise VenepaikkaGraphQLError(
                _(
                    "Can not specify both application and customer when creating a new berth lease"
                )
            )
        application = get_node_from_global_id(
            info,
            application_id,
            only_type=application_node_type,
            nullable=False,
        )
        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
            )
        input["application"] = application
        input["customer"] = application.customer

    elif customer_id := input.pop("customer_id", None):
        assert "customer" not in input
        input["customer"] = get_node_from_global_id(
            info,
            customer_id,
            only_type=ProfileNode,
            nullable=False,
        )
    else:
        raise VenepaikkaGraphQLError(
            _(
                "Must specify either application or customer when creating a new berth lease"
            )
        )


class CreateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        # either application_id or customer_id must be provided, but not both
        application_id = graphene.ID()
        customer_id = graphene.ID()
        berth_id = graphene.ID(required=True)

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    def lookup_application_and_customer(cls, info, input):
        from customers.schema import ProfileNode  # import here avoid circular import

        if application_id := input.pop("application_id", None):
            if "customer_id" in input:
                raise VenepaikkaGraphQLError(
                    _(
                        "Can not specify both application and customer when creating a new berth lease"
                    )
                )
            application: BerthApplication = get_node_from_global_id(
                info,
                application_id,
                only_type=BerthApplicationNode,
                nullable=False,
            )
            if not application.customer:
                raise VenepaikkaGraphQLError(
                    _("Application must be connected to an existing customer first")
                )
            input["application"] = application
            input["customer"] = application.customer

        elif customer_id := input.pop("customer_id", None):
            assert "customer" not in input
            input["customer"] = get_node_from_global_id(
                info,
                customer_id,
                only_type=ProfileNode,
                nullable=False,
            )
        else:
            raise VenepaikkaGraphQLError(
                _(
                    "Must specify either application or customer when creating a new berth lease"
                )
            )

    @classmethod
    @view_permission_required(BerthApplication, CustomerProfile)
    @add_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        _lookup_application_and_customer(info, input, BerthApplicationNode)

        if boat := lookup_or_create_boat(info, input):
            input["boat"] = boat

        berth = get_node_from_global_id(
            info,
            input.pop("berth_id"),
            only_type=BerthNode,
            nullable=False,
        )
        input["berth"] = berth

        try:
            lease = BerthLease.objects.create(**input)

            order = Order.objects.create(customer=input["customer"], lease=lease)
            # Do not create a contract for non-billable customers.
            if not input["customer"].is_non_billable_customer():
                get_contract_service().create_berth_contract(lease)
        except BerthProduct.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)
        except ValidationError as e:
            raise VenepaikkaGraphQLError(str(e))

        if application := input.get("application"):
            application.status = ApplicationStatus.OFFER_GENERATED
            application.save()

        if order.customer.is_non_billable_customer():
            order.set_status(OrderStatus.PAID_MANUALLY, "Non-billable customer.")

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
            info,
            input.pop("id"),
            only_type=BerthLeaseNode,
            nullable=False,
        )
        application_id = input.get("application_id")

        if application_id:
            # If the application id was passed, raise an error if it doesn't exist
            application = get_node_from_global_id(
                info,
                application_id,
                only_type=BerthApplicationNode,
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
                info,
                input.pop("boat_id"),
                only_type=BoatNode,
                nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            update_object(lease, input)
        except ValidationError as e:
            raise VenepaikkaGraphQLError(str(e))

        return UpdateBerthLeaseMutation(berth_lease=lease)


class DeleteBerthLeaseMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info,
            input.pop("id"),
            only_type=BerthLeaseNode,
            nullable=False,
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


class SwitchBerthMutation(graphene.ClientIDMutation):
    class Input:
        old_lease_id = graphene.ID(required=True)
        new_berth_id = graphene.ID(required=True)
        switch_date = graphene.Date(
            description="The date which will mark the end of the old lease and the start of the new lease."
            "If none is provided, it will default to the day when the mutation is called"
        )

    old_berth_lease = graphene.Field(BerthLeaseNode)
    new_berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    def validate_switch_date(cls, switch_date):
        if isinstance(switch_date, datetime):
            switch_date = switch_date.date()
        if switch_date < date.today() - relativedelta(months=6):
            raise VenepaikkaGraphQLError(
                _("Switch date is more than 6 months in the past")
            )

    @classmethod
    def validate_old_lease(cls, old_lease):
        if not old_lease.is_active:
            raise VenepaikkaGraphQLError(_("Berth lease is not active"))
        if old_lease.status != LeaseStatus.PAID:
            raise VenepaikkaGraphQLError(_(f"Lease is not paid: {old_lease.status}"))

    @classmethod
    @add_permission_required(BerthLease)
    @change_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, old_lease_id, new_berth_id, **input):
        switch_date = input.get("switch_date") or calculate_berth_lease_start_date()
        cls.validate_switch_date(switch_date)

        old_lease = get_node_from_global_id(
            info,
            old_lease_id,
            only_type=BerthLeaseNode,
            nullable=False,
        )
        cls.validate_old_lease(old_lease)

        new_berth = get_node_from_global_id(
            info,
            new_berth_id,
            only_type=BerthNode,
            nullable=False,
        )

        old_lease_comment = _("Lease terminated due to berth switch")
        new_lease_comment = _("Lease created from a berth switch")
        old_lease, new_lease = exchange_berth_for_lease(
            old_lease,
            new_berth,
            switch_date,
            old_lease_comment,
            new_lease_comment,
        )

        return SwitchBerthMutation(old_berth_lease=old_lease, new_berth_lease=new_lease)


class CreateWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input(AbstractLeaseInput):
        # either application_id or customer_id must be provided, but not both
        application_id = graphene.ID()
        customer_id = graphene.ID()
        place_id = graphene.ID()
        section_id = graphene.ID()

    winter_storage_lease = graphene.Field(WinterStorageLeaseNode)

    @classmethod
    @view_permission_required(WinterStorageApplication, CustomerProfile)
    @add_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):  # noqa: C901
        if "place_id" not in input and "application_id" not in input:
            raise VenepaikkaGraphQLError(
                _("Winter Storage leases without a Place require an Application.")
            )

        _lookup_application_and_customer(info, input, WinterStorageApplicationNode)

        if "place_id" in input and "section_id" in input:
            raise VenepaikkaGraphQLError(
                _("Cannot receive both Winter Storage Place and Section")
            )

        if place_id := input.pop("place_id", None):
            place = get_node_from_global_id(
                info,
                place_id,
                only_type=WinterStoragePlaceNode,
                nullable=False,
            )
            input["place"] = place
        elif section_id := input.pop("section_id", None):
            section = get_node_from_global_id(
                info,
                section_id,
                only_type=WinterStorageSectionNode,
                nullable=False,
            )
            input["section"] = section
        else:
            raise VenepaikkaGraphQLError(
                _("Either Winter Storage Place or Section are required")
            )

        if boat := lookup_or_create_boat(info, input):
            input["boat"] = boat

        try:
            lease = WinterStorageLease.objects.create(**input)
            order = Order.objects.create(customer=input["customer"], lease=lease)
            # Do not create a contract for non-billable customers.
            if not input["customer"].is_non_billable_customer():
                get_contract_service().create_winter_storage_contract(lease)
        except WinterStorageProduct.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)
        except ValidationError as e:
            raise VenepaikkaGraphQLError(str(e))

        if application := input.get("application"):
            application.status = ApplicationStatus.OFFER_GENERATED
            application.save()

        if order.customer.is_non_billable_customer():
            order.set_status(OrderStatus.PAID_MANUALLY, "Non-billable customer.")

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
            info,
            input.pop("id"),
            only_type=WinterStorageLeaseNode,
            nullable=False,
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
                info,
                input.pop("boat_id"),
                only_type=BoatNode,
                nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            update_object(lease, input)
        except ValidationError as e:
            raise VenepaikkaGraphQLError(str(e))

        return UpdateWinterStorageLeaseMutation(winter_storage_lease=lease)


class DeleteWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info,
            input.pop("id"),
            only_type=WinterStorageLeaseNode,
            nullable=False,
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


class TerminateLeaseInput:
    id = graphene.ID(required=True)
    end_date = graphene.Date(
        description="The date which will mark the end of the lease. If none is provided, "
        "it will default to the day when the mutation is called"
    )
    profile_token = graphene.String(
        description="To fetch the email the from Profile service in case the lease doesn't have an application"
    )


class TerminateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(TerminateLeaseInput):
        pass

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    @change_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, **input):
        try:
            lease: BerthLease = get_node_from_global_id(
                info,
                id,
                only_type=BerthLeaseNode,
                nullable=False,
            )

            lease = terminate_lease(
                lease,
                end_date=input.get("end_date"),
                profile_token=input.get("profile_token"),
                send_notice=True,
            )
        except (
            BerthLease.DoesNotExist,
            AnymailError,
            OSError,
            ValidationError,
            VenepaikkaGraphQLError,
        ) as e:
            raise VenepaikkaGraphQLError(str(e)) from e

        return TerminateBerthLeaseMutation(berth_lease=lease)


class TerminateWinterStorageLeaseMutation(graphene.ClientIDMutation):
    class Input(TerminateLeaseInput):
        pass

    winter_storage_lease = graphene.Field(WinterStorageLeaseNode)

    @classmethod
    @change_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, **input):
        try:
            lease: WinterStorageLease = get_node_from_global_id(
                info,
                id,
                only_type=WinterStorageLeaseNode,
                nullable=False,
            )

            lease = terminate_lease(
                lease,
                end_date=input.get("end_date"),
                profile_token=input.get("profile_token"),
                send_notice=True,
            )
        except (
            WinterStorageLease.DoesNotExist,
            AnymailError,
            OSError,
            ValidationError,
            VenepaikkaGraphQLError,
        ) as e:
            raise VenepaikkaGraphQLError(str(e)) from e

        return TerminateWinterStorageLeaseMutation(winter_storage_lease=lease)


class AssignNewStickerNumberMutation(graphene.ClientIDMutation):
    class Input:
        lease_id = graphene.String(required=True)

    sticker_number = graphene.Int()

    @classmethod
    @change_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info,
            input.pop("lease_id"),
            only_type=WinterStorageLeaseNode,
            nullable=False,
        )
        if lease.status != LeaseStatus.PAID:
            raise VenepaikkaGraphQLError(_("Lease must be in PAID status"))
        elif lease.application.area_type != ApplicationAreaType.UNMARKED:
            raise VenepaikkaGraphQLError(_("Lease must refer to unmarked area"))

        new_sticker_number = get_next_sticker_number(lease.start_date)
        lease.sticker_number = new_sticker_number
        lease.sticker_posted = None
        lease.save()

        return AssignNewStickerNumberMutation(sticker_number=new_sticker_number)


class SetStickersPostedMutation(graphene.ClientIDMutation):
    class Input:
        lease_ids = graphene.List(graphene.NonNull(graphene.String), required=True)
        date = graphene.Date(required=True)

    @classmethod
    @change_permission_required(WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        date = input.pop("date")
        for lease_id in input.pop("lease_ids", []):
            lease = get_node_from_global_id(
                info, lease_id, only_type=WinterStorageLeaseNode, nullable=False
            )
            if lease.sticker_number:
                lease.sticker_posted = date
                lease.save()
            else:
                raise VenepaikkaGraphQLError(
                    _("All leases must have an assigned sticker number")
                )

        return SetStickersPostedMutation()


class SendExistingInvoicesInput:
    due_date = graphene.Date(
        description="Defaults to 14 days from the date when the mutation is executed."
    )


class SendExistingBerthInvoicesMutation(graphene.ClientIDMutation):
    class Input(SendExistingInvoicesInput):
        profile_token = graphene.String(
            required=True,
            description="API token for Helsinki profile GraphQL API",
        )

    ok = graphene.Boolean(required=True)

    @classmethod
    @view_permission_required(CustomerProfile)
    @change_permission_required(BerthLease, WinterStorageLease, Order)
    def mutate_and_get_payload(cls, root, info, profile_token, **input):
        service = BerthInvoicingService(
            request=info.context,
            profile_token=profile_token,
            due_date=input.get("due_date"),
        )
        t1 = threading.Thread(target=service.send_invoices, args=[])
        t1.start()

        return SendExistingBerthInvoicesMutation(ok=True)


class SendExistingWinterStorageInvoicesMutation(graphene.ClientIDMutation):
    class Input(SendExistingInvoicesInput):
        profile_token = graphene.String(
            required=True,
            description="API token for Helsinki profile GraphQL API",
        )

    ok = graphene.Boolean(required=True)

    @classmethod
    @view_permission_required(CustomerProfile)
    @change_permission_required(BerthLease, WinterStorageLease, Order)
    def mutate_and_get_payload(cls, root, info, profile_token, **input):
        service = WinterStorageInvoicingService(
            request=info.context,
            profile_token=profile_token,
            due_date=input.get("due_date"),
        )
        t1 = threading.Thread(target=service.send_invoices, args=[])
        t1.start()

        return SendExistingWinterStorageInvoicesMutation(ok=True)


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
    switch_berth = SwitchBerthMutation.Field(
        description="Switches the berth of a `BerthLease` object to the provided `Berth`."
        "\n\n**Requires permissions** to edit and create leases."
        "\n\nErrors:"
        "\n* The passed lease or berth ID doesn't exist"
        "\n* A berth lease that is not `PAID` is passed"
        "\n* The the start date year does not match with the end date year"
        "\n* A berth lease that has no contract is passed"
        "\n* The passed berth already has a lease"
        "\n* The provided `switch_date` is more than 6 months in the past"
    )
    terminate_berth_lease = TerminateBerthLeaseMutation.Field(
        description="Marks a `BerthLease` as terminated."
        "\n\nIt **only** works for leases that have been paid. "
        "It receives an optional date for when the lease should end."
        "\n\n**Requires permissions** to edit leases."
        "\n\nErrors:"
        "\n* A berth lease that is not `PAID` is passed"
        "\n* The passed lease ID doesn't exist"
    )

    create_winter_storage_lease = CreateWinterStorageLeaseMutation.Field(
        description="Creates a `WinterStorageLease` associated with the `WinterStorageApplication` "
        "and `WinterStoragePlace` passed. The lease is associated with the `CustomerProfile` that owns the application."
        "\n\nIt is also possible to create a `WinterStorageLease` without a `WinterStorageApplication` by providing "
        "`customerId` instead of `applicationId`. In that case, `placeId` is required also."
        "\n\nAn `Order` will be generated with this lease. A valid `WinterStorageProduct` is required."
        "\n\n**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
        "\n* There is no `WinterStorageProduct` that can be associated to the `order`/`lease`"
        "\n* Neither `placeId` or `areaId` is passed"
        "\n* Both `applicationId` and `customerId` are passed"
        "\n* Neither `applicationId` or `placeId` is passed"
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
    terminate_winter_storage_lease = TerminateWinterStorageLeaseMutation.Field(
        description="Marks a `WinterStorageLease` as terminated."
        "\n\nIt **only** works for leases that have been paid. "
        "It receives an optional date for when the lease should end."
        "\n\n**Requires permissions** to edit leases."
        "\n\nErrors:"
        "\n* A berth lease that is not `PAID` is passed"
        "\n* The passed lease ID doesn't exist"
    )
    assign_new_sticker_number = AssignNewStickerNumberMutation.Field(
        description="Assigns new sticker number for an unmarked WS lease"
    )
    set_stickers_posted = SetStickersPostedMutation.Field(
        description="Set posted dates for stickers of unmarked WS leases"
    )

    send_existing_berth_invoices = SendExistingBerthInvoicesMutation.Field()
    send_existing_winter_storage_invoices = (
        SendExistingWinterStorageInvoicesMutation.Field()
    )
