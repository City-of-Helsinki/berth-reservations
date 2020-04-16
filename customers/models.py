import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from resources.models import BoatType
from utils.models import TimeStampedModel, UUIDModel

from .enums import InvoicingType, OrganizationType

User = get_user_model()


class CustomerProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    invoicing_type = EnumField(
        InvoicingType,
        verbose_name=_("invoicing type"),
        max_length=30,
        default=InvoicingType.ONLINE_PAYMENT,
    )
    comment = models.TextField(verbose_name=_("comment"), blank=True)

    class Meta:
        verbose_name = _("customer profile")
        verbose_name_plural = _("customer profiles")
        ordering = ("id",)

    def __str__(self):
        if self.user:
            return "{} {} ({})".format(
                self.user.first_name, self.user.last_name, self.id
            )
        else:
            return str(self.id)


class Organization(TimeStampedModel, UUIDModel):
    customer = models.OneToOneField(
        CustomerProfile,
        verbose_name=_("customer"),
        related_name="organization",
        on_delete=models.CASCADE,
    )
    organization_type = EnumField(
        OrganizationType, verbose_name=_("organization type"), max_length=16,
    )
    business_id = models.CharField(
        verbose_name=_("business id"), max_length=32, blank=True
    )
    name = models.CharField(verbose_name=_("name"), max_length=128, blank=True)
    address = models.CharField(verbose_name=_("address"), max_length=128, blank=True)
    postal_code = models.CharField(
        verbose_name=_("postal code"), max_length=5, blank=True
    )
    city = models.CharField(verbose_name=_("city"), max_length=64, blank=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ("id",)

    def save(self, *args, **kwargs):
        # ensure full_clean is always ran
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.organization_type == OrganizationType.COMPANY and not self.business_id:
            raise ValidationError(_("A company must have a business id"))

    def __str__(self):
        return (
            f"[{self.organization_type}]: {self.name} [{self.business_id}] ({self.id})"
        )


class Boat(TimeStampedModel, UUIDModel):
    owner = models.ForeignKey(
        CustomerProfile,
        verbose_name=_("owner"),
        on_delete=models.CASCADE,
        related_name="boats",
    )
    boat_type = models.ForeignKey(
        BoatType,
        verbose_name=_("boat type"),
        on_delete=models.PROTECT,
        related_name="boats",
    )

    # General boat info
    registration_number = models.CharField(
        verbose_name=_("registration number"), max_length=64, blank=True
    )
    name = models.CharField(verbose_name=_("boat name"), max_length=255, blank=True)
    model = models.CharField(verbose_name=_("model"), max_length=64, blank=True)

    # Dimensions
    length = models.DecimalField(
        verbose_name=_("length (m)"),
        decimal_places=2,
        max_digits=5,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    width = models.DecimalField(
        verbose_name=_("width (m)"),
        decimal_places=2,
        max_digits=5,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    draught = models.DecimalField(
        verbose_name=_("draught (m)"),
        decimal_places=2,
        max_digits=5,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    weight = models.PositiveIntegerField(
        verbose_name=_("weight (kg)"), null=True, blank=True,
    )

    # Large vessel specific info (if applicable)
    propulsion = models.CharField(
        verbose_name=_("propulsion"), max_length=64, blank=True
    )
    hull_material = models.CharField(
        verbose_name=_("hull material"), max_length=64, blank=True
    )

    boat_is_inspected = models.BooleanField(
        verbose_name=_("boat is inspected"), null=True, blank=True
    )
    boat_is_insured = models.BooleanField(
        verbose_name=_("boat is insured"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("boat")
        verbose_name_plural = _("boats")
        ordering = ("owner",)

    def __str__(self):
        return "{} ({})".format(self.registration_number, self.pk)
