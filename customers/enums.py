from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class InvoicingType(Enum):
    ONLINE_PAYMENT = "online-payment"
    DIGITAL_INVOICE = "digital-invoice"
    PAPER_INVOICE = "paper-invoice"

    class Labels:
        ONLINE_PAYMENT = _("Online payment")
        DIGITAL_INVOICE = _("Digital invoice")
        PAPER_INVOICE = _("Paper invoice")


class OrganizationType(Enum):
    COMPANY = "company"
    INTERNAL = "internal"
    NON_BILLABLE = "non-billable"
    OTHER = "other"

    class Labels:
        COMPANY = _("Company")
        INTERNAL = _("Internal")
        NON_BILLABLE = _("Non-billable")
        OTHER = _("Other")
