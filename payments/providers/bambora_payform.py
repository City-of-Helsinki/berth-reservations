import hashlib
import hmac
import logging
from datetime import datetime
from typing import Iterable

import requests
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.utils.translation import gettext_lazy as _, override
from requests.exceptions import RequestException

from leases.enums import LeaseStatus
from leases.utils import terminate_lease

from ..enums import OrderRefundStatus, OrderStatus, OrderType
from ..exceptions import (
    DuplicateOrderError,
    ExpiredOrderError,
    OrderStatusTransitionError,
    PayloadValidationError,
    ServiceUnavailableError,
    UnknownReturnCodeError,
)
from ..models import (
    AdditionalProduct,
    BerthProduct,
    Order,
    OrderLine,
    OrderRefund,
    OrderToken,
)
from ..utils import get_talpa_product_id, price_as_fractional_int, resolve_area
from .base import PaymentProvider

logger = logging.getLogger(__name__)

# Keys the provider expects to find in the config
VENE_PAYMENTS_BAMBORA_API_URL = "VENE_PAYMENTS_BAMBORA_API_URL"
VENE_PAYMENTS_BAMBORA_API_KEY = "VENE_PAYMENTS_BAMBORA_API_KEY"
VENE_PAYMENTS_BAMBORA_API_SECRET = "VENE_PAYMENTS_BAMBORA_API_SECRET"
VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS = "VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS"


class BamboraPayformProvider(PaymentProvider):
    """Bambora Payform specific integration utilities and configuration
    testing docs: https://payform.bambora.com/docs/web_payments/?page=testing
    api reference: https://payform.bambora.com/docs/web_payments/?page=full-api-reference
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_payment_api = self.config.get(VENE_PAYMENTS_BAMBORA_API_URL)
        self.url_payment_auth = "{}/auth_payment".format(self.url_payment_api)
        self.url_payment_token = "{}/token/{{token}}".format(self.url_payment_api)
        self.url_refund = "{}/create_refund".format(self.url_payment_api)

    @staticmethod
    def get_config_template() -> dict:
        """Keys and value types what Bambora requires from environment"""
        return {
            VENE_PAYMENTS_BAMBORA_API_URL: (str, "https://payform.bambora.com/pbwapi"),
            VENE_PAYMENTS_BAMBORA_API_KEY: str,
            VENE_PAYMENTS_BAMBORA_API_SECRET: str,
            VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS: list,
        }

    def initiate_payment(self, order: Order) -> str:
        """Initiate payment by constructing the payload with necessary items"""
        language = (
            order.lease.application.language
            if hasattr(order, "lease") and order.lease.application
            else settings.LANGUAGE_CODE
        )

        # Bambora only allows for the token to live up to 7 days since the order has been created,
        # so we make the token valid until midnight on the 6th day to be sure that we can
        # always get the expiration at the same hour
        #   "Allowed values are 1 hour from current timestamp to 7 days from current timestamp."
        #   "Default value is 1 hour from current timestamp."
        token_valid_until = datetime.combine(
            today() + relativedelta(days=6), datetime.max.time()
        )

        order_token = (
            order.tokens.exclude(token__isnull=True)
            .exclude(token__iexact="")
            .order_by("-created_at")
            .first()
        )

        # Check if there's a valid OrderToken for the current order to avoid
        # generating duplicate orders. If there's a token,
        if order_token and order_token.is_valid:
            return self.url_payment_token.format(token=order_token.token)

        # If the token found already has a value for the token (i.e. not an empty token=""),
        # it means that it's invalid and a new one should be generated.
        # Otherwise, we invalidate the previous tokens and generate a new one.
        order.invalidate_tokens()
        order_token = OrderToken.objects.create(
            order=order, valid_until=token_valid_until
        )

        payload = {
            "version": "w3.1",
            "api_key": self.config.get(VENE_PAYMENTS_BAMBORA_API_KEY),
            "payment_method": {
                "type": "e-payment",
                "return_url": self.get_success_url(lang=language),
                "notify_url": self.get_notify_url(),
                "selected": self.config.get(VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS),
                "token_valid_until": token_valid_until.timestamp(),
            },
            "currency": "EUR",
            "order_number": f"{order.order_number}-{order_token.created_at.timestamp()}",
        }

        self.payload_add_products(payload, order, language)
        self.payload_add_customer(payload, order)
        self.payload_add_auth_code(payload)

        try:
            r = requests.post(self.url_payment_auth, json=payload, timeout=60)
            r.raise_for_status()
            return self.handle_initiate_payment(
                order, r.json(), order_token=order_token
            )
        except RequestException as e:
            raise ServiceUnavailableError(_("Payment service is unreachable")) from e

    def handle_initiate_payment(
        self, order: Order, response, order_token: OrderToken = None
    ) -> str:
        """Handling the Bambora payment auth response"""
        result = response["result"]
        if order.status == OrderStatus.EXPIRED:
            raise ExpiredOrderError(_("Order has already expired"))
        if result == 0:
            # Create the URL where user is redirected to complete the payment
            # Append "?minified" to get a stripped version of the payment page
            token = response["token"]

            if order_token:
                order_token.token = token
                order_token.save()

            return self.url_payment_token.format(token=token)
        elif result == 1:
            raise PayloadValidationError(
                f"{_('Payment payload data validation failed: ')} {' '.join(response['errors'])}"
            )
        elif result == 2:
            raise DuplicateOrderError(_("Order with the same ID already exists"))
        elif result == 10:
            raise ServiceUnavailableError(_("Payment service is down for maintenance"))
        else:
            raise UnknownReturnCodeError(
                f"{_('Return code was not recognized: ')} {result}"
            )

    def payload_add_products(self, payload: dict, order: Order, language: str):
        """Attach info of bought products to payload

        Order lines that contain bought products are retrieved through order"""
        order_lines: [OrderLine] = OrderLine.objects.filter(order=order.id)
        items: [dict] = []

        area = resolve_area(order)

        # Additional product orders doesn't have berth product
        if hasattr(order, "product") and order.product:
            product = order.product
            int_tax = int(order.tax_percentage)
            assert (
                int_tax == product.tax_percentage
            )  # make sure the tax is a whole number
            with override(language):
                lease = order.lease
                place = (
                    lease.berth
                    if hasattr(lease, "berth")
                    else lease.place
                    if hasattr(lease, "place") and lease.place
                    else lease.section
                    if hasattr(lease, "section") and lease.section
                    else area
                )
                product_name = f"{product.name}: {place}"
            items.append(
                {
                    "id": get_talpa_product_id(product.id, area),
                    "title": product_name,
                    "price": price_as_fractional_int(order.price),
                    "pretax_price": price_as_fractional_int(order.pretax_price),
                    "tax": int_tax,
                    "count": 1,
                    "type": 1,
                }
            )

        for order_line in order_lines:
            product: AdditionalProduct = order_line.product
            int_tax = int(product.tax_percentage)
            assert (
                int_tax == product.tax_percentage
            )  # make sure the tax is a whole number
            with override(language):
                product_name = product.name
            items.append(
                {
                    "id": get_talpa_product_id(product.id, area),
                    "title": product_name,
                    "price": price_as_fractional_int(order_line.price),
                    "pretax_price": price_as_fractional_int(order_line.pretax_price),
                    "tax": int_tax,
                    "count": order_line.quantity,
                    "type": 1,
                }
            )
        payload["amount"] = price_as_fractional_int(order.total_price)
        payload["products"] = items

    def payload_add_customer(self, payload: dict, order: Order):
        """Attach customer data to payload"""
        if hasattr(order, "lease") and order.lease.application:
            application = order.lease.application
            payload.update(
                {
                    "email": application.email.strip(),
                    "customer": {
                        "firstname": application.first_name.capitalize(),
                        "lastname": application.last_name.capitalize(),
                        "email": application.email.strip(),
                        "address_street": application.address,
                        "address_zip": application.zip_code,
                        "address_city": application.municipality.capitalize(),
                    },
                }
            )
        else:
            payload.update(
                {
                    "email": order.customer_email.strip(),
                    "customer": {
                        "firstname": order.customer_first_name.capitalize()
                        if order.customer_first_name
                        else "",
                        "lastname": order.customer_last_name.capitalize()
                        if order.customer_last_name
                        else "",
                        "email": order.customer_email.strip(),
                        "address_street": order.customer_address,
                        "address_zip": order.customer_zip_code,
                        "address_city": order.customer_city.capitalize()
                        if order.customer_city
                        else "",
                    },
                }
            )

    def payload_add_auth_code(self, payload: dict):
        """Construct auth code string and hash it into payload"""
        data = "{}|{}".format(payload["api_key"], payload["order_number"])
        payload.update(authcode=self.calculate_auth_code(data))

    def initiate_refund(self, order: Order) -> OrderRefund:
        # Orders which are PAID_MANUALLY may not have an entry in Bambora,
        # so we can't guarantee that the refund will be executed
        if (order.status != OrderStatus.PAID) or (
            hasattr(order, "lease") and order.lease.status != LeaseStatus.PAID
        ):
            raise ValidationError(_("Cannot refund an order that is not paid"))

        order_token = (
            order.tokens.exclude(token__isnull=True, token__iexact="")
            .order_by("-created_at")
            .first()
        )

        if not order_token:
            raise ValidationError(
                _("Cannot refund an order that has not been paid through VismaPay")
            )

        refund_amount = order.total_price
        payload = {
            "version": "w3.1",
            "api_key": self.config.get(VENE_PAYMENTS_BAMBORA_API_KEY),
            "amount": price_as_fractional_int(refund_amount),
            "notify_url": self.get_notify_refund_url(),
            "email": order.customer_email,
            "order_number": f"{order.order_number}-{order_token.created_at.timestamp()}",
        }
        self.payload_add_auth_code(payload)

        try:
            r = requests.post(self.url_refund, json=payload, timeout=60)
            r.raise_for_status()
            response = r.json()
            result = response["result"]

            if result == 1:
                raise PayloadValidationError(
                    f"{_('Payment payload data validation failed: ')} {' '.join(response['errors'])}"
                )
            elif result == 10:
                raise ServiceUnavailableError(
                    _("Payment service is down for maintenance")
                )

            return OrderRefund.objects.create(
                order=order, amount=refund_amount, refund_id=str(response["refund_id"])
            )
        except RequestException as e:
            raise ServiceUnavailableError(_("Payment service is unreachable")) from e

    def handle_notify_refund_request(self) -> HttpResponse:
        request = self.request
        logger.debug(
            "Handling Bambora notify refund request, params: {}.".format(request.GET)
        )

        refund_id = request.GET.get("REFUND_ID")

        try:
            refund = OrderRefund.objects.get(refund_id=refund_id)
            order = refund.order
        except OrderRefund.DoesNotExist:
            # Target order might be deleted after posting but before the notify arrives
            logger.warning("Notify: OrderRefund does not exist.")
            return HttpResponse(status=204)

        order.invalidate_tokens()

        if not self.check_new_refund_authcode(request):
            return HttpResponse(status=204)

        return_code = request.GET.get("RETURN_CODE")
        if return_code == "0":
            logger.debug("Notify: Refund completed successfully.")
            try:
                refund.set_status(
                    OrderRefundStatus.ACCEPTED,
                    "Code 0 (refund succeeded) in Bambora Payform notify refund request.",
                )
                order.set_status(
                    OrderStatus.REFUNDED,
                    "Code 0 (refund succeeded) in Bambora Payform notify refund request.",
                )
                if refund.amount == order.total_price and order.lease:
                    terminate_lease(order.lease, send_notice=False)
            except OrderStatusTransitionError as oste:
                logger.warning(oste)
        elif return_code == "1":
            # Don't cancel the order
            refund.set_status(
                OrderRefundStatus.REJECTED,
                "Code 1 (refund rejected) in Bambora Payform notify refund request.",
            )
            logger.debug("Notify: Refund failed.")
        else:
            logger.debug('Notify: Incorrect RETURN_CODE "{}".'.format(return_code))

        return HttpResponse(status=204)

    def calculate_auth_code(self, data) -> str:
        """Calculate a hmac sha256 out of some data string"""
        return (
            hmac.new(
                bytes(self.config.get(VENE_PAYMENTS_BAMBORA_API_SECRET), "latin-1"),
                msg=bytes(data, "latin-1"),
                digestmod=hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

    def check_authcode_params(self, request: HttpRequest, params: Iterable[str]):
        """Validate that success/notify payload authcode matches"""
        is_valid = True
        auth_code_calculation_values = [
            request.GET[param_name]
            for param_name in params
            if param_name in request.GET
        ]
        correct_auth_code = self.calculate_auth_code(
            "|".join(auth_code_calculation_values)
        )
        auth_code = request.GET["AUTHCODE"]
        if not hmac.compare_digest(auth_code, correct_auth_code):
            logger.warning('Incorrect auth code "{}".'.format(auth_code))
            is_valid = False
        return is_valid

    def check_new_payment_authcode(self, request: HttpRequest):
        """Validate that success/notify payload authcode matches"""
        return self.check_authcode_params(
            request,
            ("RETURN_CODE", "ORDER_NUMBER", "SETTLED", "CONTACT_ID", "INCIDENT_ID",),
        )

    def check_new_refund_authcode(self, request: HttpRequest):
        """Validate that refund notify payload authcode matches"""
        return self.check_authcode_params(request, ("RETURN_CODE", "REFUND_ID",))

    def handle_success_request(self) -> HttpResponse:  # noqa: C901
        """Handle the payform response after user has completed the payment flow in normal fashion"""
        request = self.request
        logger.debug(
            "Handling Bambora user return request, params: {}.".format(request.GET)
        )

        order_number, _timestamp = request.GET.get("ORDER_NUMBER", "-").split("-")
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            logger.warning("Order does not exist.")
            return self.ui_redirect_failure()

        order.invalidate_tokens()

        if not self.check_new_payment_authcode(request):
            return self.ui_redirect_failure()

        return_code = request.GET["RETURN_CODE"]
        if return_code == "0":
            logger.debug("Payment completed successfully.")
            try:
                order.set_status(
                    OrderStatus.PAID,
                    "Code 0 (payment succeeded) in Bambora Payform success request.",
                )
                return self.ui_redirect_success()
            except OrderStatusTransitionError as oste:
                logger.warning(oste)
                order.create_log_entry(
                    "Code 0 (payment succeeded) in Bambora Payform success request."
                )
                return self.ui_redirect_failure()
        elif return_code == "1":
            logger.debug("Payment failed.")
            return self.ui_redirect_failure()
        elif return_code == "4":
            logger.debug("Transaction status could not be updated.")
            order.create_log_entry(
                "Code 4: Transaction status could not be updated. Use the merchant UI to resolve."
            )
            return self.ui_redirect_failure()
        elif return_code == "10":
            logger.debug("Maintenance break.")
            order.create_log_entry("Code 10: Bambora Payform maintenance break")
            return self.ui_redirect_failure()
        else:
            logger.warning('Incorrect RETURN_CODE "{}".'.format(return_code))
            order.create_log_entry(
                'Bambora Payform incorrect return code "{}".'.format(return_code)
            )
            return self.ui_redirect_failure()

    def handle_notify_request(self):
        """Handle the asynchronous part of payform response

        Arrives some time after user has completed the payment flow or stopped it abruptly.
        Skips changing order status if it has been previously set. Although, according to
        Bambora's documentation, there are some cases where payment status might change
        from failed to successful, the reservation has probably been soft-cleaned up by then.

        Bambora expects 20x response to acknowledge the notify was received"""
        request = self.request
        logger.debug("Handling Bambora notify request, params: {}.".format(request.GET))

        order_number, _timestamp = request.GET.get("ORDER_NUMBER", "-").split("-")
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            # Target order might be deleted after posting but before the notify arrives
            logger.warning("Notify: Order does not exist.")
            return HttpResponse(status=204)

        order.invalidate_tokens()

        if not self.check_new_payment_authcode(request):
            return HttpResponse(status=204)

        return_code = request.GET["RETURN_CODE"]
        if return_code == "0":
            logger.debug("Notify: Payment completed successfully.")
            try:
                order.set_status(
                    OrderStatus.PAID,
                    "Code 0 (payment succeeded) in Bambora Payform notify request.",
                )
            except OrderStatusTransitionError as oste:
                logger.warning(oste)
        elif return_code == "1":
            # Don't cancel the order
            logger.debug("Notify: Payment failed.")
        else:
            logger.debug('Notify: Incorrect RETURN_CODE "{}".'.format(return_code))

        return HttpResponse(status=204)

    def ui_redirect_success(self, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a successful payment
        This should be used after a successful payment instead of the
        standard Django redirect.
        """
        ui_return_url = self.extract_ui_return_url()
        if ui_return_url:
            return self._redirect_to_ui(
                ui_return_url, "success", order, path="/payment-result"
            )
        else:
            return HttpResponse(
                content="Payment successful, but failed redirecting back to UI"
            )

    def ui_redirect_failure(self, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a failed payment
        This should be used after a failed payment instead of the
        standard Django redirect.
        """
        ui_return_url = self.extract_ui_return_url()
        if ui_return_url:
            return self._redirect_to_ui(
                ui_return_url, "failure", order, path="/payment-result"
            )
        else:
            return HttpResponseServerError(
                content="Payment failure and failed redirecting back to UI"
            )
