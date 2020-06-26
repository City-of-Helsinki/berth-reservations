import django_filters
import graphene
from graphene_django import DjangoObjectType

from applications.enums import ApplicationStatus
from applications.models import BerthApplication, BerthSwitch, HarborChoice
from applications.schema import BerthSwitchType as OldBerthSwitchType
from customers.models import CustomerProfile
from leases.models import BerthLease
from users.decorators import view_permission_required
from utils.enum import graphene_enum
from utils.schema import CountConnection

ApplicationStatusEnum = graphene_enum(ApplicationStatus)


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
    customer = graphene.Field("customers.schema.ProfileNode")

    class Meta:
        model = BerthApplication
        interfaces = (graphene.relay.Node,)
        exclude = ("chosen_harbors", "harborchoice_set")
        connection_class = CountConnection

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
