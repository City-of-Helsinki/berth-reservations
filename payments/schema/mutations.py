from decimal import Decimal

import graphene
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from applications.enums import ApplicationAreaType, ApplicationStatus
from applications.models import BerthApplication, WinterStorageApplication
from applications.schema import BerthApplicationNode
from berth_reservations.exceptions import (
    VenepaikkaGraphQLError,
    VenepaikkaGraphQLWarning,
)
from customers.models import CustomerProfile
from customers.schema import ProfileNode
from customers.services import ProfileService
from leases.enums import LeaseStatus
from leases.models import BerthLease, WinterStorageLease
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from leases.utils import (
    calculate_season_end_date,
    calculate_season_start_date,
    exchange_berth_for_lease,
)
from resources.models import Berth
from resources.schema import BerthNode, WinterStorageAreaNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..enums import OfferStatus, OrderStatus, OrderType, ProductServiceType
from ..exceptions import OrderStatusTransitionError, VenepaikkaPaymentError
from ..models import (
    AdditionalProduct,
    BerthProduct,
    BerthSwitchOffer,
    Order,
    OrderLine,
    WinterStorageProduct,
)
from ..providers import get_payment_provider
from ..utils import (
    approve_order,
    fetch_order_profile,
    prepare_for_resending,
    resend_order,
    send_berth_switch_offer,
    send_cancellation_notice,
    send_refund_notice,
    update_order_from_profile,
)
from .types import (
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthProductNode,
    BerthSwitchOfferNode,
    FailedOfferType,
    FailedOrderType,
    OfferStatusEnum,
    OrderLineNode,
    OrderNode,
    OrderRefundNode,
    OrderStatusEnum,
    PeriodTypeEnum,
    PriceUnitsEnum,
    ProductServiceTypeEnum,
    WinterStorageProductNode,
)


class CreateBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        min_width = graphene.Decimal(required=True)
        max_width = graphene.Decimal(required=True)
        tier_1_price = graphene.Decimal(required=True)
        tier_2_price = graphene.Decimal(required=True)
        tier_3_price = graphene.Decimal(required=True)

    berth_product = graphene.Field(BerthProductNode)

    @classmethod
    @add_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            product = BerthProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return CreateBerthProductMutation(berth_product=product)


class UpdateBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        min_width = graphene.Decimal()
        max_width = graphene.Decimal()
        tier_1_price = graphene.Decimal()
        tier_2_price = graphene.Decimal()
        tier_3_price = graphene.Decimal()

    berth_product = graphene.Field(BerthProductNode)

    @classmethod
    @change_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthProductNode, nullable=False
        )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateBerthProductMutation(berth_product=product)


class DeleteBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthProductNode, nullable=False,
        )

        product.delete()

        return DeleteBerthProductMutation()


class CreateWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        price_value = graphene.Decimal(required=True)
        winter_storage_area_id = graphene.ID()

    winter_storage_product = graphene.Field(WinterStorageProductNode)

    @classmethod
    @add_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["winter_storage_area"] = get_node_from_global_id(
            info,
            input.pop("winter_storage_area_id", None),
            only_type=WinterStorageAreaNode,
            nullable=True,
        )
        try:
            product = WinterStorageProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateWinterStorageProductMutation(winter_storage_product=product)


class UpdateWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        price_value = graphene.Decimal()
        winter_storage_area_id = graphene.ID()

    winter_storage_product = graphene.Field(WinterStorageProductNode)

    @classmethod
    @change_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageProductNode, nullable=False
        )
        if "winter_storage_area_id" in input:
            input["winter_storage_area"] = get_node_from_global_id(
                info,
                input.pop("winter_storage_area_id", None),
                only_type=WinterStorageAreaNode,
                nullable=True,
            )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateWinterStorageProductMutation(winter_storage_product=product)


class DeleteWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageProductNode, nullable=False,
        )

        product.delete()

        return DeleteWinterStorageProductMutation()


class AdditionalProductInput:
    service = ProductServiceTypeEnum()
    period = PeriodTypeEnum()
    price_value = graphene.Decimal()
    price_unit = PriceUnitsEnum()
    tax_percentage = AdditionalProductTaxEnum()


class CreateAdditionalProductMutation(graphene.ClientIDMutation):
    class Input(AdditionalProductInput):
        service = ProductServiceTypeEnum(required=True)
        period = PeriodTypeEnum(required=True)
        price_value = graphene.Decimal(required=True)

    additional_product = graphene.Field(AdditionalProductNode)

    @classmethod
    @add_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        if AdditionalProduct.objects.filter(
            service=input.get("service"), period=input.get("period")
        ).exists():
            raise VenepaikkaGraphQLWarning(_("Additional product already exists"))
        try:
            product = AdditionalProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateAdditionalProductMutation(additional_product=product)


class UpdateAdditionalProductMutation(graphene.ClientIDMutation):
    class Input(AdditionalProductInput):
        id = graphene.ID(required=True)

    additional_product = graphene.Field(AdditionalProductNode)

    @classmethod
    @change_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=AdditionalProductNode, nullable=False
        )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateAdditionalProductMutation(additional_product=product)


class DeleteAdditionalProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=AdditionalProductNode, nullable=False,
        )

        product.delete()

        return DeleteAdditionalProductMutation()


class OrderInput:
    lease_id = graphene.ID()
    customer_id = graphene.ID(
        description="**Doesn't have an effect** until the price input is added."
    )
    status = OrderStatusEnum()
    comment = graphene.String()
    due_date = graphene.Date()
    product_id = graphene.ID(
        description="**OBSOLETE**: The product is determined based on the lease passed. "
        "If no lease is provided, an explicit price must be specified (not implemented yet). "
        "This field has no effect at all and will be removed on a later version.",
        deprecation_reason="**OBSOLETE**: The product is determined based on the lease passed. "
        "If no lease is provided, an explicit price must be specified (not implemented yet) "
        "This field has no effect at all and will be removed on a later version.",
    )


class CreateOrderMutation(graphene.ClientIDMutation):
    class Input(OrderInput):
        pass

    order = graphene.Field(OrderNode)

    @classmethod
    @add_permission_required(Order)
    @view_permission_required(BerthLease, WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        if input.get("customer_id") and input.get("lease_id"):
            raise VenepaikkaGraphQLError(_("Cannot receive both Lease and Customer"))

        # TODO: until the price input is added, the customer input won't have an effect
        # _customer = input.pop("customer_id", None)
        input.pop("customer_id", None)

        if lease_id := input.pop("lease_id", None):
            lease = None
            try:
                lease = get_node_from_global_id(
                    info, lease_id, BerthLeaseNode, nullable=True
                )
            # If a different node type is received get_node raises an assertion error
            # when trying to validate the type
            except AssertionError:
                lease = get_node_from_global_id(
                    info, lease_id, WinterStorageLeaseNode, nullable=True
                )
            finally:
                if not lease:
                    raise VenepaikkaGraphQLError(
                        _("Lease with the given ID does not exist")
                    )
                input["lease"] = lease
                input["customer"] = lease.customer

        try:
            order = Order.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateOrderMutation(order=order)


class CreateAdditionalProductOrderMutation(graphene.ClientIDMutation):
    class Input:
        customer_id = graphene.ID(required=True)
        lease_id = graphene.ID(required=True)
        additional_product_id = graphene.ID(required=True)

    order = graphene.Field(OrderNode)

    @classmethod
    @add_permission_required(Order)
    @view_permission_required(BerthLease, WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        customer_id = input.pop("customer_id")
        customer = get_node_from_global_id(
            info, customer_id, ProfileNode, nullable=False
        )

        additional_product_id = input.pop("additional_product_id")
        additional_product = get_node_from_global_id(
            info, additional_product_id, AdditionalProductNode, nullable=False
        )

        lease_id = input.pop("lease_id")
        lease = get_node_from_global_id(info, lease_id, BerthLeaseNode, nullable=False)

        if lease.status != LeaseStatus.PAID:
            raise VenepaikkaGraphQLError(_("Lease must be in PAID status"))
        if additional_product.service != ProductServiceType.STORAGE_ON_ICE:
            raise VenepaikkaGraphQLError(_("Only storage on ice supported"))

        try:
            order = Order.objects.create(
                order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
                customer=customer,
                lease=lease,
                product=None,
                price=Decimal("0.00"),
                tax_percentage=Decimal("0.00"),
            )
            OrderLine.objects.create(order=order, product=additional_product)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return CreateAdditionalProductOrderMutation(order=order)


class UpdateOrderInput(OrderInput, graphene.InputObjectType):
    id = graphene.ID(required=True)


class UpdateOrdersMutation(graphene.ClientIDMutation):
    class Input:
        orders = graphene.List(UpdateOrderInput, required=True)

    successful_orders = graphene.List(OrderNode)
    failed_orders = graphene.List(FailedOrderType)

    @classmethod
    @change_permission_required(Order)
    @view_permission_required(BerthLease, WinterStorageLease)
    def mutate_and_get_payload(cls, root, info, orders, **input):

        successful_orders = []
        failed_orders = []

        for order_input in orders:
            order_id = order_input.pop("id")
            try:
                with transaction.atomic():
                    order = get_node_from_global_id(
                        info, order_id, only_type=OrderNode, nullable=False
                    )
                    if lease_id := order_input.pop("lease_id", None):
                        lease = None
                        try:
                            lease = get_node_from_global_id(
                                info, lease_id, BerthLeaseNode, nullable=True
                            )
                        # If a different node type is received get_node raises an assertion error
                        # when trying to validate the type
                        except AssertionError:
                            lease = get_node_from_global_id(
                                info, lease_id, WinterStorageLeaseNode, nullable=True
                            )
                        finally:
                            if not lease:
                                raise VenepaikkaGraphQLError(
                                    _("Lease with the given ID does not exist")
                                )
                            order_input["lease"] = lease

                    # handle case where order_input has both lease and status.
                    # set order status only after changing the lease, because setting order status
                    # usually triggers a change in lease status.
                    new_status = order_input.pop("status", None)
                    update_object(order, order_input)
                    if new_status:
                        order.set_status(new_status, _("Manually updated by admin"))

            except (
                ValidationError,
                IntegrityError,
                VenepaikkaGraphQLError,
                OrderStatusTransitionError,
            ) as e:
                failed_orders.append(FailedOrderType(id=order_id, error=str(e)))
            else:
                successful_orders.append(order)
        return UpdateOrdersMutation(
            successful_orders=successful_orders, failed_orders=failed_orders
        )


class DeleteOrderMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(Order)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderNode, nullable=False,
        )

        order.delete()

        return DeleteOrderMutation()


class ConfirmPaymentMutation(graphene.ClientIDMutation):
    class Input:
        order_number = graphene.String(required=True)

    url = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        order_number = input.get("order_number", None)
        try:
            order = Order.objects.get(order_number=order_number)
            if order.status not in (OrderStatus.OFFERED, OrderStatus.REJECTED):
                raise VenepaikkaGraphQLError(
                    _("The order is not valid anymore")
                    + f": {OrderStatus(order.status).label}"
                )
            payment_url = get_payment_provider(
                info.context, ui_return_url=settings.VENE_UI_RETURN_URL
            ).initiate_payment(order)
        except Order.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        return ConfirmPaymentMutation(url=payment_url)


class CancelOrderMutation(graphene.ClientIDMutation):
    class Input:
        order_number = graphene.String(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        order_number = input.get("order_number", None)
        try:
            order = Order.objects.get(order_number=order_number)
            if order.status != OrderStatus.OFFERED:
                raise VenepaikkaGraphQLError(
                    _("The order is not valid anymore")
                    + f": {OrderStatus(order.status).label}"
                )
            application = order.lease.application if order.lease else None
            if (
                isinstance(application, WinterStorageApplication)
                and application.area_type == ApplicationAreaType.UNMARKED
            ):
                raise VenepaikkaGraphQLError(
                    _("Cannot cancel Unmarked winter storage order")
                )
            order.set_status(OrderStatus.REJECTED, _("Order rejected by customer"))
            order.invalidate_tokens()
            # annotations aren’t reloaded if using refresh_from_db, so use get() since we need
            # to have the updated value of rejected_at in the notice
            order = Order.objects.get(pk=order.pk)
            send_cancellation_notice(order)
        except (Order.DoesNotExist, ValidationError, AnymailError, OSError,) as e:
            raise VenepaikkaGraphQLError(e)

        return CancelOrderMutation()


class OrderLineInput:
    quantity = graphene.Int(description="Defaults to 1")


class CreateOrderLineMutation(graphene.ClientIDMutation):
    class Input(OrderLineInput):
        order_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)

    order_line = graphene.Field(OrderLineNode)
    order = graphene.Field(OrderNode)

    @classmethod
    @add_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["order"] = get_node_from_global_id(
            info, input.pop("order_id"), only_type=OrderNode, nullable=False
        )
        input["product"] = get_node_from_global_id(
            info,
            input.pop("product_id"),
            only_type=AdditionalProductNode,
            nullable=False,
        )

        try:
            order_line = OrderLine.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateOrderLineMutation(order_line=order_line, order=order_line.order)


class UpdateOrderLineMutation(graphene.ClientIDMutation):
    class Input(OrderLineInput):
        id = graphene.ID(required=True)

    order_line = graphene.Field(OrderLineNode)
    order = graphene.Field(OrderNode)

    @classmethod
    @change_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order_line = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderLineNode, nullable=False
        )

        try:
            update_object(order_line, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateOrderLineMutation(order_line=order_line, order=order_line.order)


class DeleteOrderLineMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order_line = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderLineNode, nullable=False
        )

        order_line.delete()

        return DeleteOrderLineMutation()


class SendBerthSwitchOfferMutation(graphene.ClientIDMutation):
    class Input:
        offers = graphene.List(graphene.ID, required=True)
        due_date = graphene.Date(description="Defaults to the Offer due date")
        profile_token = graphene.String(
            description="API token for Helsinki profile GraphQL API",
        )

    sent_offers = graphene.List(graphene.ID)
    failed_offers = graphene.List(FailedOfferType)

    @classmethod
    @change_permission_required(BerthSwitchOffer,)
    def mutate_and_get_payload(cls, root, info, offers, **input):
        due_date = input.pop("due_date", None)

        failed_offers = []
        sent_offers = []

        for offer_id in offers:
            try:
                with transaction.atomic():
                    offer = get_node_from_global_id(
                        info, offer_id, only_type=BerthSwitchOfferNode, nullable=False
                    )

                    if offer.status not in (OfferStatus.DRAFTED, OfferStatus.OFFERED):
                        # This mutation can also be used to resend offers
                        raise ValidationError(
                            _(f"Cannot send offer in {offer.status} status.")
                        )

                    if profile_token := input.get("profile_token"):
                        offer.update_from_profile(profile_token)

                    if not offer.customer_email and not offer.customer_phone:
                        failed_offers.append(
                            FailedOfferType(
                                id=offer_id,
                                error=_(
                                    "Profile token is required if an offer does not previously have email or phone."
                                ),
                            )
                        )
                        continue
                    send_berth_switch_offer(offer, due_date)
            except (
                AnymailError,
                OSError,
                BerthSwitchOffer.DoesNotExist,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                failed_offers.append(FailedOfferType(id=offer_id, error=str(e)))
            else:
                sent_offers.append(offer.id)

        return SendBerthSwitchOfferMutation(
            sent_offers=sent_offers, failed_offers=failed_offers
        )


class OrderApprovalInput(graphene.InputObjectType):
    order_id = graphene.ID(required=True)
    email = graphene.String(required=True)


class ApproveOrderMutation(graphene.ClientIDMutation):
    class Input:
        orders = graphene.List(OrderApprovalInput, required=True)
        due_date = graphene.Date(description="Defaults to the Order due date")
        profile_token = graphene.String(
            required=False, description="API token for Helsinki profile GraphQL API",
        )

    failed_orders = graphene.List(FailedOrderType, required=True)

    @classmethod
    @change_permission_required(
        Order,
        BerthLease,
        WinterStorageLease,
        BerthApplication,
        WinterStorageApplication,
    )
    def mutate_and_get_payload(cls, root, info, **input):
        failed_orders = []
        due_date = input.get("due_date", today().date() + relativedelta(weeks=2))
        profile_token = input.get("profile_token", None)

        for order_input in input.get("orders"):
            order_id = order_input.get("order_id")
            try:
                with transaction.atomic():
                    order = get_node_from_global_id(
                        info, order_id, only_type=OrderNode, nullable=False,
                    )
                    email = order_input.get("email")

                    profile = (
                        ProfileService(profile_token).get_profile(order.customer.id)
                        if profile_token
                        else None
                    )
                    approve_order(order, email, due_date, profile, info.context)
            except (
                AnymailError,
                OSError,
                Order.DoesNotExist,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                failed_orders.append(FailedOrderType(id=order_id, error=str(e)))

        return ApproveOrderMutation(failed_orders=failed_orders)


class ResendOrderMutation(graphene.ClientIDMutation):
    class Input:
        orders = graphene.List(graphene.ID, required=True)
        due_date = graphene.Date(description="Defaults to the Order due date")
        profile_token = graphene.String(
            description="API token for Helsinki profile GraphQL API",
        )

    sent_orders = graphene.List(graphene.NonNull(graphene.ID), required=True)
    failed_orders = graphene.List(graphene.NonNull(FailedOrderType), required=True)

    @classmethod
    @change_permission_required(Order)
    def mutate_and_get_payload(cls, root, info, orders, **input):
        due_date = input.pop("due_date", None)

        failed_orders = []
        sent_orders = []

        profile_token = input.get("profile_token")

        for order_id in orders:
            order = get_node_from_global_id(
                info, order_id, only_type=OrderNode, nullable=False
            )

            try:
                with transaction.atomic():
                    prepare_for_resending(order)

                    if order.lease.status != LeaseStatus.OFFERED:
                        raise ValidationError(
                            _(
                                "Cannot resend an invoice for a lease that is not currently offered."
                            )
                        )

                    if profile_token:
                        # order.customer_email and order.customer_phone could be stale, if contact
                        # info in profile service has been changed.
                        profile = fetch_order_profile(order, profile_token)
                        update_order_from_profile(order, profile)

                    elif not order.customer_email and not order.customer_phone:
                        failed_orders.append(
                            FailedOrderType(
                                id=order_id,
                                error=_(
                                    "Profile token is required if an order does not previously have email or phone."
                                ),
                            )
                        )
                        continue
                    resend_order(order, due_date, info.context)
            except (
                AnymailError,
                OSError,
                Order.DoesNotExist,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                failed_orders.append(FailedOrderType(id=order_id, error=str(e)))
            else:
                sent_orders.append(order.id)

        return ResendOrderMutation(sent_orders=sent_orders, failed_orders=failed_orders)


class RefundOrderMutation(graphene.ClientIDMutation):
    class Input:
        order_id = graphene.ID(required=True)
        profile_token = graphene.String(
            required=False, description="API token for Helsinki profile GraphQL API",
        )

    order_refund = graphene.Field(OrderRefundNode, required=True)

    @classmethod
    @change_permission_required(
        Order, BerthLease, WinterStorageLease,
    )
    def mutate_and_get_payload(cls, root, info, order_id, **input):
        profile_token = input.get("profile_token", None)
        try:
            order = get_node_from_global_id(info, order_id, OrderNode, nullable=False)
            refund = get_payment_provider(info.context).initiate_refund(order)

            if profile_token:
                # order.customer_email and order.customer_phone could be stale, if contact
                # info in profile service has been changed.
                profile = fetch_order_profile(order, profile_token)
                update_order_from_profile(order, profile)

            send_refund_notice(order)
        except (
            AnymailError,
            OSError,
            Order.DoesNotExist,
            ValidationError,
            VenepaikkaGraphQLError,
            VenepaikkaPaymentError,
        ) as e:
            # If there's an error with either the validated data or the VismaPay service
            raise VenepaikkaGraphQLError(str(e)) from e

        return RefundOrderMutation(order_refund=refund)


class CreateBerthSwitchOfferMutation(graphene.ClientIDMutation):
    class Input:
        # Required fields
        application_id = graphene.ID(required=True)
        new_berth_id = graphene.ID(required=True)
        # Optional fields
        old_lease_id = graphene.ID(
            description="If provided, it will ignore the `Berth Switch` from the application "
            "and force this lease to be terminated when the offer is accepted"
        )
        due_date = graphene.Date()
        profile_token = graphene.String(
            description="API token for Helsinki profile GraphQL API",
        )

    berth_switch_offer = graphene.Field(BerthSwitchOfferNode, required=True)

    @staticmethod
    def get_old_lease(application: BerthApplication) -> BerthLease:
        # Based on the information filled by the customer on the switch application,
        # we retrieve the corresponding lease on the current season
        return BerthLease.objects.get(
            customer=application.customer,
            berth=application.berth_switch.berth,
            status=LeaseStatus.PAID,
            start_date=calculate_season_start_date(),
            end_date=calculate_season_end_date(),
        )

    @classmethod
    @add_permission_required(BerthSwitchOffer)
    def mutate_and_get_payload(cls, root, info, application_id, new_berth_id, **input):
        try:
            application = get_node_from_global_id(
                info, application_id, only_type=BerthApplicationNode, nullable=False
            )

            if not application.customer:
                raise VenepaikkaGraphQLError(
                    _("Application must be connected to a customer")
                )

            if not application.berth_switch:
                raise VenepaikkaGraphQLError(
                    _("Application must be a switch application")
                )

            new_berth = get_node_from_global_id(
                info, new_berth_id, only_type=BerthNode, nullable=False
            )
            if old_lease_id := input.get("old_lease_id"):
                old_lease = get_node_from_global_id(
                    info, old_lease_id, only_type=BerthLeaseNode, nullable=False
                )
            else:
                old_lease = cls.get_old_lease(application)
        except BerthApplication.DoesNotExist as e:
            raise VenepaikkaGraphQLError(str(e)) from e
        except (BerthLease.DoesNotExist, Berth.DoesNotExist) as e:
            raise VenepaikkaGraphQLError("NO_LEASE") from e

        try:
            offer = BerthSwitchOffer.objects.create(
                customer=old_lease.customer,
                application=application,
                lease=old_lease,
                berth=new_berth,
            )
            if profile_token := input.get("profile_token"):
                offer.update_from_profile(profile_token)
            application.status = ApplicationStatus.OFFER_GENERATED
            application.save()

        except ValidationError as e:
            raise VenepaikkaGraphQLError(str(e)) from e

        return CreateBerthSwitchOfferMutation(berth_switch_offer=offer)


class AcceptBerthSwitchOfferMutation(graphene.ClientIDMutation):
    class Input:
        offer_number = graphene.String(required=True)
        is_accepted = graphene.Boolean(required=True)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, offer_number, is_accepted, **input):
        offer = BerthSwitchOffer.objects.get(offer_number=offer_number)
        if is_accepted:
            if offer.status == OfferStatus.ACCEPTED:
                # do not proceed with db updates in exchange_berth_for_lease
                raise VenepaikkaGraphQLError(_("Offer is already accepted"))
            offer.set_status(OfferStatus.ACCEPTED)

            old_lease, new_lease = exchange_berth_for_lease(
                old_lease=offer.lease,
                new_berth=offer.berth,
                switch_date=max(today().date(), offer.lease.start_date),
                old_lease_comment=_("Lease terminated due to a berth switch offer"),
                new_lease_comment=_("Lease created from a berth switch offer"),
            )
            new_lease.application = offer.application
            new_lease.save()
            if old_lease.order:
                new_lease.orders.add(old_lease.order)
        else:
            # Reject offer
            offer.set_status(OfferStatus.REJECTED)

        return AcceptBerthSwitchOfferMutation()


class OfferInput:
    # currently the application, berth and lease of the Offer can not be changed
    status = OfferStatusEnum()
    due_date = graphene.Date()


class UpdateBerthSwitchOfferMutation(graphene.ClientIDMutation):
    class Input(OfferInput):
        id = graphene.ID(required=True)

    berth_switch_offer = graphene.Field(BerthSwitchOfferNode)

    @classmethod
    @change_permission_required(BerthSwitchOffer)
    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        offer = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthSwitchOfferNode, nullable=False
        )
        try:
            # do not assign status directly on the object, use proper state transition through set_status
            new_status = input.pop("status", None)
            update_object(offer, input)
            if new_status:
                offer.set_status(new_status, _("Manually updated by admin"))

        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateBerthSwitchOfferMutation(berth_switch_offer=offer)


class Mutation:
    create_berth_product = CreateBerthProductMutation.Field(
        description="Creates a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
    )
    update_berth_product = UpdateBerthProductMutation.Field(
        description="Updates a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `BerthProduct` doesn't exist"
    )
    delete_berth_product = DeleteBerthProductMutation.Field(
        description="Deletes a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `BerthProduct` doesn't exist"
    )

    create_winter_storage_product = CreateWinterStorageProductMutation.Field(
        description="Creates a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
    )
    update_winter_storage_product = UpdateWinterStorageProductMutation.Field(
        description="Updates a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `WinterStorageProduct` doesn't exist"
    )
    delete_winter_storage_product = DeleteWinterStorageProductMutation.Field(
        description="Deletes a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `WinterStorageProduct` doesn't exist"
    )

    create_additional_product = CreateAdditionalProductMutation.Field(
        description="Deletes a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
    )
    update_additional_product = UpdateAdditionalProductMutation.Field(
        description="Updates a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `AdditionalProduct` doesn't exist"
    )
    delete_additional_product = DeleteAdditionalProductMutation.Field(
        description="Deletes a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `AdditionalProduct` doesn't exist"
    )

    create_order = CreateOrderMutation.Field(
        description="Creates an `Order` object and the `OrderLine`s according to the place associated."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `customer` does not exist"
        "\n* A `BerthProduct` and a `WinterStorageLease` are passed"
        "\n* A `WinterStorageProduct` and a `BerthLease` are passed"
        "\n* The `lease` provided belongs to a different `customer`"
        "\n* An invalid `product` (neither `BerthProduct` nor `WinterStorageProduct`) is passed"
    )
    create_additional_product_order = CreateAdditionalProductOrderMutation.Field(
        description="Creates an `Order` object and the `OrderLine`s for only one additional product."
    )
    update_orders = UpdateOrdersMutation.Field(
        description="Updates an `Order` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` does not exist"
        "\n* A different `product` is trying to be assigned"
        "\n* A different `lease` is trying to be assigned"
    )
    delete_order = DeleteOrderMutation.Field(
        description="Deletes an `Order` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` does not exist"
    )

    create_order_line = CreateOrderLineMutation.Field(
        description="Creates an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` doesn't exist"
        "\n* The passed `product` doesn't exist"
    )
    update_order_line = UpdateOrderLineMutation.Field(
        description="Updates an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `OrderLine` does not exist"
        "\n* A different `order` is trying to be assigned"
        "\n* A different `product` is trying to be assigned"
    )
    delete_order_line = DeleteOrderLineMutation.Field(
        description="Deletes an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `OrderLine` does not exist"
    )

    approve_orders = ApproveOrderMutation.Field(
        description="Approves a list of Orders."
        "\n\nIt receives a list of `GlobalID`s with the email to which the notification will be sent. "
        "It also receives a `dueDate` for the orders. If no due date is passed, "
        "it will take the due date set on the order."
        "\n\nIt returns a list of failed order ids and the reason why they failed."
        "\n\n**Requires permissions** to update orders, leases, and applications."
        "\n\nErrors:"
        "\n* The passed `order` does not exist"
        "\n* An `order.lease` or `order.lease.application` have an invalid status transition"
        "\n* There's an error when sending the email"
    )

    resend_order = ResendOrderMutation.Field(
        description="Resends the specified order notice."
        "\n\nUpdates order due date and price if the underlying product has been changed, "
        "and resends the payment email to the customer."
        "\n\nIt returns the updated order."
        "\n\n**Requires permissions** to update orders."
        "\n\nErrors:"
        "\n* The passed order must have a lease in status OFFERED"
    )
    refund_order = RefundOrderMutation.Field(
        description="Refunds the specified order."
        "\n\nStarts the refund process through VismaPay. It returns the `RefundOrder` object."
        "\n\n**Requires permissions** to update orders."
        "\n\nErrors:"
        "\n* The passed order must be in `PAID` status"
    )

    create_berth_switch_offer = CreateBerthSwitchOfferMutation.Field(
        description="Creates an offer for a berth switch application."
        "\n\nIt expects an application with a `BerthSwitch`. From there, it takes the harbor, pier, and berth "
        "and tries to find the lease associated to the customer, and creates the offer. "
        "\n\nIf the `oldLeaseId` is passed, it will ignore that matching and it will automatically use that lease."
        "\n\n**Requires permissions** to create offers."
        "\n\nErrors:"
        "\n* The passed application is not connected to a customer"
        "\n* The passed application is not a switch application"
        "\n* No associated lease could be find for the switch application"
        "\n* The related lease must be in `PAID` status"
    )
    update_berth_switch_offer = UpdateBerthSwitchOfferMutation.Field(
        description="Updates a berth switch offer."
        "\n\nCurrently it is possible to update the status and dueDate fields of the Offer."
        "\n\ndueDate must be a valid date, it is not possible to remove dueDate once it is set."
        "\n\n**Requires permissions** to edit offers."
        "\n\nErrors:"
        "\n* State transition is not allowed"
    )

    send_berth_switch_offer = SendBerthSwitchOfferMutation.Field(
        description="Sends an offer for a berth switch to the customer via email and SMS."
        "\n\nResending a previously sent offer is possible."
        "\n\nOffer status is changed to PENDING and application status is changed to OFFER_SENT."
        "\n\nIf profile_token is given, then customer's contact information stored in offer is refreshed from "
        "\n\nthe city profile service."
        "\n\n**Requires permissions** to edit offers."
        "\n\nErrors:"
        "\n* The offer is not DRAFTED or OFFERED"
        "\n* Customer's contact information is not available"
    )
    accept_berth_switch_offer = AcceptBerthSwitchOfferMutation.Field(
        description="Accepts or rejects an offer for a berth switch application."
        "\n\nIf the offer is accepted, it will terminate the old lease and create a new lease with the new berth."
        "\n\nIf the offer is rejected, nothing is created and the related lease stays as is."
        "\n\nErrors:"
        "\n\n**Requires permissions** to add and change berth leases and to change berth switch offers."
        "\n\nErrors:"
        "\n* The passed berth switch offer ID doesn't exist"
        "\n* The related lease must be in `PAID` status"
    )

    confirm_payment = ConfirmPaymentMutation.Field()
    cancel_order = CancelOrderMutation.Field()
