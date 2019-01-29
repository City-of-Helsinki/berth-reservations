import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test.client import RequestFactory

from berth_reservations.tests.factories import UserFactory

from ..admin import ReservationAdmin
from ..models import Reservation

site = admin.AdminSite(name='test_admin_site')
site.register(Reservation)


@pytest.mark.parametrize('has_resend_permissions', [True, False])
def test_admin_gets_resend_reservations_action_when(has_resend_permissions):
    user = UserFactory()
    user.is_staff = True
    user.save()

    if has_resend_permissions:
        resend_permission = Permission.objects.filter(
            content_type__app_label=Reservation._meta.app_label,
            content_type__model=Reservation._meta.model_name,
            codename='resend_reservation'
        ).first()
        user.user_permissions.add(resend_permission)

    request = RequestFactory().get('/')
    request.user = user

    model_admin = ReservationAdmin(admin_site=site, model=Reservation)
    actions = model_admin.get_actions(request)
    resend_action_name = 'resend_reservation_confirmation'

    assert (resend_action_name in actions) == has_resend_permissions
