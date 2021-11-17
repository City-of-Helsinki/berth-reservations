from django.core.management import call_command

from applications.enums import ApplicationStatus
from customers.tests.factories import BoatFactory
from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from resources.tests.factories import BoatTypeFactory


def test_create_boats_berth_applications(berth_application_with_customer):
    # Renaming for simplicity
    application = berth_application_with_customer
    BoatTypeFactory(id=application.boat.boat_type_id)

    application.status = ApplicationStatus.OFFER_SENT
    BerthLeaseFactory(
        application=application,
        customer=application.customer,
        status=LeaseStatus.PAID,
        boat=None,
    )
    application.save()

    assert application.customer.boats.count() == 0

    call_command("create_boat_for_existing_applications")

    application.refresh_from_db()
    assert application.customer.boats.count() == 1
    boat = application.customer.boats.first()

    assert application.lease.boat == application.boat == boat


def test_update_boats_berth_applications(berth_application_with_customer):
    # Renaming for simplicity
    application = berth_application_with_customer
    boat_type = BoatTypeFactory(id=application.boat.boat_type_id)

    application.boat.name = "New name"
    application.boat.registration_number = "NUMBER"
    application.boat.save()
    application.status = ApplicationStatus.OFFER_SENT
    BerthLeaseFactory(
        application=application,
        customer=application.customer,
        status=LeaseStatus.PAID,
        boat=BoatFactory(
            owner=application.customer,
            registration_number="NUMBER",
            name="Old name",
            boat_type=boat_type,
        ),
    )
    application.save()

    assert application.customer.boats.count() == 1

    call_command("create_boat_for_existing_applications")

    assert application.customer.boats.count() == 1
    boat = application.customer.boats.first()

    assert boat.registration_number == application.boat.registration_number
    assert boat.name == "New name"


def test_create_boats_winter_storage_applications(
    winter_storage_application_with_customer,
):
    # Renaming for simplicity
    application = winter_storage_application_with_customer
    BoatTypeFactory(id=application.boat.boat_type_id)

    application.status = ApplicationStatus.OFFER_SENT
    WinterStorageLeaseFactory(
        application=application,
        customer=application.customer,
        status=LeaseStatus.PAID,
        boat=None,
    )
    application.save()

    assert application.customer.boats.count() == 0

    call_command("create_boat_for_existing_applications")

    application.refresh_from_db()
    assert application.customer.boats.count() == 1
    boat = application.customer.boats.first()

    assert application.lease.boat == boat


def test_update_boats_winter_storage_applications(
    winter_storage_application_with_customer,
):
    # Renaming for simplicity
    application = winter_storage_application_with_customer
    boat_type = BoatTypeFactory(id=application.boat_type_id)

    application.boat.name = "New name"
    application.boat.registration_number = "NUMBER"
    application.boat.save()
    application.status = ApplicationStatus.OFFER_SENT
    WinterStorageLeaseFactory(
        application=application,
        customer=application.customer,
        status=LeaseStatus.PAID,
        boat=BoatFactory(
            owner=application.customer,
            registration_number="NUMBER",
            name="Old name",
            boat_type=boat_type,
        ),
    )
    application.save()

    assert application.customer.boats.count() == 1

    call_command("create_boat_for_existing_applications")

    assert application.customer.boats.count() == 1
    boat = application.customer.boats.first()
    assert boat.name == "New name"
