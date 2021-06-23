import graphene
from graphene_django.filter import DjangoFilterConnectionField

from ..models import BerthApplication, BerthSwitchReason, WinterStorageApplication
from .types import (
    ApplicationAreaTypeEnum,
    ApplicationStatusEnum,
    BerthApplicationFilter,
    BerthApplicationNode,
    BerthSwitchReasonType,
    WinterStorageApplicationFilter,
    WinterStorageApplicationNode,
)


class Query:
    berth_application = graphene.relay.Node.Field(BerthApplicationNode)
    berth_applications = DjangoFilterConnectionField(
        BerthApplicationNode,
        filterset_class=BerthApplicationFilter,
        statuses=graphene.List(ApplicationStatusEnum),
        description="The `statuses` filter takes a list of `ApplicationStatus` values "
        "representing the desired statuses. If an empty list is passed, no filter will be applied "
        "and all the results will be returned."
        "\n\n`BerthApplications` are ordered by `createdAt` in ascending order by default."
        "\n\n**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* A value passed is not a valid status",
    )

    winter_storage_application = graphene.relay.Node.Field(WinterStorageApplicationNode)
    winter_storage_applications = DjangoFilterConnectionField(
        WinterStorageApplicationNode,
        filterset_class=WinterStorageApplicationFilter,
        statuses=graphene.List(ApplicationStatusEnum),
        area_types=graphene.List(ApplicationAreaTypeEnum),
        description="The `statuses` filter takes a list of `ApplicationStatus` values "
        "representing the desired statuses. If an empty list is passed, no filter will be applied "
        "and all the results will be returned."
        "\n\n`WinterStorageApplications` are ordered by `createdAt` in ascending order by default."
        "\n\n**Requires permissions** to access winter storage applications."
        "\n\nErrors:"
        "\n* A value passed is not a valid status",
    )
    berth_switch_reasons = graphene.List(BerthSwitchReasonType)

    def resolve_berth_switch_reasons(self, info, **kwargs):
        return BerthSwitchReason.objects.all()

    def resolve_berth_applications(self, info, **kwargs):
        statuses = kwargs.pop("statuses", [])

        qs = BerthApplication.objects

        if statuses:
            qs = qs.filter(status__in=statuses)

        return qs.select_related(
            "boat_type",
            "berth_switch",
            "berth_switch__berth",
            "berth_switch__reason",
            "customer",
        ).prefetch_related(
            "berth_switch__reason__translations",
            "harborchoice_set",
            "harborchoice_set__harbor",
        )

    def resolve_winter_storage_applications(self, info, **kwargs):
        statuses = kwargs.pop("statuses", [])
        area_types = kwargs.pop("area_types", [])

        qs = WinterStorageApplication.objects

        if statuses:
            qs = qs.filter(status__in=statuses)
        if area_types:
            qs = qs.filter(area_type__in=area_types)

        return qs.select_related("boat_type", "customer",).prefetch_related(
            "winterstorageareachoice_set",
            "winterstorageareachoice_set__winter_storage_area",
            "lease",
        )
