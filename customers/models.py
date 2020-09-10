import uuid
from decimal import Decimal

from dateutil.parser import parse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Case, UniqueConstraint, Value, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from resources.models import BoatType
from utils.models import TimeStampedModel, UUIDModel

from .enums import BoatCertificateType, InvoicingType, OrganizationType
from .utils import calculate_lease_start_and_end_dates

User = get_user_model()


class CustomerProfileManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                customer_group=Case(
                    When(
                        organization__isnull=False,
                        then="organization__organization_type",
                    ),
                    default=Value("private"),
                    output_field=models.CharField(),
                )
            )
        )

    @transaction.atomic
    def import_customer_data(self, data):  # noqa: C901
        """
        Imports list of customers of the following shape:
        {
            "id": "98edea83-4c92-4dda-bb90-f22e9dafe94c"  <-- profile should have this very ID
            "comment": ""
            "customer_id": "313431",  <-- not really used for any field
            "boats": [
                {
                    "boat_type": "Perämoottorivene",  <-- Finnish name for the boat type, from translated_fields
                    "name": "McBoatface 111",
                    "registration_number": "31123A",
                    "width": "2.00",
                    "length": "5.30",
                    "draught": null,  <-- either null or string like width and length above
                    "weight": null  <-- either null or integer
                }
            ],
            "leases": [
                {
                    "harbor_servicemap_id": "41074",
                    "pier_id": "A",  <-- harbor identifier
                    "berth_number": 4,
                    "start_date": "2019-06-10",
                    "end_date": "2019-09-14",
                    "boat_index": 0  <-- index of the boat in the "boats" list
                }
            ],
            "orders": [
                {
                    "created_at": "2019-12-02 00:00:00.000",
                    "order_sum": "251.00",
                    "vat_percentage": "25.0",
                    "berth": {
                        "harbor_servicemap_id": "41074",  <-- service map id
                        "pier_id": "A",  <-- harbor identifier
                        "berth_number": 4
                    },
                    "comment": "Laskunumero: 247509 RAMSAYRANTA A 004"
                }
            ],
            "organization": {  <-- either a dict like here or it will not be in this customer's dict at all
                "type": "company",  <-- values from OrganizationType enum
                "name": "Nice Profitable Firm Ltd.",
                "address": "Mannerheimintie 1 A 1",
                "postal_code": "00100",
                "city": "Helsinki"
            },
        }

        And returns dict where key is the customer_id and value is the UUID of created profile object
        """
        from leases.models import BerthLease
        from payments.models import Order
        from resources.models import Berth, Harbor

        def _get_berth(harbor_servicemap_id: str, berth_number: str, pier_id: str):
            """
            - Try to filter the pier based on the identifier
            - If no pier with that identifier was found, look for the default "-" pier
            - If that isn't found either, check how many berth are on the pier
                - If there's only one, assign it; otherwise, raise an error
            """
            possible_berths = Berth.objects.filter(
                pier__harbor=Harbor.objects.get(servicemap_id=harbor_servicemap_id),
                number=berth_number,
            )
            # Filter only for the specified pier
            # If there's only one berth matching the berth number + pier identifier, that's the one
            if matching_berth := possible_berths.filter(
                pier__identifier=pier_id
            ).first():
                berth = matching_berth
            # If there's no berth on the pier with the identifier, but there's only one pier on the harbor,
            # then we take it as "default" pier and we assign it to the berth on that pier
            elif possible_berths.count() == 1:
                berth = possible_berths.first()
            # Otherwise, rise an error
            else:
                raise Berth.DoesNotExist(
                    _(f"Berth {berth_number} does not exist on pier {pier_id}")
                )
            return berth

        result = {}
        for index, customer_data in enumerate(data):
            try:
                if not customer_data.get("id"):
                    raise Exception(_("No customer ID provided"))

                customer = self.create(
                    id=customer_data.get("id"), comment=customer_data.get("comment"),
                )
                customer.refresh_from_db()

                if organization := customer_data.get("organization"):
                    organization_type = OrganizationType(organization.get("type"))
                    Organization.objects.create(
                        customer=customer,
                        organization_type=organization_type,
                        name=organization.get("name"),
                        address=organization.get("address"),
                        postal_code=organization.get("postal_code"),
                        city=organization.get("city"),
                        business_id="-"
                        if organization_type == OrganizationType.COMPANY
                        else "",
                    )

                boats = []
                for boat in customer_data.get("boats", []):
                    boat_type = BoatType.objects.language("fi").get(
                        translations__name=boat.get("boat_type")
                    )
                    boats.append(
                        Boat.objects.create(
                            owner=customer,
                            name=boat.get("name"),
                            boat_type=boat_type,
                            registration_number=boat.get("registration_number"),
                            width=Decimal(boat.get("width")),
                            length=Decimal(boat.get("length")),
                            draught=Decimal(boat.get("draught"))
                            if boat.get("draught")
                            else None,
                            weight=Decimal(boat.get("weight"))
                            if boat.get("weight")
                            else None,
                        )
                    )

                for lease in customer_data.get("leases", []):
                    berth = _get_berth(
                        lease.get("harbor_servicemap_id"),
                        lease.get("berth_number"),
                        lease.get("pier_id", "-"),
                    )

                    BerthLease.objects.create(
                        customer=customer,
                        berth=berth,
                        boat=boats[lease.get("boat_index")]
                        if lease.get("boat_index")
                        else None,
                        start_date=lease.get("start_date"),
                        end_date=lease.get("end_date"),
                    )

                for order in customer_data.get("orders", []):
                    lease = None
                    if berth_data := order.get("berth"):
                        berth = _get_berth(
                            berth_data.get("harbor_servicemap_id"),
                            berth_data.get("berth_number"),
                            berth_data.get("pier_id", "-"),
                        )

                        start_date, end_date = calculate_lease_start_and_end_dates(
                            parse(order.get("created_at")).date()
                        )

                        lease, _created = BerthLease.objects.get_or_create(
                            customer=customer,
                            berth=berth,
                            start_date=start_date,
                            end_date=end_date,
                        )

                    Order.objects.create(
                        customer=customer,
                        lease=lease,
                        created_at=order.get("created_at"),
                        price=Decimal(order.get("order_sum")),
                        tax_percentage=Decimal(order.get("vat_percentage")),
                        comment=order.get("comment"),
                    )
                result[customer_data["customer_id"]] = customer.pk
            except Exception as err:
                msg = (
                    "Could not import customer_id: {}, index: {}".format(
                        customer_data["customer_id"], index
                    )
                    if "customer_id" in customer_data
                    else "Could not import unknown customer, index: {}".format(index)
                )
                msg += f"\n{err}"
                raise Exception(msg) from err
        return result


class CustomerProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    invoicing_type = models.CharField(
        choices=InvoicingType.choices,
        verbose_name=_("invoicing type"),
        max_length=30,
        default=InvoicingType.ONLINE_PAYMENT,
    )
    comment = models.TextField(verbose_name=_("comment"), blank=True)

    objects = CustomerProfileManager()

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
    organization_type = models.CharField(
        choices=OrganizationType.choices,
        verbose_name=_("organization type"),
        max_length=16,
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
    intended_use = models.TextField(verbose_name=_("intended use"), blank=True)

    class Meta:
        verbose_name = _("boat")
        verbose_name_plural = _("boats")
        ordering = ("owner",)

    def __str__(self):
        return "{} ({})".format(self.registration_number, self.pk)


def get_boat_media_folder(instance, filename):
    return "boats/{boat_id}/{filename}".format(boat_id=instance.id, filename=filename)


def get_boat_certificate_media_folder(instance, filename):
    return get_boat_media_folder(instance=instance.boat, filename=filename)


class BoatCertificate(UUIDModel):
    boat = models.ForeignKey(
        Boat,
        verbose_name=_("boat"),
        related_name="certificates",
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        verbose_name="certificate file",
        upload_to=get_boat_certificate_media_folder,
        storage=FileSystemStorage(),
        blank=True,
        null=True,
    )
    certificate_type = models.CharField(
        choices=BoatCertificateType.choices,
        verbose_name=_("certificate type"),
        max_length=16,
    )
    valid_until = models.DateField(verbose_name=_("valid until"), blank=True, null=True)
    checked_at = models.DateField(verbose_name=_("checked at"), default=timezone.now)
    checked_by = models.CharField(
        verbose_name=_("checked by"), max_length=100, blank=True, null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["boat_id", "certificate_type"], name="unique_boat_certificate"
            )
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        creating = self._state.adding
        if not creating:
            old_instance = BoatCertificate.objects.get(id=self.id)
            # If the certificate is being changed
            if old_instance.boat != self.boat:
                raise ValidationError(
                    _("Cannot change the boat assigned to this certificate")
                )
        super().clean()
