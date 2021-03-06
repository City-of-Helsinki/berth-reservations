from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from customers.models import CustomerProfile
from resources.models import Berth, BoatType, Harbor, WinterStorageArea

from .enums import ApplicationAreaType, ApplicationStatus, WinterStorageMethod
from .utils import localize_datetime


class HarborChoice(models.Model):
    harbor = models.ForeignKey(Harbor, on_delete=models.CASCADE)
    application = models.ForeignKey("BerthApplication", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(verbose_name=_("priority"))

    class Meta:
        unique_together = ("application", "priority")
        ordering = ("application", "priority")


class WinterStorageAreaChoice(models.Model):
    winter_storage_area = models.ForeignKey(WinterStorageArea, on_delete=models.CASCADE)
    application = models.ForeignKey(
        "WinterStorageApplication", on_delete=models.CASCADE
    )
    priority = models.PositiveSmallIntegerField(verbose_name=_("priority"))

    class Meta:
        unique_together = ("application", "priority")
        ordering = ("application", "priority")


class BerthSwitchReason(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(
            verbose_name=_("title"),
            max_length=64,
            blank=True,
            help_text=_("Title of the berth switch reason"),
        )
    )

    def __str__(self):
        return self.safe_translation_getter("title", super().__str__())


class BerthSwitch(models.Model):
    berth = models.ForeignKey(Berth, verbose_name=_("berth"), on_delete=models.CASCADE)
    reason = models.ForeignKey(
        BerthSwitchReason,
        null=True,
        blank=True,
        verbose_name=_("berth switch reason"),
        on_delete=models.SET_NULL,
    )


class BaseApplication(models.Model):
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    status = models.CharField(
        choices=ApplicationStatus.choices,
        verbose_name=_("handling status"),
        max_length=32,
        default=ApplicationStatus.PENDING,
    )

    language = models.CharField(
        verbose_name=_("language"),
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
    )

    # Applicant info
    first_name = models.CharField(verbose_name=_("first name"), max_length=40)
    last_name = models.CharField(verbose_name=_("last name"), max_length=150)
    email = models.EmailField(verbose_name=_("email address"))
    phone_number = models.CharField(verbose_name=_("phone number"), max_length=64)
    address = models.CharField(verbose_name=_("address"), max_length=150)
    zip_code = models.CharField(verbose_name=_("zip code"), max_length=64)
    municipality = models.CharField(verbose_name=_("municipality"), max_length=64)

    # Company info (if applicable)
    company_name = models.CharField(
        verbose_name=_("company name"), max_length=150, blank=True
    )
    business_id = models.CharField(
        verbose_name=_("business ID"), max_length=64, blank=True
    )

    # General boat info
    boat_type = models.ForeignKey(
        BoatType,
        verbose_name=_("boat type"),
        related_name="+",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    boat_registration_number = models.CharField(
        verbose_name=_("boat registration number"), max_length=64, blank=True
    )
    boat_name = models.CharField(verbose_name=_("boat name"), max_length=64, blank=True)
    boat_model = models.CharField(
        verbose_name=_("boat model"), max_length=64, blank=True
    )
    boat_length = models.DecimalField(
        verbose_name=_("boat length"),
        decimal_places=2,
        max_digits=5,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    boat_width = models.DecimalField(
        verbose_name=_("boat width"),
        decimal_places=2,
        max_digits=5,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    accept_boating_newsletter = models.BooleanField(
        verbose_name=_("accept boating newsletter"), default=False
    )
    accept_fitness_news = models.BooleanField(
        verbose_name=_("accept fitness news"), default=False
    )
    accept_library_news = models.BooleanField(
        verbose_name=_("accept library news"), default=False
    )
    accept_other_culture_news = models.BooleanField(
        verbose_name=_("accept other culture news"), default=False
    )

    information_accuracy_confirmed = models.BooleanField(
        verbose_name=_("information accuracy confirmed"), default=False
    )

    application_code = models.TextField(verbose_name=_("application code"), blank=True)

    class Meta:
        abstract = True
        permissions = (
            ("resend_application", _("Can resend confirmation for applications")),
        )

    def __str__(self):
        return "{}: {} {}".format(self.pk, self.first_name, self.last_name)


class BerthApplication(BaseApplication):
    customer = models.ForeignKey(
        CustomerProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="berth_applications",
    )

    chosen_harbors = models.ManyToManyField(
        Harbor, through=HarborChoice, verbose_name=_("chosen harbors"), blank=True
    )

    berth_switch = models.ForeignKey(
        BerthSwitch,
        verbose_name=_("berth switch"),
        related_name="applications",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # Extra boat dimensions
    boat_draught = models.DecimalField(
        verbose_name=_("boat draught"),
        decimal_places=2,
        max_digits=5,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    boat_weight = models.DecimalField(
        verbose_name=_("boat weight"),
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    accessibility_required = models.BooleanField(
        verbose_name=_("accessibility required"), default=False
    )

    # Large vessel specific info (if applicable)
    boat_propulsion = models.CharField(
        verbose_name=_("boat propulsion"), max_length=64, blank=True
    )
    boat_hull_material = models.CharField(
        verbose_name=_("boat hull material"), max_length=64, blank=True
    )
    boat_intended_use = models.CharField(
        verbose_name=_("boat intended use"), max_length=150, blank=True
    )
    renting_period = models.CharField(
        verbose_name=_("renting period"), max_length=64, blank=True
    )
    rent_from = models.CharField(verbose_name=_("rent from"), max_length=64, blank=True)
    rent_till = models.CharField(verbose_name=_("rent till"), max_length=64, blank=True)
    boat_is_inspected = models.BooleanField(
        verbose_name=_("boat is inspected"), null=True, blank=True
    )
    boat_is_insured = models.BooleanField(
        verbose_name=_("boat is insured"), null=True, blank=True
    )
    agree_to_terms = models.BooleanField(
        verbose_name=_("agree to terms"), null=True, blank=True
    )

    def get_notification_context(self):
        return {
            "created_at": localize_datetime(self.created_at, self.language),
            "harbor_choices": self.harborchoice_set.order_by("priority"),
            "application": self,
        }

    def _validate_status(self):
        """
        * If the BerthApplication it is a switch application, then the set of available statuses is restricted
        * If the BerthApplication does not have a BerthLease related to it,
          it can only have PENDING, EXPIRED or NO_SUITABLE_BERTHS statuses.
        """
        if self.berth_switch:
            allowed_statuses_for_switch = [
                ApplicationStatus.PENDING,
                ApplicationStatus.OFFER_GENERATED,
                ApplicationStatus.OFFER_SENT,
                ApplicationStatus.EXPIRED,
                ApplicationStatus.REJECTED,
            ]
            if self.status not in allowed_statuses_for_switch:
                raise ValidationError(
                    _(
                        "Berth switch application can only be "
                        f"{', '.join([status.name for status in allowed_statuses_for_switch])}; "
                        f"has {self.status.name}"
                    )
                )
        else:
            # not a switch application
            allowed_statuses_without_lease = [
                ApplicationStatus.PENDING,
                ApplicationStatus.EXPIRED,
                ApplicationStatus.NO_SUITABLE_BERTHS,
            ]

            if (
                not hasattr(self, "lease")
                and self.status not in allowed_statuses_without_lease
            ):
                raise ValidationError(
                    _(
                        "BerthApplication with no lease can only be "
                        f"{', '.join([status.name for status in allowed_statuses_without_lease])}; "
                        f"has {self.status.name}"
                    )
                )

    def save(self, *args, **kwargs):
        fields_to_strip = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "zip_code",
            "municipality",
            "company_name",
            "business_id",
            "boat_registration_number",
            "boat_name",
            "boat_model",
            "application_code",
            "boat_propulsion",
            "boat_hull_material",
            "boat_intended_use",
            "renting_period",
            "rent_from",
            "rent_till",
        ]
        for field in fields_to_strip:
            if field_value := getattr(self, field):
                setattr(self, field, field_value.strip())

        # Ensure clean is always ran
        # FIXME: exclude decimal fields for now, as GQL API uses floats for those
        #  which does not work well with Django's validation for DecimalField
        self.full_clean(exclude=["boat_length", "boat_width", "boat_draught"])
        super().save(*args, **kwargs)

    def clean(self):
        self._validate_status()


class WinterStorageApplication(BaseApplication):
    area_type = models.CharField(
        choices=ApplicationAreaType.choices,
        verbose_name=_("application area type"),
        max_length=30,
        null=True,
    )

    customer = models.ForeignKey(
        CustomerProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="winter_storage_applications",
    )

    chosen_areas = models.ManyToManyField(
        WinterStorageArea,
        through=WinterStorageAreaChoice,
        verbose_name=_("chosen winter storage areas"),
        blank=True,
    )

    storage_method = models.CharField(
        choices=WinterStorageMethod.choices,
        verbose_name=_("storage method"),
        max_length=60,
    )

    # If boat stored on a trailer, trailer's registration number is required
    trailer_registration_number = models.CharField(
        verbose_name=_("trailer registration number"), max_length=64, blank=True
    )

    def save(self, *args, **kwargs):
        fields_to_strip = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "zip_code",
            "municipality",
            "company_name",
            "business_id",
            "boat_registration_number",
            "boat_name",
            "boat_model",
            "application_code",
            "trailer_registration_number",
        ]
        for field in fields_to_strip:
            if field_value := getattr(self, field):
                setattr(self, field, field_value.strip())
        super().save(*args, **kwargs)

    def resolve_area_type(self) -> ApplicationAreaType:
        first_area = self.chosen_areas.first()

        is_unmarked_area = bool(
            self.chosen_areas.count() == 1
            and first_area.estimated_number_of_unmarked_spaces
            and first_area.estimated_number_of_unmarked_spaces > 0
        )

        return (
            ApplicationAreaType.UNMARKED
            if is_unmarked_area
            else ApplicationAreaType.MARKED
        )

    def get_notification_context(self):
        return {
            "created_at": localize_datetime(self.created_at, self.language),
            "area_choices": self.winterstorageareachoice_set.order_by("priority"),
            "application": self,
        }
