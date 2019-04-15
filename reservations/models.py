from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from harbors.models import BoatType, Harbor

from .utils import localize_datetime


class HarborChoice(models.Model):
    harbor = models.ForeignKey(Harbor, on_delete=models.CASCADE)
    reservation = models.ForeignKey("Reservation", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(verbose_name=_("priority"))

    class Meta:
        unique_together = ("reservation", "priority")


class Reservation(models.Model):
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    is_processed = models.BooleanField(verbose_name=_("is processed"), default=False)

    language = models.CharField(
        verbose_name=_("language"),
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
    )

    chosen_harbors = models.ManyToManyField(
        Harbor, through=HarborChoice, verbose_name=_("chosen harbors"), blank=True
    )

    # Applicant info
    first_name = models.CharField(
        verbose_name=_("first name"), max_length=40, blank=True
    )
    last_name = models.CharField(
        verbose_name=_("last name"), max_length=150, blank=True
    )
    email = models.EmailField(verbose_name=_("email address"), blank=True)
    phone_number = models.CharField(
        verbose_name=_("phone number"), max_length=64, blank=True
    )
    address = models.CharField(verbose_name=_("address"), max_length=150, blank=True)
    zip_code = models.CharField(verbose_name=_("zip code"), max_length=64, blank=True)
    municipality = models.CharField(
        verbose_name=_("municipality"), max_length=64, blank=True
    )

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
        related_name="reservations",
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
        null=True,
        blank=True,
    )
    boat_width = models.DecimalField(
        verbose_name=_("boat width"),
        decimal_places=2,
        max_digits=5,
        null=True,
        blank=True,
    )
    boat_draught = models.DecimalField(
        verbose_name=_("boat draught"),
        decimal_places=2,
        max_digits=5,
        null=True,
        blank=True,
    )
    boat_weight = models.DecimalField(
        verbose_name=_("boat weight"),
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
    )
    accessibility_required = models.BooleanField(
        verbose_name=_("accessibility required"), default=False
    )

    # Large vessel specific info
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

    data = JSONField(blank=True, null=True)

    application_code = models.TextField(verbose_name=_("application code"), blank=True)

    class Meta:
        permissions = (
            ("resend_reservation", _("Can resend confirmation for reservations")),
        )

    def __str__(self):
        return "{}: {} {}".format(self.pk, self.first_name, self.last_name)

    def get_notification_context(self):
        return {
            "created_at": localize_datetime(self.created_at, self.language),
            "harbor_choices": self.harborchoice_set.order_by("priority"),
            "reservation": self,
        }
