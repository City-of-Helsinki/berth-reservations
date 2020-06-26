import graphene
from graphene_django.filter import DjangoFilterConnectionField

from applications.models import BerthApplication
from customers.models import CustomerProfile
from leases.models import BerthLease
from users.decorators import view_permission_required

from .types import ApplicationStatusEnum, BerthApplicationFilter, BerthApplicationNode


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

    @view_permission_required(BerthApplication, BerthLease, CustomerProfile)
    def resolve_berth_applications(self, info, **kwargs):
        statuses = kwargs.pop("statuses", [])

        qs = BerthApplication.objects

        if statuses:
            qs = qs.filter(status__in=statuses)

        return (
            qs.select_related(
                "boat_type",
                "berth_switch",
                "berth_switch__harbor",
                "berth_switch__reason",
            )
            .prefetch_related(
                "berth_switch__reason__translations",
                "harborchoice_set",
                "harborchoice_set__harbor",
            )
            .order_by("created_at")
        )
