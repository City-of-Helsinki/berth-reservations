from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class InvoicingType(TextChoices):
    ONLINE_PAYMENT = "online-payment", _("Online payment")
    DIGITAL_INVOICE = "digital-invoice", _("Digital invoice")
    PAPER_INVOICE = "paper-invoice", _("Paper invoice")


class OrganizationType(TextChoices):
    COMPANY = "company", _("Company")
    INTERNAL = "internal", _("Internal")
    NON_BILLABLE = "non-billable", _("Non-billable")
    OTHER = "other", _("Other")


class BoatCertificateType(TextChoices):
    INSPECTION = "inspection", _("Inspection")
    INSURANCE = "insurance", _("Insurance")
