import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test.client import RequestFactory
from freezegun import freeze_time

from ..admin import ReservationAdmin
from ..models import Reservation

site = admin.AdminSite(name='test_admin_site')
site.register(Reservation)


@pytest.mark.parametrize('has_resend_permissions', [True, False])
def test_admin_gets_resend_reservations_action_when(has_resend_permissions, admin_user):
    if has_resend_permissions:
        resend_permission = Permission.objects.filter(
            content_type__app_label=Reservation._meta.app_label,
            content_type__model=Reservation._meta.model_name,
            codename='resend_reservation'
        ).first()
        admin_user.user_permissions.add(resend_permission)

    request = RequestFactory().get('/')
    request.user = admin_user

    model_admin = ReservationAdmin(admin_site=site, model=Reservation)
    actions = model_admin.get_actions(request)
    resend_action_name = 'resend_reservation_confirmation'

    assert (resend_action_name in actions) == has_resend_permissions


def test_admin_gets_export_reservations_action(admin_user):
    request = RequestFactory().get('/')
    request.user = admin_user

    model_admin = ReservationAdmin(admin_site=site, model=Reservation)
    actions = model_admin.get_actions(request)

    assert 'export_reservations' in actions


@freeze_time('2019-01-14T08:00:00Z')
def test_export_reservations_action_responds_with_xlsx(admin_user):
    request = RequestFactory().get('/')
    request.user = admin_user

    model_admin = ReservationAdmin(admin_site=site, model=Reservation)
    queryset = Reservation.objects.all()
    action_response = model_admin.export_reservations(request, queryset)

    exp_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert action_response['Content-Type'] == exp_type

    exp_disp = 'attachment; filename=berth_reservations_2019-01-14_10-00-00.xlsx'
    assert action_response['Content-Disposition'] == exp_disp
