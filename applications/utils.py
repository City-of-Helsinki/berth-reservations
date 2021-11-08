import io

from django.conf import settings
from django.utils import dateformat, formats, timezone, translation
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from customers.models import Boat

from .enums import WinterStorageMethod


def export_berth_applications_as_xlsx(applications):
    fields = (
        # Common fields
        ("Reserved at", "created_at", 15),
        ("Chosen harbors", "chosen_harbors", 55),
        ("Current berth", "berth_switch", 35),
        ("Switch Reason", "berth_switch_reason", 55),
        ("Company name", "company_name", 35),
        ("Business ID", "business_id", 15),
        ("First name", "first_name", 15),
        ("Last name", "last_name", 15),
        ("Email", "email", 15),
        ("Address", "address", 15),
        ("Zip code", "zip_code", 15),
        ("Municipality", "municipality", 15),
        ("Phone number", "phone_number", 15),
        ("Boat type", "boat_type", 15),
        ("Boat width", "get_boat_width", 15),
        ("Boat length", "get_boat_length", 15),
        ("Boat draught", "get_boat_draught", 15),
        ("Boat weight", "get_boat_weight", 15),
        ("Boat registration number", "get_boat_registration_number", 15),
        ("Boat name", "get_boat_name", 15),
        ("Boat model", "get_boat_model", 15),
        ("Accessibility required", "accessibility_required", 15),
        ("Accept boating newsletter", "accept_boating_newsletter", 15),
        ("Accept fitness news", "accept_fitness_news", 15),
        ("Accept library news", "accept_library_news", 15),
        ("Accept other culture news", "accept_other_culture_news", 15),
        # Big boat specific fields
        ("Boat hull material", "boat_hull_material", 15),
        ("Boat intended use", "boat_intended_use", 15),
        ("Renting period", "renting_period", 15),
        ("Rent from", "rent_from", 15),
        ("Rent till", "rent_till", 15),
        ("Boat is insured", "boat_is_insured", 15),
        ("Boat is inspected", "boat_is_inspected", 15),
        ("Agree to terms", "agree_to_terms", 15),
        ("Application code", "application_code", 15),
    )

    output = io.BytesIO()

    wb = Workbook(output)
    ws = wb.add_worksheet(name="berth_applications")
    wrapped_cell_format = wb.add_format()
    wrapped_cell_format.set_text_wrap()

    header_format = wb.add_format({"bold": True})
    for column, field in enumerate(fields):
        ws.write(0, column, str(_(field[0])), header_format)
        ws.set_column(column, column, field[2])

    with translation.override(settings.LANGUAGES[0][0]):

        for row_number, application in enumerate(applications, 1):
            timestamp = application.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
            ws.write(row_number, 0, timestamp)

            harbor_choices = application.harborchoice_set.order_by("priority")
            choices_str = parse_choices_to_multiline_string(harbor_choices)
            ws.write(row_number, 1, choices_str, wrapped_cell_format)

            for column_number, field in enumerate(fields[2:], 2):
                attr_name = field[1]
                if attr_name == "boat_type" and (
                    boat_type := application.get_boat_type()
                ):
                    value = boat_type.name
                elif attr_name == "berth_switch" and application.berth_switch:
                    value = parse_berth_switch_str(application.berth_switch)
                elif attr_name == "berth_switch_reason":
                    value = None
                    if application.berth_switch:
                        value = (
                            application.berth_switch.reason.title
                            if application.berth_switch.reason
                            else "---"
                        )
                else:
                    value = getattr(application, attr_name)
                    if callable(value):
                        value = value()
                    if isinstance(value, bool):
                        value = "Yes" if value else ""

                ws.write(row_number, column_number, value)

    wb.close()

    return output.getvalue()


def export_winter_storage_applications_as_xlsx(applications):
    fields = (
        ("Reserved at", "created_at", 15),
        ("Chosen winter areas", "chosen_harbors", 55),
        ("Company name", "company_name", 35),
        ("Business ID", "business_id", 15),
        ("First name", "first_name", 15),
        ("Last name", "last_name", 15),
        ("Email", "email", 15),
        ("Address", "address", 15),
        ("Zip code", "zip_code", 15),
        ("Municipality", "municipality", 15),
        ("Phone number", "phone_number", 15),
        ("Storage method", "storage_method", 15),
        ("Trailer registration number", "trailer_registration_number", 15),
        ("Boat type", "boat_type", 15),
        ("Boat width", "get_boat_width", 15),
        ("Boat length", "get_boat_length", 15),
        ("Boat registration number", "get_boat_registration_number", 15),
        ("Boat name", "get_boat_name", 15),
        ("Boat model", "get_boat_model", 15),
        ("Accept boating newsletter", "accept_boating_newsletter", 15),
        ("Accept fitness news", "accept_fitness_news", 15),
        ("Accept library news", "accept_library_news", 15),
        ("Accept other culture news", "accept_other_culture_news", 15),
        ("Application code", "application_code", 15),
    )

    output = io.BytesIO()

    wb = Workbook(output)
    ws = wb.add_worksheet(name="winter_storage_applications")
    wrapped_cell_format = wb.add_format()
    wrapped_cell_format.set_text_wrap()

    header_format = wb.add_format({"bold": True})
    for column, field in enumerate(fields):
        ws.write(0, column, str(_(field[0])), header_format)
        ws.set_column(column, column, field[2])

    with translation.override(settings.LANGUAGES[0][0]):

        for row_number, application in enumerate(applications, 1):
            timestamp = application.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
            ws.write(row_number, 0, timestamp)

            winter_area_choices = application.winterstorageareachoice_set.order_by(
                "priority"
            )
            choices_str = parse_choices_to_multiline_string(winter_area_choices)
            ws.write(row_number, 1, choices_str, wrapped_cell_format)

            for column_number, field in enumerate(fields[2:], 2):
                attr_name = field[1]
                if attr_name == "boat_type" and (
                    boat_type := application.get_boat_type()
                ):
                    value = boat_type.name
                else:
                    value = getattr(application, attr_name)
                    if callable(value):
                        value = value()
                    if isinstance(value, bool):
                        value = "Yes" if value else ""
                    elif value in WinterStorageMethod:
                        status = WinterStorageMethod(value)
                        value = str(getattr(status, "label", str(status)))

                ws.write(row_number, column_number, value)

    wb.close()

    return output.getvalue()


def parse_choices_to_multiline_string(choices):
    """
    Turns a Queryset of HarborChoice or WinterStorageAreaChoice
    objects into a nice user-friendly string.

    Example of the returned string:

        '1: Aurinkosatama'
        '2: Mustikkamaan satama'

    :type choices: django.db.models.query.QuerySet
    :rtype: str
    """
    from .models import HarborChoice, WinterStorageAreaChoice

    choices_str = ""
    for choice in choices:
        if isinstance(choice, HarborChoice):
            single_choice_line = "{}: {}".format(choice.priority, choice.harbor.name)
        elif isinstance(choice, WinterStorageAreaChoice):
            single_choice_line = "{}: {}".format(
                choice.priority, choice.winter_storage_area.name
            )
        else:
            single_choice_line = ""

        if choices_str:
            choices_str += "\n" + single_choice_line
        else:
            choices_str += single_choice_line
    return choices_str


def parse_berth_switch_str(berth_switch):
    """
    Parse a string with berth switch information.

    Examples:

        'Aurinkosatama (B): 5'
        'Mustikkamaan satama: 6'

    :type berth_switch: applications.models.BerthSwitch
    :rtype: str
    """

    berth_switch_str = "{} ({}): {}".format(
        berth_switch.berth.pier.harbor.name,
        berth_switch.berth.pier.identifier,
        berth_switch.berth.number,
    )

    return berth_switch_str


def localize_datetime(dt, language=settings.LANGUAGES[0][0]):
    with translation.override(language):
        return dateformat.format(
            timezone.localtime(dt), formats.get_format("DATETIME_FORMAT", lang=language)
        )


def create_or_update_boat_for_application(application) -> (Boat, bool):
    def prop_or_none(prop):
        value = getattr(application, prop, None)
        if value == 0:
            value = None
        return value

    return Boat.objects.update_or_create(
        owner=application.customer,
        registration_number=application.boat_registration_number,
        defaults={
            "boat_type_id": application.boat_type_id,
            "length": application.boat_length,
            "width": application.boat_width,
            "registration_number": getattr(application, "boat_registration_number", ""),
            "name": getattr(application, "boat_name", ""),
            "model": getattr(application, "boat_model", ""),
            "draught": prop_or_none("boat_draught"),
            "weight": prop_or_none("boat_weight"),
            "propulsion": getattr(application, "boat_propulsion", ""),
            "hull_material": getattr(application, "boat_hull_material", ""),
            "intended_use": getattr(application, "boat_intended_use", ""),
        },
    )
