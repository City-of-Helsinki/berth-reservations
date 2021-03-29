import pytest
from django.core.exceptions import ValidationError

from resources.tests.factories import WinterStorageAreaFactory

from ..enums import ApplicationAreaType, ApplicationStatus
from .factories import (
    BerthApplicationFactory,
    WinterAreaChoiceFactory,
    WinterStorageApplicationFactory,
)


def test_berth_application_without_lease_valid_statuses(berth_application):
    new_status = ApplicationStatus.PENDING
    berth_application.lease = None
    berth_application.status = new_status

    berth_application.save()

    assert berth_application.status == new_status


def test_berth_application_without_lease_invalid_statuses(berth_application):
    new_status = ApplicationStatus.OFFER_GENERATED
    berth_application.lease = None
    berth_application.status = new_status

    with pytest.raises(ValidationError) as exception:
        berth_application.save()

    error_msg = str(exception.value)
    assert new_status.name in error_msg
    assert "BerthApplication with no lease can only be" in error_msg


def test_winterstorage_application_resolve_marked_area(winter_storage_application):
    area = WinterStorageAreaFactory()
    area.estimated_number_of_unmarked_spaces = None
    area.save()
    WinterAreaChoiceFactory(
        application=winter_storage_application, winter_storage_area=area
    )

    assert winter_storage_application.resolve_area_type() == ApplicationAreaType.MARKED


def test_winterstorage_application_resolve_unmarked_area(winter_storage_application):
    area = WinterStorageAreaFactory()
    area.estimated_number_of_unmarked_spaces = 50
    area.save()
    WinterAreaChoiceFactory(
        application=winter_storage_application, winter_storage_area=area
    )

    assert (
        winter_storage_application.resolve_area_type() == ApplicationAreaType.UNMARKED
    )


def test_berth_application_stripped_fields():
    application = BerthApplicationFactory(
        first_name="    Foo     ",
        last_name="  Bar \t ",
        email=" spaces@email.com   ",
        phone_number=" 01123123",
        address="   Street 1     ",
        zip_code="  01010 ",
        municipality="    Helsinki    ",
        company_name=" Company   ",
        business_id=" 010101010 ",
        boat_registration_number=" BOAT  ",
        boat_name=" Boat name \t \t",
        boat_model="    Buster",
        application_code="     code ",
        boat_propulsion="      propulsion ",
        boat_hull_material=" hull ",
        boat_intended_use=" use ",
        renting_period="     01-02 ",
        rent_from=" 01",
        rent_till="02 ",
    )
    assert application.first_name == "Foo"
    assert application.last_name == "Bar"
    assert application.email == "spaces@email.com"
    assert application.phone_number == "01123123"
    assert application.address == "Street 1"
    assert application.zip_code == "01010"
    assert application.municipality == "Helsinki"
    assert application.company_name == "Company"
    assert application.business_id == "010101010"
    assert application.boat_registration_number == "BOAT"
    assert application.boat_name == "Boat name"
    assert application.boat_model == "Buster"
    assert application.application_code == "code"
    assert application.boat_propulsion == "propulsion"
    assert application.boat_hull_material == "hull"
    assert application.boat_intended_use == "use"
    assert application.renting_period == "01-02"
    assert application.rent_from == "01"
    assert application.rent_till == "02"


def test_winter_storage_application_stripped_fields():
    application = WinterStorageApplicationFactory(
        area_type=None,
        first_name="    Foo     ",
        last_name="  Bar \t ",
        email=" spaces@email.com   ",
        phone_number=" 01123123",
        address="   Street 1     ",
        zip_code="  01010 ",
        municipality="    Helsinki    ",
        company_name=" Company   ",
        business_id=" 010101010 ",
        boat_registration_number=" BOAT  ",
        boat_name=" Boat name \t \t",
        boat_model="    Buster",
        application_code="     code ",
        trailer_registration_number="    trailer    ",
    )
    assert application.first_name == "Foo"
    assert application.last_name == "Bar"
    assert application.email == "spaces@email.com"
    assert application.phone_number == "01123123"
    assert application.address == "Street 1"
    assert application.zip_code == "01010"
    assert application.municipality == "Helsinki"
    assert application.company_name == "Company"
    assert application.business_id == "010101010"
    assert application.boat_registration_number == "BOAT"
    assert application.boat_name == "Boat name"
    assert application.boat_model == "Buster"
    assert application.application_code == "code"
    assert application.trailer_registration_number == "trailer"
