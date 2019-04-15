import io

from django.conf import settings
from django.utils import dateformat, formats, timezone, translation
from django.utils.translation import ugettext_lazy as _
from xlsxwriter import Workbook


def export_reservations_as_xlsx(reservations):
    fields = (
        # Common fields
        ("Reserved at", "created_at", 15),
        ("Chosen harbors", "chosen_harbors", 55),
        ("First name", "first_name", 15),
        ("Last name", "last_name", 15),
        ("Email", "email", 15),
        ("Address", "address", 15),
        ("Zip code", "zip_code", 15),
        ("Municipality", "municipality", 15),
        ("Phone number", "phone_number", 15),
        ("Boat type", "boat_type", 15),
        ("Boat width", "boat_width", 15),
        ("Boat length", "boat_length", 15),
        ("Boat draught", "boat_draught", 15),
        ("Boat weight", "boat_weight", 15),
        ("Boat registration number", "boat_registration_number", 15),
        ("Boat name", "boat_name", 15),
        ("Boat model", "boat_model", 15),
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
    ws = wb.add_worksheet(name="berth_reservations")
    wrapped_cell_format = wb.add_format()
    wrapped_cell_format.set_text_wrap()

    header_format = wb.add_format({"bold": True})
    for column, field in enumerate(fields):
        ws.write(0, column, str(_(field[0])), header_format)
        ws.set_column(column, column, field[2])

    with translation.override(settings.LANGUAGES[0][0]):

        for row_number, reservation in enumerate(reservations, 1):
            timestamp = reservation.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
            ws.write(row_number, 0, timestamp)

            harbor_choices = reservation.harborchoice_set.order_by("priority")
            choices_str = parse_harbor_choices_to_multiline_string(harbor_choices)
            ws.write(row_number, 1, choices_str, wrapped_cell_format)

            for column_number, field in enumerate(fields[2:], 2):
                attr_name = field[1]
                if attr_name == "boat_type" and reservation.boat_type:
                    value = reservation.boat_type.name
                else:
                    value = getattr(reservation, attr_name)
                    if isinstance(value, bool):
                        value = "Yes" if value else ""

                ws.write(row_number, column_number, value)

    wb.close()

    return output.getvalue()


def parse_harbor_choices_to_multiline_string(choices):
    """
    Turns a Queryset of HarborChoice objects into a nice
    user-friendly string.

    Example of the returned string:

        '1: Aurinkosatama'
        '2: Mustikkamaan satama'

    :type choices: django.db.models.query.QuerySet
    :rtype: str
    """
    harbor_choices_str = ""
    for choice in choices:
        single_choice_line = "{}: {}".format(choice.priority, choice.harbor.name)
        if harbor_choices_str:
            harbor_choices_str += "\n" + single_choice_line
        else:
            harbor_choices_str += single_choice_line
    return harbor_choices_str


def localize_datetime(dt, language=settings.LANGUAGES[0][0]):
    with translation.override(language):
        return dateformat.format(
            timezone.localtime(dt), formats.get_format("DATETIME_FORMAT", lang=language)
        )
