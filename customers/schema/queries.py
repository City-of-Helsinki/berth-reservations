import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from munigeo.models import Municipality as MP

from applications.models import BerthApplication
from leases.models import BerthLease
from users.decorators import view_permission_required

from ..models import CustomerProfile
from .types import CustomerGroupEnum, InvoicingTypeEnum, ProfileFilterSet, ProfileNode

class Municipality(DjangoObjectType):
    class Meta:
        model = MP
        fields = "__all__"

class Query:
    municipalities = graphene.List(Municipality)
    berth_profile = graphene.relay.Node.Field(ProfileNode)
    berth_profiles = DjangoFilterConnectionField(
        ProfileNode,
        filterset_class=ProfileFilterSet,
        invoicing_types=graphene.List(InvoicingTypeEnum),
        customer_groups=graphene.List(CustomerGroupEnum),
        description="The `invoicingTypes` filter takes a list of `InvoicingType` values "
        "representing the desired invoicing types of the customers. If an empty list is "
        "passed, no filter will be applied and all the results will be returned."
        "\n\nThe `customerGroups` filter takes a list of `CustomerGroup` values "
        "representing the desired groups of the customers. If an empty list is "
        "passed, no filter will be applied and all the results will be returned."
        "\n\n**Requires permissions** to access customer profiles."
        "\n\nErrors:"
        "\n* A value passed is not a valid invoicing type"
        "\n* A value passed is not a valid customer group",
    )

    @view_permission_required(CustomerProfile, BerthApplication, BerthLease)
    def resolve_berth_profiles(self, info, **kwargs):
        invoicing_types = kwargs.pop("invoicing_types", [])
        customer_groups = kwargs.pop("customer_groups", [])

        qs = CustomerProfile.objects

        if invoicing_types:
            qs = qs.filter(invoicing_type__in=invoicing_types)
        if customer_groups:
            qs = qs.filter(customer_group__in=customer_groups)

        return qs.select_related("organization").prefetch_related(
            "boats",
            "berth_applications",
            "berth_leases",
            "winter_storage_applications",
            "winter_storage_leases",
            "orders",
        )

    def resolve_municipalities(self, info, **kwargs):
        return MP.objects.all()