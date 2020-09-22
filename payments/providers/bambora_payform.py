import hashlib
import hmac
import logging
from datetime import datetime

import requests
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.utils.translation import gettext_lazy as _, override
from requests.exceptions import RequestException

from ..enums import OrderStatus
from ..exceptions import (
    DuplicateOrderError,
    ExpiredOrderError,
    MissingCustomerError,
    OrderStatusTransitionError,
    PayloadValidationError,
    ServiceUnavailableError,
    UnknownReturnCodeError,
)
from ..models import AdditionalProduct, Order, OrderLine
from ..utils import get_talpa_product_id, price_as_fractional_int
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

        payload = {
            "version": "w3.1",
            "api_key": self.config.get(VENE_PAYMENTS_BAMBORA_API_KEY),
            "payment_method": {
                "type": "e-payment",
                "return_url": self.get_success_url(
                    lang=order.lease.application.language
                ),
                "notify_url": self.get_notify_url(),
                "selected": self.config.get(VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS),
                "token_valid_until": datetime.combine(
                    order.due_date, datetime.max.time()
                ).timestamp(),
            },
            "currency": "EUR",
            "order_number": str(order.order_number),
        }

        self.payload_add_products(payload, order)
        self.payload_add_customer(payload, order)
        self.payload_add_auth_code(payload)

        try:
            r = requests.post(self.url_payment_auth, json=payload, timeout=60)
            r.raise_for_status()
            return self.handle_initiate_payment(order, r.json())
        except RequestException as e:
            raise ServiceUnavailableError(_("Payment service is unreachable")) from e

    def handle_initiate_payment(self, order: Order, response) -> str:
        """Handling the Bambora payment auth response"""
        result = response["result"]
        if order.status == OrderStatus.EXPIRED:
            raise ExpiredOrderError(_("Order has already expired"))
        if result == 0:
            # Create the URL where user is redirected to complete the payment
            # Append "?minified" to get a stripped version of the payment page
            return self.url_payment_token.format(token=response["token"])
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

    def payload_add_products(self, payload: dict, order: Order):
        """Attach info of bought products to payload

        Order lines that contain bought products are retrieved through order"""
        order_lines: [OrderLine] = OrderLine.objects.filter(order=order.id)
        items: [dict] = []

        area = None

        if hasattr(order, "product"):
            if hasattr(order.product, "harbor"):
                area = order.product.harbor
            elif hasattr(order.product, "winter_storage_area"):
                area = order.product.winter_storage_area

        product = order.product
        int_tax = int(order.tax_percentage)
        assert int_tax == product.tax_percentage  # make sure the tax is a whole number
        with override(order.lease.application.language):
            product_name = product.name
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
            with override(order.lease.application.language):
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
        if not order.lease or order.lease and not order.lease.application:
            raise MissingCustomerError(_("Order is not associated with a Lease"))

        application = order.lease.application

        payload.update(
            {
                "email": application.email,
                "customer": {
                    "firstname": application.first_name.capitalize(),
                    "lastname": application.last_name.capitalize(),
                    "email": application.email,
                    "address_street": application.address,
                    "address_zip": application.zip_code,
                    "address_city": application.municipality.capitalize(),
                },
            }
        )

    def payload_add_auth_code(self, payload: dict):
        """Construct auth code string and hash it into payload"""
        data = "{}|{}".format(payload["api_key"], payload["order_number"])
        payload.update(authcode=self.calculate_auth_code(data))

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

    def check_new_payment_authcode(self, request: HttpRequest):
        """Validate that success/notify payload authcode matches"""
        is_valid = True
        auth_code_calculation_values = [
            request.GET[param_name]
            for param_name in (
                "RETURN_CODE",
                "ORDER_NUMBER",
                "SETTLED",
                "CONTACT_ID",
                "INCIDENT_ID",
            )
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

    def handle_success_request(self) -> HttpResponse:  # noqa: C901
        """Handle the payform response after user has completed the payment flow in normal fashion"""
        request = self.request
        logger.debug(
            "Handling Bambora user return request, params: {}.".format(request.GET)
        )

        if not self.check_new_payment_authcode(request):
            return self.ui_redirect_failure()

        try:
            order = Order.objects.get(order_number=request.GET["ORDER_NUMBER"])
        except Order.DoesNotExist:
            logger.warning("Order does not exist.")
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
            try:
                order.set_status(
                    OrderStatus.REJECTED,
                    "Code 1 (payment rejected) in Bambora Payform success request.",
                )
                return self.ui_redirect_failure()
            except OrderStatusTransitionError as oste:
                logger.warning(oste)
                order.create_log_entry(
                    "Code 1 (payment rejected) in Bambora Payform success request."
                )
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

        if not self.check_new_payment_authcode(request):
            return HttpResponse(status=204)

        try:
            order = Order.objects.get(order_number=request.GET["ORDER_NUMBER"])
        except Order.DoesNotExist:
            # Target order might be deleted after posting but before the notify arrives
            logger.warning("Notify: Order does not exist.")
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
            logger.debug("Notify: Payment failed.")
            try:
                order.set_status(
                    OrderStatus.REJECTED,
                    "Code 1 (payment rejected) in Bambora Payform notify request.",
                )
            except OrderStatusTransitionError as oste:
                logger.warning(oste)
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