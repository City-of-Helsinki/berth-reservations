import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test.client import RequestFactory
from freezegun import freeze_time

from ..admin import BerthApplicationAdmin
from ..models import BerthApplication

site = admin.AdminSite(name="test_admin_site")
site.register(BerthApplication)


@pytest.mark.parametrize("has_resend_permissions", [True, False])
def test_admin_gets_resend_applications_action_when(has_resend_permissions, admin_user):
    if has_resend_permissions:
        resend_permission = Permission.objects.filter(
            content_type__app_label=BerthApplication._meta.app_label,
            codename="resend_application",
        ).first()
        admin_user.user_permissions.add(resend_permission)

    request = RequestFactory().get("/")
    request.user = admin_user

    model_admin = BerthApplicationAdmin(admin_site=site, model=BerthApplication)
    actions = model_admin.get_actions(request)
    resend_action_name = "resend_application_confirmation"

    assert (resend_action_name in actions) == has_resend_permissions


def test_admin_gets_export_applications_action(admin_user):
    request = RequestFactory().get("/")
    request.user = admin_user

    model_admin = BerthApplicationAdmin(admin_site=site, model=BerthApplication)
    actions = model_admin.get_actions(request)

    assert "export_applications" in actions


@freeze_time("2019-01-14T08:00:00Z")
def test_export_applications_action_responds_with_xlsx(admin_user):
    request = RequestFactory().get("/")
    request.user = admin_user

    model_admin = BerthApplicationAdmin(admin_site=site, model=BerthApplication)
    queryset = BerthApplication.objects.all()
    action_response = model_admin.export_applications(request, queryset)

    exp_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert action_response["Content-Type"] == exp_type

    exp_disp = "attachment; filename=berth_applications_2019-01-14_10-00-00.xlsx"
    assert action_response["Content-Disposition"] == exp_disp
