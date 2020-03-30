import django_filters
import graphene
from django.db import transaction
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from customers.models import CustomerProfile
from leases.models import BerthLease
from users.decorators import change_permission_required, view_permission_required
from utils.relay import get_node_from_global_id

from .enums import ApplicationStatus
from .models import BerthApplication, BerthSwitch, HarborChoice
from .schema import BerthSwitchType as OldBerthSwitchType

ApplicationStatusEnum = graphene.Enum.from_enum(ApplicationStatus)


class HarborChoiceType(DjangoObjectType):
    harbor = graphene.String(required=True)
    harbor_name = graphene.String(required=True)

    class Meta:
        model = HarborChoice
        exclude = ("id", "application")

    def resolve_harbor(self, info, **kwargs):
        return self.harbor.servicemap_id

    def resolve_harbor_name(self, info, **kwargs):
        return self.harbor.safe_translation_getter("name")


class BerthSwitchType(OldBerthSwitchType):
    harbor = graphene.String(required=True)
    harbor_name = graphene.String(required=True)

    class Meta:
        model = BerthSwitch
        exclude = ("berthapplication_set",)

    def resolve_harbor(self, info, **kwargs):
        return self.harbor.servicemap_id

    def resolve_harbor_name(self, info, **kwargs):
        return self.harbor.safe_translation_getter("name")


class BerthApplicationFilter(django_filters.FilterSet):
    switch_applications = django_filters.BooleanFilter(
        field_name="berth_switch", method="filter_berth_switch"
    )
    no_customer = django_filters.BooleanFilter(
        field_name="customer", lookup_expr="isnull"
    )
    order_by = django_filters.OrderingFilter(
        fields=(("created_at", "createdAt"),),
        label="Supports only `createdAt` and `-createdAt`.",
    )

    def filter_berth_switch(self, queryset, name, value):
        lookup = "__".join([name, "isnull"])
        return queryset.filter(**{lookup: not value})


class BerthApplicationNode(DjangoObjectType):
    boat_type = graphene.String()
    harbor_choices = graphene.List(HarborChoiceType)
    status = ApplicationStatusEnum(required=True)

    class Meta:
        model = BerthApplication
        interfaces = (graphene.relay.Node,)
        exclude = ("chosen_harbors", "harborchoice_set")

    def resolve_boat_type(self, info, **kwargs):
        if self.boat_type:
            return self.boat_type.id
        return None

    def resolve_harbor_choices(self, info, **kwargs):
        if self.harborchoice_set.count():
            return self.harborchoice_set.all()
        return None

    @classmethod
    @view_permission_required(BerthApplication, BerthLease, CustomerProfile)
    def get_node(cls, info, id):
        return super().get_node(info, id)


class BerthApplicationInput:
    # TODO: the required has to be removed once more fields are added
    customer_id = graphene.ID(required=True)


class UpdateBerthApplication(graphene.ClientIDMutation):
    class Input(BerthApplicationInput):
        id = graphene.ID(required=True)

    berth_application = graphene.Field(BerthApplicationNode)

    @classmethod
    @view_permission_required(CustomerProfile, BerthLease)
    @change_permission_required(BerthApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        from customers.schema import BerthProfileNode

        application = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthApplicationNode
        )
        customer = get_node_from_global_id(
            info, input.pop("customer_id"), only_type=BerthProfileNode
        )

        application.customer = customer
        application.save()

        return UpdateBerthApplication(berth_application=application)


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


class Mutation:
    update_berth_application = UpdateBerthApplication.Field()
