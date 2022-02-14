import datetime
import io

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from freezegun import freeze_time
from openpyxl import load_workbook
from rest_framework import status

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.enums import InvoicingType
from customers.models import CustomerProfile
from customers.schema import ProfileNode
from exports.xlsx_writer import CustomerXlsx
from utils.relay import to_global_id


def to_global_profile_node_ids(ids):
    return map(lambda x: to_global_id(ProfileNode, x), ids)


@pytest.mark.parametrize("has_permission", [True, False])
def test_admin_credentials_are_required(user_api_client, has_permission):
    if has_permission:
        permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(CustomerProfile),
            codename="view_customerprofile",
        )
        user_api_client.user.user_permissions.add(permission)
    CustomerProfileFactory()
    ids = CustomerProfile.objects.all().values_list("id", flat=True)
    global_ids = to_global_profile_node_ids(ids)

    response = user_api_client.post(reverse("customer_xlsx"), data={"ids": global_ids})

    if has_permission:
        assert response.status_code == status.HTTP_200_OK
    else:
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_amount_of_queries(superuser_api_client, django_assert_max_num_queries):
    CustomerProfileFactory.create_batch(2)
    CustomerProfileFactory.create_batch(2, user=None)
    ids = CustomerProfile.objects.all().values_list("id", flat=True)
    global_ids = to_global_profile_node_ids(ids)

    with django_assert_max_num_queries(2):
        response = superuser_api_client.post(
            reverse("customer_xlsx"), data={"ids": global_ids}
        )

    assert response.status_code == status.HTTP_200_OK


def test_export_view_produces_an_excel(superuser_api_client):
    CustomerProfileFactory.create_batch(2)
    ids = CustomerProfile.objects.all().values_list("id", flat=True)
    global_ids = to_global_profile_node_ids(ids)

    response = superuser_api_client.post(
        reverse("customer_xlsx"), data={"ids": global_ids}
    )

    assert response.status_code == status.HTTP_200_OK
    xlsx_bytes = response.content
    xlsx_file = io.BytesIO(xlsx_bytes)
    wb = load_workbook(filename=xlsx_file, read_only=True)
    assert "Customers" in wb.sheetnames
    xl_sheet = wb["Customers"]
    for row_number, identifier in enumerate(ids, 2):
        assert xl_sheet.cell(row_number, 1).value == str(identifier)


@freeze_time("2020-01-01T10:00:00+02:00")
def test_customer_excel_fields():
    expected_datetime_format = "YYYY-MM-DD HH:MM:SS"
    cp = CustomerProfileFactory()
    exporter = CustomerXlsx(CustomerProfile.objects.all())

    xlsx_bytes = exporter.serialize()

    xlsx_file = io.BytesIO(xlsx_bytes)
    wb = load_workbook(filename=xlsx_file, read_only=True)
    assert "Customers" in wb.sheetnames
    xl_sheet = wb["Customers"]

    assert xl_sheet.max_column == 8

    assert xl_sheet.cell(2, 1).value == str(cp.id)
    assert xl_sheet.cell(2, 2).value == cp.user.first_name
    assert xl_sheet.cell(2, 3).value == cp.user.last_name
    assert xl_sheet.cell(2, 4).value == str(InvoicingType(cp.invoicing_type).label)
    assert xl_sheet.cell(2, 5).value == "private"
    assert xl_sheet.cell(2, 6).value == cp.comment

    assert xl_sheet.cell(2, 7).value == datetime.datetime(2020, 1, 1, 10)
    assert xl_sheet.cell(2, 7).number_format == expected_datetime_format
    assert xl_sheet.cell(2, 8).value == datetime.datetime(2020, 1, 1, 10)
    assert xl_sheet.cell(2, 8).number_format == expected_datetime_format
