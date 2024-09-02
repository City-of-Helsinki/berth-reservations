import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.utils.translation import gettext_lazy as _, override
from requests import RequestException

from customers.utils import get_customer_hash
from resources.enums import BerthMooringType
from resources.models import (
    Berth,
    Harbor,
    WinterStorageArea,
    WinterStoragePlace,
    WinterStorageSection,
)
from utils.numbers import rounded

from ..consts import (
    TALPA_ECOM_WEBHOOK_EVENT_ORDER_CANCELLED,
    TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID,
    TALPA_ECOM_WEBHOOK_EVENT_TYPES,
)
from ..enums import OrderStatus
from ..exceptions import (
    MissingOrderIDError,
    OrderStatusTransitionError,
    RequestValidationFailedError,
    ServiceUnavailableError,
    UnknownWebhookEventError,
)
from ..models import Order, OrderLine
from ..utils import resolve_area, resolve_order_place, resolve_product_talpa_ecom_id
from .base import PaymentProvider

logger = logging.getLogger(__name__)

VENE_PAYMENTS_TALPA_ECOM_PAYMENT_API_URL = "VENE_PAYMENTS_TALPA_ECOM_PAYMENT_API_URL"
VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL = "VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL"
VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL = "VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL"
VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE = "VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE"


OrderIsh = Union[Order, OrderLine]


@dataclass
class TalpaEComPaymentDetails:
    payment_id: str
    namespace: str
    order_id: str
    user_id: str
    status: str
    payment_method: str
    payment_type: str
    total_excl_tax: Decimal
    total: Decimal
    tax_amount: Decimal
    description: Optional[str]
    additional_info: str
    token: str
    timestamp: str
    payment_method_label: str

    PAYMENT_CREATED = "payment_created"
    PAYMENT_PAID = "payment_paid_online"
    PAYMENT_CANCELLED = "payment_cancelled"

    def __init__(self, payment_dict: dict):
        self.payment_id = payment_dict.get("paymentId", "")
        self.namespace = payment_dict.get("namespace", "")
        self.order_id = payment_dict.get("orderId", "")
        self.user_id = payment_dict.get("userId", "")
        self.status = payment_dict.get("status", "")
        self.payment_method = payment_dict.get("paymentMethod", "")
        self.payment_type = payment_dict.get("paymentType", "")
        self.total_excl_tax = Decimal(payment_dict.get("totalExclTax", 0))
        self.total = Decimal(payment_dict.get("total", 0))
        self.tax_amount = Decimal(payment_dict.get("taxAmount", 0))
        self.additional_info = payment_dict.get("additionalInfo", "")
        self.description = payment_dict.get("description", None)
        self.token = payment_dict.get("token", "")
        self.timestamp = payment_dict.get("timestamp", "")
        self.payment_method_label = payment_dict.get("paymentMethodLabel", "")


class TalpaEComProvider(PaymentProvider):
    """Talpa eCommerce Platform specific integration utilities and configuration."""

    ui_return_url_param_name = "VENE_UI_RETURN_URL"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        checkout_url: str = self.config.get(
            VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL, ""
        ).rstrip("/")

        self.url_order_experience_api = self.config.get(
            VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL, ""
        )
        self.url_payment_experience_api = self.config.get(
            VENE_PAYMENTS_TALPA_ECOM_PAYMENT_API_URL, ""
        )
        self.url_checkout = f"{checkout_url}/{{talpa_ecom_id}}?user={{user_hash}}"
        self.namespace = self.config.get(VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE)

    @staticmethod
    def get_config_template() -> dict:
        """Keys and value types what Talpa eCom requires from environment"""
        return {
            VENE_PAYMENTS_TALPA_ECOM_PAYMENT_API_URL: (
                str,
                "https://checkout.api.hel.fi/v1/payment/",
            ),
            VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL: (
                str,
                "https://checkout.api.hel.fi/v1/order/",
            ),
            VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL: (str, "https://checkout.hel.fi/"),
            VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE: (str, "venepaikat"),
        }

    def initiate_payment(self, order: Order) -> str:
        """Initiate payment by creating an Order on the Talpa eCom service"""
        language = (
            order.lease.application.language
            if hasattr(order, "lease") and order.lease.application
            else settings.LANGUAGE_CODE
        )
        user_hash = get_customer_hash(order.customer)

        headers = {"user": user_hash}

        payload = {
            "namespace": self.config.get(VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE),
            "user": user_hash,
        }

        self.payload_add_customer(payload, order)
        self.payload_add_products(payload, order, language)

        try:
            r = requests.post(
                self.url_order_experience_api, json=payload, headers=headers, timeout=60
            )
            r.raise_for_status()
            resp = r.json()
            return self.handle_initiate_payment(order, resp)
        except RequestException as e:
            if e.response is not None and (data := e.response.json()):
                errors = data.get("errors", [])
                messages = "\n".join([error.get("message", "") for error in errors])
                raise RequestValidationFailedError(messages)

            raise ServiceUnavailableError(_("Payment service is unreachable")) from e

    def handle_initiate_payment(self, order, response) -> str:
        if errors := response.get("errors", []):
            messages = "\n".join([error.get("message", "") for error in errors])
            raise RequestValidationFailedError(messages)

        if talpa_order_id := response.get("orderId"):
            order.talpa_ecom_id = talpa_order_id
            order.save(update_fields=["talpa_ecom_id"])
        else:
            raise MissingOrderIDError(_("Order did not contain an id"))

        return self.url_checkout.format(
            talpa_ecom_id=talpa_order_id,
            user_hash=get_customer_hash(order.customer),
        )

    def payload_add_products(self, payload: dict, order: Order, language: str):
        """Attach info of bought products to payload

        Order lines that contain bought products are retrieved through order"""
        order_lines: [OrderLine] = order.order_lines.all()
        payload["items"] = []

        area = resolve_area(order)

        # Additional product orders doesn't have berth product
        if hasattr(order, "product") and order.product:
            self.payload_add_place_product(payload, order, area, language)

        for order_line in order_lines:
            with override(language):
                product_name = str(order_line.product.name)
            self.payload_add_to_items(payload, order_line, area, product_name, [])

        payload["priceNet"] = rounded(order.total_pretax_price, as_string=True)
        payload["priceTotal"] = rounded(order.total_price, as_string=True)
        payload["priceVat"] = str(
            rounded(order.total_price) - rounded(order.total_pretax_price)
        )

    def payload_add_to_items(
        self,
        payload: dict,
        item: OrderIsh,
        area: Optional[Union[Harbor, WinterStorageArea]],
        product_name: str,
        meta: list = None,
    ):
        product = item.product

        payload["items"].append(
            {
                "productId": resolve_product_talpa_ecom_id(product, area),
                "quantity": 1,
                "productName": str(product_name),
                "unit": "pcs",
                "rowPriceNet": rounded(item.pretax_price, as_string=True),
                "rowPriceVat": str(rounded(item.price) - rounded(item.pretax_price)),
                "rowPriceTotal": rounded(item.price, as_string=True),
                "vatPercentage": rounded(
                    item.tax_percentage,
                    decimals=0,
                    round_to_nearest=1,
                    as_string=True,
                ),
                "priceNet": rounded(item.pretax_price, as_string=True),
                "priceVat": str(rounded(item.price) - rounded(item.pretax_price)),
                "priceGross": rounded(item.price, as_string=True),
                "meta": meta.copy() or [],
            },
        )

    def payload_add_place_product(
        self,
        payload: dict,
        order: Order,
        area: Optional[Union[Harbor, WinterStorageArea]],
        language: str,
    ):
        # https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement
        # "The current code generator emits no code for an assert
        # statement when optimization is requested at compile time."
        assert order.tax_percentage == order.product.tax_percentage

        with override(language):
            lease = order.lease
            place = resolve_order_place(lease) or area
            place_name = str(place)
            area_address = area.safe_translation_getter("street_address", language)

            product_name = None
            width = None
            length = None
            mooring_type = None

            if isinstance(place, Berth):
                product_name = _("Berth product")
                width = place.berth_type.width
                length = place.berth_type.length
                mooring_type = BerthMooringType(place.berth_type.mooring_type).label
            elif isinstance(place, WinterStoragePlace):
                product_name = _("Winter storage place product")
                width = place.place_type.width
                length = place.place_type.length
            elif isinstance(place, WinterStorageSection):
                product_name = _("Winter storage product")
            else:
                raise ValidationError(_("A product order should have a specific place"))

        meta_fields = [
            {
                "key": "placeLocation",
                "value": area_address,
                "label": place_name,
                "visibleInCheckout": True,
                "ordinal": "1",
            },
        ]

        if width:
            meta_fields.append(
                {
                    "key": "placeWidth",
                    "value": f"{_('width (m)').capitalize()}: {width}",
                    "visibleInCheckout": True,
                    "ordinal": "2",
                }
            )
        if length:
            meta_fields.append(
                {
                    "key": "placeLength",
                    "value": f"{_('length (m)').capitalize()}: {length}",
                    "visibleInCheckout": True,
                    "ordinal": "3",
                }
            )
        if mooring_type:
            meta_fields.append(
                {
                    "key": "placeMooring",
                    "value": f"{_('Mooring')}: {mooring_type}",
                    "visibleInCheckout": True,
                    "ordinal": "4",
                }
            )

        self.payload_add_to_items(payload, order, area, product_name, meta_fields)

    def payload_add_customer(self, payload: dict, order: Order):
        # Order customer information will have higher priority since it's fetched from
        # Profile everytime
        customer = {}
        phone = ""
        phone_regex = re.compile(r"^\+(?:[0-9] ?){6,14}[0-9]$")

        if order.has_customer_information:
            customer = {
                "firstName": order.customer_first_name.capitalize(),
                "lastName": order.customer_last_name.capitalize(),
                "email": order.customer_email.strip(),
            }
            phone = (order.customer_phone or "").strip()

        elif (
            hasattr(order, "lease")
            and order.lease is not None
            and order.lease.application
        ):
            application = order.lease.application
            customer = {
                "firstName": application.first_name.capitalize(),
                "lastName": application.last_name.capitalize(),
                "email": application.email.strip(),
            }
            phone = application.phone_number.strip()

        # Talpa only supports phones with a specific format, so if the phone is not in a valid
        # format, to avoid errors from the API, we skip it from the order and let the customer
        # enter it manually on the Talpa Checkout page.
        if phone_regex.match(phone):
            customer["phone"] = phone

        payload["customer"] = customer

    def handle_settle_order(self, order: Order, event_type: str) -> HttpResponse:
        status: Optional[OrderStatus]
        message: str
        payment_status: str

        if event_type == TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID:
            status = OrderStatus.PAID
            message = "Payment succeeded in Talpa eCommerce"
            payment_status = TalpaEComPaymentDetails.PAYMENT_PAID
        elif event_type == TALPA_ECOM_WEBHOOK_EVENT_ORDER_CANCELLED:
            status = OrderStatus.REJECTED
            message = "Payment rejected in Talpa eCommerce"
            payment_status = TalpaEComPaymentDetails.PAYMENT_CANCELLED
        else:
            raise UnknownWebhookEventError(_("Unknown webhook event: ") + event_type)

        # To verify that the payment information is correct and the call to the webhook
        # is not being faked, we check that the payment status matches the type of event
        # that we're getting on the webhook
        payment_details = self.get_payment_details(order)
        if payment_details.status != payment_status:
            return HttpResponseBadRequest()

        try:
            order.set_status(status, message)
        except OrderStatusTransitionError as oste:
            logger.warning(oste)
            order.create_log_entry(None, comment=message)

        # We don't have to redirect anything since it's Talpa eCom Payment API calling this
        # after the payment has settled on their system not the customer being redirected after payment
        return HttpResponse(str(order), status=204)

    def handle_notify_request(self) -> HttpResponse:
        """Handle incoming notify request from the payment provider.

        Example response:
        {
             "paymentId": "36985766-eb07-42c2-8277-9508630f42d1",
             "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
             "namespace": "venepaikat",
             "eventType": "PAYMENT_PAID",
             "timestamp": "2021-10-19T09:11:00.123Z",
        }
        """
        if self.request.content_type != "application/json":
            return HttpResponseBadRequest(_("Invalid content type"))

        data = self.request.body
        try:
            data = json.loads(data)
        except Exception as e:
            return HttpResponseBadRequest(str(e))

        logger.debug(
            "Handling Talpa eCommerce notify request, params: {}.".format(data)
        )

        order_id = data.get("orderId", "")
        namespace = data.get("namespace", "")
        event_type = data.get("eventType", "")

        if namespace != self.namespace:
            return HttpResponseBadRequest(f"{_('Wrong namespace')}: {namespace}")

        if event_type not in TALPA_ECOM_WEBHOOK_EVENT_TYPES:
            return HttpResponseBadRequest(f"{_('Wrong webhook event')}: {event_type}")

        try:
            order = Order.objects.get(talpa_ecom_id=order_id)
        except Order.DoesNotExist:
            logger.warning("Order does not exist.")
            return HttpResponseNotFound()

        try:
            return self.handle_settle_order(order, event_type)
        except UnknownWebhookEventError as e:
            return HttpResponseBadRequest(f"{_('Webhook event error')}: {e}")

    def get_payment_details(self, order: Order) -> TalpaEComPaymentDetails:
        headers = {"user": get_customer_hash(order.customer)}

        r = requests.get(
            f"{self.url_payment_experience_api.rstrip('/')}/{order.talpa_ecom_id}",
            headers=headers,
            timeout=60,
        )
        r.raise_for_status()
        response = json.loads(r.text, parse_float=Decimal)

        return TalpaEComPaymentDetails(payment_dict=response)

    # The following functionalities are not used by this provider:
    def handle_success_request(self) -> HttpResponse:
        """
        The success results are handled directly by Talpa eCom Checkout.
        """
        return HttpResponseNotFound()

    def _get_final_return_url(self, vene_return_url, lang: str):
        """
        The success/failure pages are configured directly on the Talpa eCom system,
        so we don't have to pass it as a parameter to the requests.
        """
        raise NotImplementedError("Not used in the Talpa eCom flow")

    def get_success_url(self, lang: str = settings.LANGUAGE_CODE) -> str:
        """
        The success page URL is configured directly on the Talpa eCom system,
        so we don't have to pass it as a parameter to the requests.
        """
        raise NotImplementedError("Not used in the Talpa eCom flow")

    def get_failure_url(self, lang: str = settings.LANGUAGE_CODE) -> str:
        """
        The failures are handled directly by Talpa eCom Checkout.
        """
        raise NotImplementedError("Not used in the Talpa eCom flow")

    def ui_redirect_success(self, order: Order = None) -> HttpResponse:
        """
        The success page is handled by Talpa eCom Checkout, at the end of the
        flow we only get the notification that the payment was completed, so
        we don't have to redirect the user to the final page
        """
        return HttpResponseNotFound()

    def ui_redirect_failure(self, order: Order = None) -> HttpResponse:
        """
        The failure page is handled by Talpa eCom Checkout, at the end of the
        flow we only get the notification that the payment was completed, so
        we don't have to redirect the user to the final page
        """
        return HttpResponseNotFound()

    @classmethod
    def _redirect_to_ui(
        cls, return_url: str, status: str, order: Order = None, path: str = "/"
    ):
        """The Talpa eCom handles the UI-related parts, so there's no need to do any redirects."""
        raise NotImplementedError("Not used in the Talpa eCom flow")
