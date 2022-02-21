import io

from django.db.models import Prefetch, QuerySet
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from applications.enums import WinterStorageMethod
from applications.models import (
    BerthApplication,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)
from customers.enums import InvoicingType
from customers.models import CustomerProfile
from customers.services import ProfileService
from exports.utils import parse_berth_switch_str, parse_choices_to_multiline_string


class BaseExportXlsxWriter:

    content_start_index = 1
    identifier = "export"
    title = _("export")

    fields = []
    wrapped_fields = []  # Fields with wrapped text formatting

    def __init__(self, queryset: QuerySet, **kwargs):
        """Export the given queryset of items into an Excel.

        Example for fields:

        fields = [
            ("id", _("ID"), 15),
            ("first_name", _("First name"), 15),
        ]
        """
        self.queryset = queryset

    @property
    def filename(self):
        timestamp = timezone.localtime().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{self.identifier}-{timestamp}"

    def _write_header_row(self, workbook, sheet):
        header_format = workbook.add_format({"bold": True})
        for column, field in enumerate(self.fields):
            field_name, verbose_name, width = field
            sheet.write(0, column, str(verbose_name).capitalize(), header_format)
            sheet.set_column(column, column, width)

    def _write_rows(self, workbook, sheet):
        wrapped_cell_format = workbook.add_format()
        wrapped_cell_format.set_text_wrap()

        column_index = [
            (index, field_name)
            for index, (field_name, verbose_name, width) in enumerate(self.fields)
        ]

        for row_index, item in enumerate(self.queryset, self.content_start_index):
            for col_index, field_name in column_index:
                value = self.get_value(field_name, item)
                if field_name in self.wrapped_fields:
                    sheet.write(row_index, col_index, value, wrapped_cell_format)
                else:
                    sheet.write(row_index, col_index, value)

    def get_value(self, field_name, item):
        """Get value for a specific field in Excel."""
        raise NotImplementedError

    def get_optimized_queryset(self):
        """This method can be used to optimize the queryset with prefetches etc."""
        return self.queryset

    def serialize(self):
        self.queryset = self.get_optimized_queryset()
        output = io.BytesIO()

        workbook = Workbook(
            output,
            {
                "constant_memory": True,
                "remove_timezone": True,
                "default_date_format": "YYYY-MM-DD HH:MM:SS",
            },
        )
        worksheet = workbook.add_worksheet(name=str(self.title).capitalize())

        self._write_header_row(workbook, worksheet)
        self._write_rows(workbook, worksheet)

        workbook.close()

        return output.getvalue()


class CustomerXlsx(BaseExportXlsxWriter):
    identifier = "customers"
    title = _("customers")
    fields = (
        ("id", _("id"), 37),
        ("first_name", _("first name"), 15),
        ("last_name", _("last name"), 15),
        ("invoicing_type", _("invoicing type"), 15),
        ("customer_group", _("customer group"), 15),
        ("email", _("email"), 25),
        ("phone", _("phone"), 15),
        ("address", _("address"), 25),
        ("postal_code", _("postal code"), 6),
        ("city", _("city"), 15),
        ("comment", _("comment"), 15),
        ("created_at", _("time created"), 19),
        ("modified_at", _("time modified"), 19),
        ("user_source", _("user source"), 19),
    )

    helsinki_profile_values = {}
    helsinki_profile_field = {
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "postal_code",
        "city",
    }

    def __init__(self, queryset, profile_token: str = None, **kwargs):
        super().__init__(queryset, **kwargs)
        self.profile_service = ProfileService(profile_token) if profile_token else None

    def serialize(self):
        if self.profile_service:
            profile_ids = self.queryset.values_list("id", flat=True)
            self.helsinki_profile_values = self.profile_service.get_all_profiles(
                profile_ids
            )
        return super().serialize()

    def get_value(self, field_name, item: CustomerProfile):  # noqa: C901
        """Return the value for the given field name."""
        fallback_value = getattr(item, field_name, "")

        if (
            field_name in self.helsinki_profile_field
            and item.id in self.helsinki_profile_values
        ):
            hp_item = self.helsinki_profile_values[item.id]
            if field_name == "first_name":
                return hp_item.first_name
            elif field_name == "last_name":
                return hp_item.last_name
            elif field_name == "email":
                return hp_item.email
            elif field_name == "phone":
                return hp_item.phone
            elif field_name == "address":
                return hp_item.address
            elif field_name == "postal_code":
                return hp_item.postal_code
            elif field_name == "city":
                return hp_item.city

        if field_name == "id":
            return str(fallback_value)
        elif field_name == "first_name":
            return item.user.first_name if item.user else ""
        elif field_name == "last_name":
            return item.user.last_name if item.user else ""
        elif field_name == "invoicing_type":
            return str(InvoicingType(item.invoicing_type).label)
        elif field_name == "created_at":
            return localtime(item.created_at)
        elif field_name == "modified_at":
            return localtime(item.modified_at)

        if field_name == "user_source":
            if item.id in self.helsinki_profile_values:
                return str(_("Helsinki profile"))
            else:
                return str(_("Local"))
        return fallback_value

    def get_optimized_queryset(self):
        qs = super().get_optimized_queryset()
        return qs.select_related("user")


class BerthApplicationXlsx(BaseExportXlsxWriter):
    identifier = "berth_applications"
    title = _("berth applications")
    fields = (
        # Common fields
        ("created_at", _("reserved at"), 15),
        ("chosen_harbors", _("chosen harbors"), 55),
        ("berth_switch", _("current berth"), 35),
        ("berth_switch_reason", _("wwitch Reason"), 55),
        ("company_name", _("company name"), 35),
        ("business_id", _("business ID"), 15),
        ("first_name", _("first name"), 15),
        ("last_name", _("last name"), 15),
        ("email", _("email"), 15),
        ("address", _("address"), 15),
        ("zip_code", _("zip code"), 15),
        ("municipality", _("municipality"), 15),
        ("phone_number", _("phone number"), 15),
        ("boat_type", _("boat type"), 15),
        ("boat_width", _("boat width"), 15),
        ("boat_length", _("boat length"), 15),
        ("boat_draught", _("boat draught"), 15),
        ("boat_weight", _("boat weight"), 15),
        ("boat_registration_number", _("boat registration number"), 15),
        ("boat_name", _("boat name"), 15),
        ("boat_model", _("boat model"), 15),
        ("accessibility_required", _("accessibility required"), 15),
        ("accept_boating_newsletter", _("accept boating newsletter"), 15),
        ("accept_fitness_news", _("accept fitness news"), 15),
        ("accept_library_news", _("accept library news"), 15),
        ("accept_other_culture_news", _("accept other culture news"), 15),
        # Big boat specific fields
        ("boat_hull_material", _("boat hull material"), 15),
        ("boat_intended_use", _("boat intended use"), 15),
        ("renting_period", _("renting period"), 15),
        ("rent_from", _("rent from"), 15),
        ("rent_till", _("rent till"), 15),
        ("boat_is_insured", _("boat is insured"), 15),
        ("boat_is_inspected", _("boat is inspected"), 15),
        ("agree_to_terms", _("agree to terms"), 15),
        ("application_code", _("application code"), 15),
    )
    wrapped_fields = ("chosen_harbors",)

    def get_value(self, field_name, item: BerthApplication):
        fallback_value = getattr(item, field_name, "")

        if field_name == "created_at":
            return item.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
        elif field_name == "chosen_harbors":
            return parse_choices_to_multiline_string(item.harborchoice_set.all())
        elif field_name == "berth_switch" and item.berth_switch:
            return parse_berth_switch_str(item.berth_switch)

        elif field_name == "berth_switch_reason" and item.berth_switch:
            return item.berth_switch.reason.title if item.berth_switch.reason else "---"
        elif field_name == "boat_type":
            return item.boat_type.name

        if isinstance(fallback_value, bool):
            return "Yes" if fallback_value else ""
        return fallback_value

    def get_optimized_queryset(self):
        qs = super().get_optimized_queryset()
        return qs.prefetch_related(
            Prefetch(
                "harborchoice_set",
                queryset=HarborChoice.objects.order_by("priority").select_related(
                    "harbor"
                ),
            ),
            "berth_switch__reason__translations",
        ).select_related(
            "boat",
            "boat__boat_type",
            "berth_switch",
            "berth_switch__reason",
            "berth_switch__berth__pier__harbor",
        )


class WinterStorageApplicationXlsx(BaseExportXlsxWriter):
    identifier = "winter_storage_applications"
    title = _("winter storage applications")
    fields = (
        ("created_at", _("reserved at"), 15),
        ("chosen_harbors", _("chosen winter areas"), 55),
        ("company_name", _("company name"), 35),
        ("business_id", _("business ID"), 15),
        ("first_name", _("first name"), 15),
        ("last_name", _("last name"), 15),
        ("email", _("email"), 15),
        ("address", _("address"), 15),
        ("zip_code", _("zip code"), 15),
        ("municipality", _("municipality"), 15),
        ("phone_number", _("phone number"), 15),
        ("storage_method", _("storage method"), 15),
        ("trailer_registration_number", _("trailer registration number"), 15),
        ("boat_type", _("boat type"), 15),
        ("boat_width", _("boat width"), 15),
        ("boat_length", _("boat length"), 15),
        ("boat_registration_number", _("boat registration number"), 15),
        ("boat_name", _("boat name"), 15),
        ("boat_model", _("boat model"), 15),
        ("accept_boating_newsletter", _("accept boating newsletter"), 15),
        ("accept_fitness_news", _("accept fitness news"), 15),
        ("accept_library_news", _("accept library news"), 15),
        ("accept_other_culture_news", _("accept other culture news"), 15),
        ("application_code", _("application code"), 15),
    )
    wrapped_fields = ("chosen_harbors",)

    def get_value(self, field_name, item: WinterStorageApplication):
        fallback_value = getattr(item, field_name, "")

        if field_name == "created_at":
            return item.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
        elif field_name == "chosen_harbors":
            return parse_choices_to_multiline_string(
                item.winterstorageareachoice_set.all()
            )
        elif field_name == "boat_type":
            return item.boat_type.name
        elif field_name == "storage_method":
            storage_method = WinterStorageMethod(fallback_value)
            return str(getattr(storage_method, "label", str(storage_method)))

        if isinstance(fallback_value, bool):
            return "Yes" if fallback_value else ""
        return fallback_value

    def get_optimized_queryset(self):
        qs = super().get_optimized_queryset()
        return qs.prefetch_related(
            Prefetch(
                "winterstorageareachoice_set",
                queryset=WinterStorageAreaChoice.objects.order_by(
                    "priority"
                ).select_related("winter_storage_area"),
            ),
        ).select_related("boat", "boat__boat_type")
