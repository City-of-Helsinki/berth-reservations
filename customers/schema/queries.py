import graphene
from graphene_django.filter import DjangoFilterConnectionField

from applications.models import BerthApplication
from leases.models import BerthLease
from users.decorators import view_permission_required

from ..models import CustomerProfile
from .types import InvoicingTypeEnum, ProfileFilterSet, ProfileNode


class Query:
    berth_profile = graphene.relay.Node.Field(ProfileNode)
    berth_profiles = DjangoFilterConnectionField(
        ProfileNode,
        filterset_class=ProfileFilterSet,
        invoicing_types=graphene.List(InvoicingTypeEnum),
        description="The `invoicingTypes` filter takes a list of `InvoicingType` values "
        "representing the desired invoicing types of the customers. If an empty list is "
        "passed, no filter will be applied and all the results will be returned."
        "\n\n**Requires permissions** to access customer profiles."
        "\n\nErrors:"
        "\n* A value passed is not a valid invoicing type",
    )

    @view_permission_required(CustomerProfile, BerthApplication, BerthLease)
    def resolve_berth_profiles(self, info, **kwargs):
        invoicing_types = kwargs.pop("invoicing_types", [])

        qs = CustomerProfile.objects

        if invoicing_types:
            qs = qs.filter(invoicing_type__in=invoicing_types)

        return qs.select_related("organization").prefetch_related(
            "boats",
            "berth_applications",
            "berth_leases",
            "winter_storage_applications",
            "winter_storage_leases",
            "orders",
        )
