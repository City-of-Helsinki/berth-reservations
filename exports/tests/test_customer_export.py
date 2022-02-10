import pytest
import xlrd
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
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
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)
    assert "Customers" in wb.sheet_names()
    xl_sheet = wb.sheet_by_name("Customers")
    for row_number, identifier in enumerate(ids, 1):
        row = xl_sheet.row(row_number)
        assert row[0].value == str(identifier)


def test_customer_excel_fields():
    cp = CustomerProfileFactory()
    exporter = CustomerXlsx(CustomerProfile.objects.all())

    xlsx_bytes = exporter.serialize()

    wb = xlrd.open_workbook(file_contents=xlsx_bytes)
    assert "Customers" in wb.sheet_names()
    xl_sheet = wb.sheet_by_name("Customers")
    assert xl_sheet.ncols == 8
    row = xl_sheet.row(1)
    assert row[0].value == str(cp.id)
    assert row[1].value == cp.user.first_name
    assert row[2].value == cp.user.last_name
    assert row[3].value == str(InvoicingType(cp.invoicing_type).label)
    assert row[4].value == "private"
    assert row[5].value == cp.comment

    # Excel internally presents datetimes as floats
    float(row[6].value)
    float(row[7].value)
