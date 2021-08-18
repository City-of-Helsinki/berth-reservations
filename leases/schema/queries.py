import django_filters
import graphene
from graphene_django.filter import DjangoFilterConnectionField

from users.decorators import view_permission_required

from ..models import BerthLease, WinterStorageLease
from .types import (
    BerthLeaseNode,
    LeaseStatusEnum,
    SendExistingInvoicesPreviewType,
    WinterStorageLeaseNode,
)


class AbstractLeaseNodeFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=("created_at",), label="Supports only `createdAt` and `-createdAt`.",
    )


class Query:
    berth_lease = graphene.relay.Node.Field(BerthLeaseNode)
    berth_leases = DjangoFilterConnectionField(
        BerthLeaseNode,
        statuses=graphene.List(LeaseStatusEnum),
        start_year=graphene.Int(),
        filterset_class=AbstractLeaseNodeFilter,
        description="`BerthLeases` are ordered by `startDate/endDate` in descending order, "
        "and `createdAt` in ascending order by default.",
    )

    winter_storage_lease = graphene.relay.Node.Field(WinterStorageLeaseNode)
    winter_storage_leases = DjangoFilterConnectionField(
        WinterStorageLeaseNode,
        statuses=graphene.List(LeaseStatusEnum),
        start_year=graphene.Int(),
        filterset_class=AbstractLeaseNodeFilter,
        description="`WinterStorageLeases` are ordered by `startDate/endDate` in descending order, "
        "and `createdAt` in ascending order by default.",
    )

    send_berth_invoice_preview = graphene.Field(SendExistingInvoicesPreviewType)
    send_marked_winter_storage_invoice_preview = graphene.Field(
        SendExistingInvoicesPreviewType
    )

    def resolve_berth_leases(self, info, statuses=None, start_year=None, **kwargs):
        qs = BerthLease.objects
        if statuses:
            qs = qs.filter(status__in=statuses)
        if start_year:
            qs = qs.filter(start_date__year=start_year)

        return qs.select_related(
            "application",
            "application__customer",
            "berth",
            "berth__pier",
            "berth__pier__harbor",
        ).prefetch_related("application__customer__boats")

    def resolve_winter_storage_leases(
        self, info, statuses=None, start_year=None, **kwargs
    ):
        qs = WinterStorageLease.objects
        if statuses:
            qs = qs.filter(status__in=statuses)
        if start_year:
            qs = qs.filter(start_date__year=start_year)

        return qs.select_related(
            "application",
            "application__customer",
            "place",
            "place__winter_storage_section",
            "place__winter_storage_section__area",
        ).prefetch_related("application__customer__boats")

    @view_permission_required(BerthLease)
    def resolve_send_berth_invoice_preview(self, info, **kwargs):
        count = BerthLease.objects.get_renewable_leases().count()
        return SendExistingInvoicesPreviewType(expected_leases=count)

    @view_permission_required(WinterStorageLease)
    def resolve_send_marked_winter_storage_invoice_preview(self, info, **kwargs):
        count = WinterStorageLease.objects.get_renewable_marked_leases().count()
        return SendExistingInvoicesPreviewType(expected_leases=count)
