import io

from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from customers.enums import InvoicingType
from customers.models import CustomerProfile
from customers.services import ProfileService


class BaseExportXlsxWriter:

    content_start_index = 1
    identifier = "export"
    title = _("Export")

    fields = []

    def __init__(self, items, **kwargs):
        """Export the given set of items into an Excel.

        Example for fields:

        fields = [
            ("id", _("ID"), 15),
            ("first_name", _("First name"), 15),
        ]
        """
        self.items = items

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

        for row_index, item in enumerate(self.items, self.content_start_index):
            for col_index, field_name in column_index:
                value = self.get_value(field_name, item)
                sheet.write(row_index, col_index, value)

    def get_value(self, field_name, item):
        """Get value for a specific field in Excel."""
        raise NotImplementedError

    def serialize(self):
        output = io.BytesIO()

        workbook = Workbook(
            output,
            {
                "constant_memory": True,
                "remove_timezone": True,
                "default_date_format": "YYYY-MM-DD HH:MM:SS",
            },
        )
        worksheet = workbook.add_worksheet(name=str(self.title))

        self._write_header_row(workbook, worksheet)
        self._write_rows(workbook, worksheet)

        workbook.close()

        return output.getvalue()


class CustomerXlsx(BaseExportXlsxWriter):
    identifier = "customers"
    title = _("Customers")
    fields = [
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
    ]

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

    def __init__(self, items, profile_token: str = None, **kwargs):
        super().__init__(items, **kwargs)
        self.profile_service = ProfileService(profile_token) if profile_token else None

    def serialize(self):
        if self.profile_service:
            profile_ids = self.items.values_list("id", flat=True)
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
