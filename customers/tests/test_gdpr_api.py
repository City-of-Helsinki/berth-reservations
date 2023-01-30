import datetime
import json
from unittest import TestCase

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from helusers.settings import api_token_auth_settings
from jose import jwt

from applications.enums import ApplicationStatus, WinterStorageMethod
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.factories import CustomerProfileFactory
from customers.enums import InvoicingType
from customers.models import CustomerProfile
from customers.tests.factories import BoatFactory, OrganizationFactory
from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.enums import OfferStatus, OrderStatus
from payments.tests.factories import BerthSwitchOfferFactory, OrderFactory

from .keys import rsa_key

User = get_user_model()


def get_api_token_for_user_with_scopes(user, scopes, requests_mock):
    """Build a proper auth token with desired scopes."""

    audience = api_token_auth_settings.AUDIENCE
    issuer = api_token_auth_settings.ISSUER
    auth_field = api_token_auth_settings.API_AUTHORIZATION_FIELD
    config_url = f"{issuer}/.well-known/openid-configuration"
    jwks_url = f"{issuer}/jwks"
    configuration = {
        "issuer": issuer,
        "jwks_uri": jwks_url,
    }

    keys = {"keys": [rsa_key.public_key_jwk]}

    now = datetime.datetime.now()
    expire = now + datetime.timedelta(days=14)

    jwt_data = {
        "iss": issuer,
        "aud": audience,
        "sub": str(user.uuid),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        auth_field: scopes,
    }
    encoded_jwt = jwt.encode(
        jwt_data, key=rsa_key.private_key_pem, algorithm=rsa_key.jose_algorithm
    )

    requests_mock.get(config_url, json=configuration)
    requests_mock.get(jwks_url, json=keys)
    auth_header = f"{api_token_auth_settings.AUTH_SCHEME} {encoded_jwt}"
    return auth_header


@override_settings(GDPR_API_QUERY_SCOPE="berthsapidev.gdprquery")
def test_get_profile_information_from_gdpr_api(
    rest_api_client, requests_mock, settings
):
    customer_profile = CustomerProfileFactory()

    auth_header = get_api_token_for_user_with_scopes(
        customer_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
    )

    rest_api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = rest_api_client.get(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": customer_profile.id})
    )

    resp = json.loads(response.content)
    assert response.status_code == 200
    assert resp == {
        "key": "CUSTOMERPROFILE",
        "children": [
            {
                "key": "INVOICING_TYPE",
                "value": dict(InvoicingType.choices)[customer_profile.invoicing_type],
            },
            {"key": "COMMENT", "value": customer_profile.comment},
            {
                "key": "CREATED_AT",
                "value": customer_profile.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            },
            {
                "key": "MODIFIED_AT",
                "value": customer_profile.modified_at.strftime("%d-%m-%Y %H:%M:%S"),
            },
            {"key": "BERTH_APPLICATIONS", "children": []},
            {"key": "BERTH_LEASES", "children": []},
            {"key": "BOATS", "children": []},
            {"key": "OFFERS", "children": []},
            {"key": "ORDERS", "children": []},
            {"key": "WINTER_STORAGE_APPLICATIONS", "children": []},
            {"key": "WINTER_STORAGE_LEASES", "children": []},
        ],
    }


@override_settings(GDPR_API_QUERY_SCOPE="berthsapidev.gdprquery")
def test_get_full_profile_information_from_gdpr_api(
    rest_api_client, requests_mock, settings
):
    customer_profile = CustomerProfileFactory()
    boat = BoatFactory(owner=customer_profile)
    berth_application = BerthApplicationFactory(customer=customer_profile, boat=boat)
    berth_lease = BerthLeaseFactory(
        customer=customer_profile, boat=boat, status=LeaseStatus.PAID
    )
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile, boat=boat
    )
    winter_storage_lease = WinterStorageLeaseFactory(
        customer=customer_profile, boat=boat
    )
    order = OrderFactory(lease=berth_lease)
    berth_switch_offer = BerthSwitchOfferFactory(
        customer=customer_profile, lease=berth_lease
    )
    organization = OrganizationFactory(customer=customer_profile)

    auth_header = get_api_token_for_user_with_scopes(
        customer_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
    )
    rest_api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = rest_api_client.get(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": customer_profile.id})
    )

    resp = json.loads(response.content)

    assert response.status_code == 200

    assert {
        "key": "INVOICING_TYPE",
        "value": dict(InvoicingType.choices)[customer_profile.invoicing_type],
    } in resp["children"]

    assert {"key": "COMMENT", "value": customer_profile.comment} in resp["children"]

    assert {
        "key": "CREATED_AT",
        "value": customer_profile.created_at.strftime("%d-%m-%Y %H:%M:%S"),
    } in resp["children"]

    assert {
        "key": "MODIFIED_AT",
        "value": customer_profile.modified_at.strftime("%d-%m-%Y %H:%M:%S"),
    } in resp["children"]

    berth_applications_dict = {}
    berth_leases_dict = {}
    boats_dict = {}
    offers_dict = {}
    orders_dict = {}
    organization_dict = {}
    winter_storage_applications_dict = {}
    winter_storage_leases_dict = {}
    for child_dict in resp["children"]:
        if child_dict["key"] == "BERTH_APPLICATIONS":
            berth_applications_dict = child_dict
        elif child_dict["key"] == "BERTH_LEASES":
            berth_leases_dict = child_dict
        elif child_dict["key"] == "BOATS":
            boats_dict = child_dict
        elif child_dict["key"] == "OFFERS":
            offers_dict = child_dict
        elif child_dict["key"] == "ORDERS":
            orders_dict = child_dict
        elif child_dict["key"] == "ORGANIZATION":
            organization_dict = child_dict
        elif child_dict["key"] == "WINTER_STORAGE_APPLICATIONS":
            winter_storage_applications_dict = child_dict
        elif child_dict["key"] == "WINTER_STORAGE_LEASES":
            winter_storage_leases_dict = child_dict

    # Using a TestCase here since assertDictEqual is better for comparing dicts
    test_case = TestCase()

    test_case.assertDictEqual(
        {
            "key": "BERTH_APPLICATIONS",
            "children": [
                {
                    "key": "BERTHAPPLICATION",
                    "children": [
                        {"key": "ID", "value": berth_application.id},
                        {
                            "key": "CREATED_AT",
                            "value": berth_application.created_at.strftime(
                                "%d-%m-%Y %H:%M:%S"
                            ),
                        },
                        {
                            "key": "STATUS",
                            "value": dict(ApplicationStatus.choices)[
                                berth_application.status
                            ],
                        },
                        {"key": "LANGUAGE", "value": berth_application.language},
                        {"key": "FIRST_NAME", "value": berth_application.first_name},
                        {"key": "LAST_NAME", "value": berth_application.last_name},
                        {"key": "EMAIL", "value": berth_application.email},
                        {
                            "key": "PHONE_NUMBER",
                            "value": berth_application.phone_number,
                        },
                        {"key": "ADDRESS", "value": berth_application.address},
                        {"key": "ZIP_CODE", "value": berth_application.zip_code},
                        {
                            "key": "MUNICIPALITY",
                            "value": berth_application.municipality,
                        },
                        {
                            "key": "COMPANY_NAME",
                            "value": berth_application.company_name,
                        },
                        {"key": "BUSINESS_ID", "value": berth_application.business_id},
                        {
                            "key": "BOAT",
                            "value": str(berth_application.boat.id),
                        },
                        {
                            "key": "ACCEPT_BOATING_NEWSLETTER",
                            "value": berth_application.accept_boating_newsletter,
                        },
                        {
                            "key": "ACCEPT_FITNESS_NEWS",
                            "value": berth_application.accept_fitness_news,
                        },
                        {
                            "key": "ACCEPT_LIBRARY_NEWS",
                            "value": berth_application.accept_library_news,
                        },
                        {
                            "key": "ACCEPT_OTHER_CULTURE_NEWS",
                            "value": berth_application.accept_other_culture_news,
                        },
                        {
                            "key": "INFORMATION_ACCURACY_CONFIRMED",
                            "value": berth_application.information_accuracy_confirmed,
                        },
                        {
                            "key": "APPLICATION_CODE",
                            "value": berth_application.application_code,
                        },
                        {"key": "HARBORCHOICE_SET", "value": []},
                        {
                            "key": "BERTH_SWITCH",
                            "value": berth_application.berth_switch,
                        },
                        {
                            "key": "ACCESSIBILITY_REQUIRED",
                            "value": berth_application.accessibility_required,
                        },
                        {
                            "key": "RENTING_PERIOD",
                            "value": berth_application.renting_period,
                        },
                        {"key": "RENT_FROM", "value": berth_application.rent_from},
                        {"key": "RENT_TILL", "value": berth_application.rent_till},
                        {
                            "key": "AGREE_TO_TERMS",
                            "value": berth_application.agree_to_terms,
                        },
                    ],
                }
            ],
        },
        berth_applications_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "BERTH_LEASES",
            "children": [
                {
                    "key": "BERTHLEASE",
                    "children": [
                        {"key": "ID", "value": str(berth_lease.id)},
                        {"key": "BOAT", "value": str(boat.id)},
                        {
                            "key": "STATUS",
                            "value": dict(LeaseStatus.choices)[berth_lease.status],
                        },
                        {"key": "ORDERS", "value": [str(order.id)]},
                        {"key": "COMMENT", "value": berth_lease.comment},
                        {
                            "key": "BERTH",
                            "value": {
                                "key": "BERTH",
                                "children": [
                                    {
                                        "key": "NUMBER",
                                        "value": berth_lease.berth.number,
                                    },
                                    {
                                        "key": "PIER",
                                        "value": {
                                            "key": "PIER",
                                            "children": [
                                                {
                                                    "key": "IDENTIFIER",
                                                    "value": berth_lease.berth.pier.identifier,
                                                }
                                            ],
                                        },
                                    },
                                ],
                            },
                        },
                        {"key": "APPLICATION", "value": None},
                        {
                            "key": "START_DATE",
                            "value": berth_lease.start_date.strftime("%d-%m-%Y"),
                        },
                        {
                            "key": "END_DATE",
                            "value": berth_lease.end_date.strftime("%d-%m-%Y"),
                        },
                    ],
                }
            ],
        },
        berth_leases_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "BOATS",
            "children": [
                {
                    "key": "BOAT",
                    "children": [
                        {"key": "ID", "value": str(boat.id)},
                        {"key": "BOAT_TYPE", "value": boat.boat_type.name},
                        {"key": "CERTIFICATES", "children": []},
                        {
                            "key": "REGISTRATION_NUMBER",
                            "value": boat.registration_number,
                        },
                        {"key": "NAME", "value": boat.name},
                        {"key": "MODEL", "value": boat.model},
                        {"key": "LENGTH", "value": float(boat.length)},
                        {"key": "WIDTH", "value": float(boat.width)},
                        {"key": "DRAUGHT", "value": boat.draught},
                        {"key": "WEIGHT", "value": boat.weight},
                        {"key": "PROPULSION", "value": boat.propulsion},
                        {"key": "HULL_MATERIAL", "value": boat.hull_material},
                        {"key": "INTENDED_USE", "value": boat.intended_use},
                        {"key": "IS_INSPECTED", "value": boat.is_inspected},
                        {"key": "IS_INSURED", "value": boat.is_insured},
                    ],
                }
            ],
        },
        boats_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "OFFERS",
            "children": [
                {
                    "key": "BERTHSWITCHOFFER",
                    "children": [
                        {"key": "ID", "value": str(berth_switch_offer.id)},
                        {
                            "key": "STATUS",
                            "value": dict(OfferStatus.choices)[
                                berth_switch_offer.status
                            ],
                        },
                        {
                            "key": "DUE_DATE",
                            "value": berth_switch_offer.due_date.strftime("%d-%m-%Y")
                            if berth_switch_offer.due_date
                            else None,
                        },
                        {
                            "key": "CUSTOMER_FIRST_NAME",
                            "value": berth_switch_offer.customer_first_name,
                        },
                        {
                            "key": "CUSTOMER_LAST_NAME",
                            "value": berth_switch_offer.customer_last_name,
                        },
                        {
                            "key": "CUSTOMER_EMAIL",
                            "value": berth_switch_offer.customer_email,
                        },
                        {
                            "key": "CUSTOMER_PHONE",
                            "value": berth_switch_offer.customer_phone,
                        },
                        {
                            "key": "APPLICATION",
                            "value": berth_switch_offer.application.id,
                        },
                        {"key": "LEASE", "value": str(berth_switch_offer.lease.id)},
                        {"key": "BERTH", "value": str(berth_switch_offer.berth.id)},
                    ],
                }
            ],
        },
        offers_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "ORDERS",
            "children": [
                {
                    "key": "ORDER",
                    "children": [
                        {"key": "ID", "value": str(order.id)},
                        {
                            "key": "PRODUCT",
                            "value": {
                                "key": "BERTHPRODUCT",
                                "children": [
                                    {
                                        "key": "MIN_WIDTH",
                                        "value": float(order.product.min_width),
                                    },
                                    {
                                        "key": "MAX_WIDTH",
                                        "value": float(order.product.max_width),
                                    },
                                    {
                                        "key": "TIER_1_PRICE",
                                        "value": float(order.product.tier_1_price),
                                    },
                                    {
                                        "key": "TIER_2_PRICE",
                                        "value": float(order.product.tier_2_price),
                                    },
                                    {
                                        "key": "TIER_3_PRICE",
                                        "value": float(order.product.tier_3_price),
                                    },
                                    {
                                        "key": "PRICE_UNIT",
                                        "value": order.product.price_unit,
                                    },
                                    {
                                        "key": "TAX_PERCENTAGE",
                                        "value": float(order.product.tax_percentage),
                                    },
                                ],
                            },
                        },
                        {"key": "LEASE", "value": str(order.lease.id)},
                        {
                            "key": "STATUS",
                            "value": dict(OrderStatus.choices)[order.status],
                        },
                        {"key": "COMMENT", "value": order.comment},
                        {"key": "PRICE", "value": float(order.price)},
                        {"key": "TAX_PERCENTAGE", "value": float(order.tax_percentage)},
                        {"key": "PRETAX_PRICE", "value": float(order.pretax_price)},
                        {"key": "TOTAL_PRICE", "value": float(order.total_price)},
                        {
                            "key": "TOTAL_PRETAX_PRICE",
                            "value": float(order.total_pretax_price),
                        },
                        {
                            "key": "TOTAL_TAX_PERCENTAGE",
                            "value": float(order.total_tax_percentage),
                        },
                        {
                            "key": "DUE_DATE",
                            "value": order.due_date.strftime("%d-%m-%Y"),
                        },
                        {"key": "ORDER_LINES", "children": []},
                        {"key": "LOG_ENTRIES", "children": []},
                        {"key": "PAID_AT", "value": None},
                        {"key": "CANCELLED_AT", "value": None},
                        {"key": "REJECTED_AT", "value": None},
                    ],
                }
            ],
        },
        orders_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "ORGANIZATION",
            "children": [
                {"key": "ID", "value": str(organization.id)},
                {"key": "BUSINESS_ID", "value": organization.business_id},
                {"key": "NAME", "value": organization.name},
                {"key": "ADDRESS", "value": organization.address},
                {"key": "POSTAL_CODE", "value": organization.postal_code},
                {"key": "CITY", "value": organization.city},
            ],
        },
        organization_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "WINTER_STORAGE_APPLICATIONS",
            "children": [
                {
                    "key": "WINTERSTORAGEAPPLICATION",
                    "children": [
                        {"key": "ID", "value": winter_storage_application.id},
                        {
                            "key": "CREATED_AT",
                            "value": winter_storage_application.created_at.strftime(
                                "%d-%m-%Y %H:%M:%S"
                            ),
                        },
                        {
                            "key": "STATUS",
                            "value": dict(ApplicationStatus.choices)[
                                winter_storage_application.status
                            ],
                        },
                        {
                            "key": "LANGUAGE",
                            "value": winter_storage_application.language,
                        },
                        {
                            "key": "FIRST_NAME",
                            "value": winter_storage_application.first_name,
                        },
                        {
                            "key": "LAST_NAME",
                            "value": winter_storage_application.last_name,
                        },
                        {"key": "EMAIL", "value": winter_storage_application.email},
                        {
                            "key": "PHONE_NUMBER",
                            "value": winter_storage_application.phone_number,
                        },
                        {"key": "ADDRESS", "value": winter_storage_application.address},
                        {
                            "key": "ZIP_CODE",
                            "value": winter_storage_application.zip_code,
                        },
                        {
                            "key": "MUNICIPALITY",
                            "value": winter_storage_application.municipality,
                        },
                        {"key": "COMPANY_NAME", "value": ""},
                        {"key": "BUSINESS_ID", "value": ""},
                        {
                            "key": "BOAT",
                            "value": str(winter_storage_application.boat.id),
                        },
                        {"key": "ACCEPT_BOATING_NEWSLETTER", "value": False},
                        {"key": "ACCEPT_FITNESS_NEWS", "value": False},
                        {"key": "ACCEPT_LIBRARY_NEWS", "value": False},
                        {"key": "ACCEPT_OTHER_CULTURE_NEWS", "value": False},
                        {"key": "INFORMATION_ACCURACY_CONFIRMED", "value": False},
                        {"key": "APPLICATION_CODE", "value": ""},
                        {"key": "AREA_TYPE", "value": None},
                        {"key": "WINTERSTORAGEAREACHOICE_SET", "value": []},
                        {
                            "key": "STORAGE_METHOD",
                            "value": dict(WinterStorageMethod.choices)[
                                winter_storage_application.storage_method
                            ],
                        },
                        {"key": "TRAILER_REGISTRATION_NUMBER", "value": ""},
                    ],
                }
            ],
        },
        winter_storage_applications_dict,
    )

    test_case.assertDictEqual(
        {
            "key": "WINTER_STORAGE_LEASES",
            "children": [
                {
                    "key": "WINTERSTORAGELEASE",
                    "children": [
                        {"key": "ID", "value": str(winter_storage_lease.id)},
                        {"key": "BOAT", "value": str(boat.id)},
                        {
                            "key": "STATUS",
                            "value": dict(LeaseStatus.choices)[
                                winter_storage_lease.status
                            ],
                        },
                        {"key": "ORDERS", "value": []},
                        {"key": "COMMENT", "value": winter_storage_lease.comment},
                        {
                            "key": "PLACE",
                            "value": {
                                "key": "WINTERSTORAGEPLACE",
                                "children": [
                                    {
                                        "key": "NUMBER",
                                        "value": winter_storage_lease.place.number,
                                    },
                                    {
                                        "key": "WINTER_STORAGE_SECTION",
                                        "value": {
                                            "key": "WINTERSTORAGESECTION",
                                            "children": [
                                                {
                                                    "key": "IDENTIFIER",
                                                    "value": (
                                                        winter_storage_lease.place.winter_storage_section.identifier
                                                    ),
                                                }
                                            ],
                                        },
                                    },
                                ],
                            },
                        },
                        {"key": "SECTION", "value": None},
                        {"key": "APPLICATION", "value": None},
                        {
                            "key": "START_DATE",
                            "value": winter_storage_lease.start_date.strftime(
                                "%d-%m-%Y"
                            ),
                        },
                        {
                            "key": "END_DATE",
                            "value": winter_storage_lease.end_date.strftime("%d-%m-%Y"),
                        },
                        {"key": "STICKER_NUMBER", "value": None},
                        {"key": "STICKER_POSTED", "value": None},
                    ],
                }
            ],
        },
        winter_storage_leases_dict,
    )


@override_settings(GDPR_API_DELETE_SCOPE="berthsapidev.gdprdelete")
def test_delete_profile(rest_api_client, requests_mock, settings):
    customer_profile = CustomerProfileFactory()

    auth_header = get_api_token_for_user_with_scopes(
        customer_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    rest_api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = rest_api_client.delete(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": customer_profile.id})
    )

    assert response.status_code == 204
    assert CustomerProfile.objects.count() == 0
    assert User.objects.count() == 0


@override_settings(GDPR_API_DELETE_SCOPE="berthsapidev.gdprdelete")
def test_delete_profile_with_lease(rest_api_client, requests_mock, settings):
    """For now, if the profile has resources connected to it, they will prevent
    the deletion of the profile
    """
    customer_profile = CustomerProfileFactory()
    BerthLeaseFactory(customer=customer_profile)

    auth_header = get_api_token_for_user_with_scopes(
        customer_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    rest_api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = rest_api_client.delete(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": customer_profile.id})
    )

    assert response.status_code == 403
    assert CustomerProfile.objects.count() == 1
    assert User.objects.count() == 1
