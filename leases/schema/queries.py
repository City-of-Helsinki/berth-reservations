import django_filters
import graphene
from graphene_django.filter import DjangoFilterConnectionField

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import CustomerProfile
from users.decorators import view_permission_required

from ..models import BerthLease, WinterStorageLease
from .types import BerthLeaseNode, WinterStorageLeaseNode


class AbstractLeaseNodeFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(("created_at", "createdAt"),),
        label="Supports only `createdAt` and `-createdAt`.",
    )


class Query:
    berth_lease = graphene.relay.Node.Field(BerthLeaseNode)
    berth_leases = DjangoFilterConnectionField(
        BerthLeaseNode,
        filterset_class=AbstractLeaseNodeFilter,
        description="`BerthLeases` are ordered by `createdAt` in ascending order by default.",
    )

    winter_storage_lease = graphene.relay.Node.Field(WinterStorageLeaseNode)
    winter_storage_leases = DjangoFilterConnectionField(
        WinterStorageLeaseNode,
        filterset_class=AbstractLeaseNodeFilter,
        description="`WinterStorageLeases` are ordered by `createdAt` in ascending order by default.",
    )

    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    def resolve_berth_leases(self, info, **kwargs):
        return (
            BerthLease.objects.select_related(
                "application",
                "application__customer",
                "berth",
                "berth__pier",
                "berth__pier__harbor",
            )
            .prefetch_related("application__customer__boats")
            .order_by("created_at")
        )

    @view_permission_required(
        WinterStorageLease, WinterStorageApplication, CustomerProfile
    )
    def resolve_winter_storage_leases(self, info, **kwargs):
        return (
            WinterStorageLease.objects.select_related(
                "application",
                "application__customer",
                "place",
                "place__winter_storage_section",
                "place__winter_storage_section__area",
            )
            .prefetch_related("application__customer__boats")
            .order_by("created_at")
        )
