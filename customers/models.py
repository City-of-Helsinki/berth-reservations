from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from utils.models import TimeStampedModel, UUIDModel

from .enums import InvoicingType

User = get_user_model()


class CustomerProfile(TimeStampedModel, UUIDModel):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    invoicing_type = EnumField(
        InvoicingType, verbose_name=_("invoicing type"), max_length=30
    )
    comment = models.TextField(verbose_name=_("comment"), blank=True)

    def __str__(self):
        if self.user:
            return "{} {} ({})".format(
                self.user.first_name, self.user.last_name, self.id
            )
        else:
            return self.id
