from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from berth_reservations.mixins import ChoicesMixin


class InvoicingType(ChoicesMixin, TextChoices):
    ONLINE_PAYMENT = "online-payment", _("Online payment")
    PAPER_INVOICE = "paper-invoice", _("Paper invoice")


class OrganizationType(ChoicesMixin, TextChoices):
    COMPANY = "company", _("Company")
    INTERNAL = "internal", _("Internal")
    NON_BILLABLE = "non-billable", _("Non-billable")
    OTHER = "other", _("Other")


class BoatCertificateType(ChoicesMixin, TextChoices):
    INSPECTION = "inspection", _("Inspection")
    INSURANCE = "insurance", _("Insurance")
