from babel.dates import format_date
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from helsinki_gdpr.models import SerializableMixin
from parler.models import TranslatableModel, TranslatedFields

from customers.models import Boat, CustomerProfile
from resources.models import Berth, Harbor, WinterStorageArea
from utils.models import TimeStampedModel, UUIDModel

from .enums import (
    ApplicationAreaType,
    ApplicationPriority,
    ApplicationStatus,
    WinterStorageMethod,
)
from .utils import localize_datetime


class HarborChoice(SerializableMixin):
    harbor = models.ForeignKey(Harbor, on_delete=models.CASCADE)
    application = models.ForeignKey("BerthApplication", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(verbose_name=_("priority"))

    class Meta:
        unique_together = ("application", "priority")
        ordering = ("application", "priority")

    serialize_fields = ({"name": "harbor", "accessor": lambda x: x.name},)

    def __str__(self):
        return f"{self.priority}: {self.harbor.name}"


class WinterStorageAreaChoice(SerializableMixin):
    winter_storage_area = models.ForeignKey(WinterStorageArea, on_delete=models.CASCADE)
    application = models.ForeignKey(
        "WinterStorageApplication", on_delete=models.CASCADE
    )
    priority = models.PositiveSmallIntegerField(verbose_name=_("priority"))

    class Meta:
        unique_together = ("application", "priority")
        ordering = ("application", "priority")

    serialize_fields = ({"name": "winter_storage_area", "accessor": lambda x: x.name},)

    def __str__(self):
        return f"{self.priority}: {self.winter_storage_area.name}"


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


class BerthSwitch(SerializableMixin):
    berth = models.ForeignKey(Berth, verbose_name=_("berth"), on_delete=models.CASCADE)
    reason = models.ForeignKey(
        BerthSwitchReason,
        null=True,
        blank=True,
        verbose_name=_("berth switch reason"),
        on_delete=models.SET_NULL,
    )

    serialize_fields = (
        {"name": "berth", "accessor": lambda x: x.serialize() if x else None},
        {"name": "reason", "accessor": lambda x: x.title if x else None},
    )


class BaseApplication(models.Model):
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    status = models.CharField(
        choices=ApplicationStatus.choices,
        verbose_name=_("handling status"),
        max_length=32,
        default=ApplicationStatus.PENDING,
    )

    priority = models.PositiveSmallIntegerField(
        choices=ApplicationPriority.choices,
        verbose_name=_("priority"),
        default=ApplicationPriority.MEDIUM,
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

    boat = models.ForeignKey(Boat, verbose_name=_("boat"), on_delete=models.PROTECT)
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

    @property
    def boat_type(self):
        return self.boat.boat_type

    @property
    def boat_registration_number(self):
        return self.boat.registration_number

    @property
    def boat_name(self):
        return self.boat.name

    @property
    def boat_model(self):
        return self.boat.model

    @property
    def boat_length(self):
        return self.boat.length

    @property
    def boat_width(self):
        return self.boat.width

    class Meta:
        abstract = True
        ordering = ("-priority", "created_at")
        permissions = (
            ("resend_application", _("Can resend confirmation for applications")),
        )

    def __str__(self):
        return "{}: {} {}".format(self.pk, self.first_name, self.last_name)

    def clean(self):
        if self.customer and self.boat.owner != self.customer:
            raise ValidationError(
                _("The boat should belong to the customer of the application")
            )


class BaseApplicationChange(TimeStampedModel, UUIDModel):
    change_list = models.TextField(verbose_name="change list")

    class Meta:
        abstract = True
        ordering = (
            "created_at",
            "change_list",
        )

    def __str__(self):
        return f"{format_date(self.created_at, locale='fi')}\n{self.change_list}"


class BerthApplicationChange(BaseApplicationChange):
    application = models.ForeignKey(
        "BerthApplication", on_delete=models.CASCADE, related_name="changes"
    )


class WinterStorageApplicationChange(BaseApplicationChange):
    application = models.ForeignKey(
        "WinterStorageApplication", on_delete=models.CASCADE, related_name="changes"
    )


class BerthApplicationManager(SerializableMixin.SerializableManager):
    def reset_application_priority(
        self, only_low_priority: bool = False, dry_run: bool = False
    ):
        # MEDIUM priority applications don't have to be modified either way
        qs = self.get_queryset().exclude(priority=ApplicationPriority.MEDIUM)

        if only_low_priority:
            # If only the low priority are required, we exclude the HIGH priority ones
            # to avoid modifying them
            qs = qs.exclude(priority=ApplicationPriority.HIGH)

        if dry_run:
            return qs.count()

        return qs.update(priority=ApplicationPriority.MEDIUM)


class BerthApplication(BaseApplication, SerializableMixin):
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
    accessibility_required = models.BooleanField(
        verbose_name=_("accessibility required"), default=False
    )
    renting_period = models.CharField(
        verbose_name=_("renting period"), max_length=64, blank=True
    )
    rent_from = models.CharField(verbose_name=_("rent from"), max_length=64, blank=True)
    rent_till = models.CharField(verbose_name=_("rent till"), max_length=64, blank=True)
    agree_to_terms = models.BooleanField(
        verbose_name=_("agree to terms"), null=True, blank=True
    )

    objects = BerthApplicationManager()

    @property
    def boat_draught(self):
        return self.boat.draught

    @property
    def boat_weight(self):
        return self.boat.weight

    @property
    def boat_propulsion(self):
        return self.boat.propulsion

    @property
    def boat_hull_material(self):
        return self.boat.hull_material

    @property
    def boat_intended_use(self):
        return self.boat.intended_use

    @property
    def boat_is_inspected(self):
        return self.boat.is_inspected

    @property
    def boat_is_insured(self):
        return self.boat.is_insured

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

    def create_change_entry(self):
        fields_to_compare = [
            "status",
            "language",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "zip_code",
            "municipality",
            "company_name",
            "business_id",
            "boat_id",
            "accept_boating_newsletter",
            "accept_fitness_news",
            "accept_library_news",
            "accept_other_culture_news",
            "information_accuracy_confirmed",
            "application_code",
            "berth_switch",
            "accessibility_required",
            "renting_period",
            "rent_from",
            "rent_till",
            "agree_to_terms",
        ]

        creating = self._state.adding
        if not creating:
            old_instance = BerthApplication.objects.get(id=self.id)

            change_list = ""
            for field in fields_to_compare:
                old_value = getattr(old_instance, field, "[Empty]")
                new_value = getattr(self, field, "[Empty]")
                if old_value != new_value:
                    field_name = BerthApplication._meta.get_field(
                        field
                    ).verbose_name.capitalize()
                    change_list += f"{field_name}: {old_value} -> {new_value}\n"

            if len(change_list) > 0:
                BerthApplicationChange.objects.create(
                    application=self, change_list=change_list
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
            "application_code",
            "renting_period",
            "rent_from",
            "rent_till",
        ]
        for field in fields_to_strip:
            if field_value := getattr(self, field):
                setattr(self, field, field_value.strip())

        self.create_change_entry()

        # Ensure clean is always ran
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self._validate_status()

    serialize_fields = (
        {"name": "id"},
        {"name": "created_at", "accessor": lambda x: x.strftime("%d-%m-%Y %H:%M:%S")},
        {"name": "status", "accessor": lambda x: dict(ApplicationStatus.choices)[x]},
        {"name": "language"},
        {"name": "first_name"},
        {"name": "last_name"},
        {"name": "email"},
        {"name": "phone_number"},
        {"name": "address"},
        {"name": "zip_code"},
        {"name": "municipality"},
        {"name": "company_name"},
        {"name": "business_id"},
        {"name": "boat", "accessor": lambda x: x.id},
        {"name": "accept_boating_newsletter"},
        {"name": "accept_fitness_news"},
        {"name": "accept_library_news"},
        {"name": "accept_other_culture_news"},
        {"name": "information_accuracy_confirmed"},
        {"name": "application_code"},
        {
            "name": "harborchoice_set",
            "accessor": lambda x: x.serialize() if x else None,
        },
        {"name": "berth_switch", "accessor": lambda x: x.serialize() if x else None},
        {"name": "accessibility_required"},
        {"name": "renting_period"},
        {"name": "rent_from"},
        {"name": "rent_till"},
        {"name": "agree_to_terms"},
    )


class WinterStorageApplication(BaseApplication, SerializableMixin):
    area_type = models.CharField(
        choices=ApplicationAreaType.choices,
        verbose_name=_("application area type"),
        max_length=30,
        null=True,
        blank=True,
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

    def create_change_entry(self):
        fields_to_compare = [
            "status",
            "language",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "zip_code",
            "municipality",
            "company_name",
            "business_id",
            "boat_id",
            "accept_boating_newsletter",
            "accept_fitness_news",
            "accept_library_news",
            "accept_other_culture_news",
            "information_accuracy_confirmed",
            "application_code",
            "storage_method",
            "trailer_registration_number",
        ]

        creating = self._state.adding
        if not creating:
            old_instance = WinterStorageApplication.objects.get(id=self.id)

            change_list = ""
            for field in fields_to_compare:
                old_value = getattr(old_instance, field, "[Empty]")
                new_value = getattr(self, field, "[Empty]")
                if old_value != new_value:
                    field_name = WinterStorageApplication._meta.get_field(
                        field
                    ).verbose_name.capitalize()
                    change_list += f"{field_name}: {old_value} -> {new_value}\n"

            if len(change_list) > 0:
                WinterStorageApplicationChange.objects.create(
                    application=self, change_list=change_list
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
            "application_code",
            "trailer_registration_number",
        ]
        for field in fields_to_strip:
            if field_value := getattr(self, field):
                setattr(self, field, field_value.strip())

        self.create_change_entry()

        # Ensure clean is always ran
        self.full_clean()

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

    serialize_fields = (
        {"name": "id"},
        {"name": "created_at", "accessor": lambda x: x.strftime("%d-%m-%Y %H:%M:%S")},
        {"name": "status", "accessor": lambda x: dict(ApplicationStatus.choices)[x]},
        {"name": "language"},
        {"name": "first_name"},
        {"name": "last_name"},
        {"name": "email"},
        {"name": "phone_number"},
        {"name": "address"},
        {"name": "zip_code"},
        {"name": "municipality"},
        {"name": "company_name"},
        {"name": "business_id"},
        {"name": "boat", "accessor": lambda x: x.id},
        {"name": "accept_boating_newsletter"},
        {"name": "accept_fitness_news"},
        {"name": "accept_library_news"},
        {"name": "accept_other_culture_news"},
        {"name": "information_accuracy_confirmed"},
        {"name": "application_code"},
        {
            "name": "area_type",
            "accessor": lambda x: dict(ApplicationAreaType.choices)[x] if x else None,
        },
        {
            "name": "winterstorageareachoice_set",
            "accessor": lambda x: x.serialize() if x else None,
        },
        {
            "name": "storage_method",
            "accessor": lambda x: dict(WinterStorageMethod.choices)[x] if x else None,
        },
        {"name": "trailer_registration_number"},
    )
