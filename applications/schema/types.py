import django_filters
import graphene
from django.db.models import Q
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from graphql_relay import to_global_id

from customers.models import CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from utils.relay import return_node_if_user_has_permissions
from utils.schema import CountConnection

from ..enums import ApplicationAreaType, ApplicationStatus, WinterStorageMethod
from ..models import (
    BerthApplication,
    BerthSwitch,
    BerthSwitchReason,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)

ApplicationStatusEnum = graphene.Enum.from_enum(ApplicationStatus)
WinterStorageMethodEnum = graphene.Enum.from_enum(WinterStorageMethod)
ApplicationAreaTypeEnum = graphene.Enum.from_enum(ApplicationAreaType)


class HarborChoiceType(DjangoObjectType):
    harbor = graphene.Field("resources.schema.HarborNode", required=True)

    class Meta:
        model = HarborChoice
        exclude = ("id", "application")


class BerthSwitchReasonType(DjangoObjectType):
    title = graphene.String()

    class Meta:
        model = BerthSwitchReason
        exclude = ("berthswitch_set",)


class BerthSwitchType(DjangoObjectType):
    reason = graphene.Field(BerthSwitchReasonType)

    class Meta:
        model = BerthSwitch


class BerthApplicationFilter(django_filters.FilterSet):
    switch_applications = django_filters.BooleanFilter(
        field_name="berth_switch", method="filter_berth_switch"
    )
    no_customer = django_filters.BooleanFilter(
        field_name="customer", lookup_expr="isnull"
    )
    application_code = django_filters.BooleanFilter(
        field_name="application_code", method="filter_application_code"
    )
    order_by = django_filters.OrderingFilter(
        fields=("created_at",), label="Supports only `createdAt` and `-createdAt`.",
    )
    name = django_filters.CharFilter(method="filter_name")

    def filter_name(self, qs, name, value):
        for part in value.split():
            qs = qs.filter(Q(first_name__icontains=part) | Q(last_name__icontains=part))
        return qs

    def filter_berth_switch(self, queryset, name, value):
        lookup = "__".join([name, "isnull"])
        return queryset.filter(**{lookup: not value})

    def filter_application_code(self, queryset, name, value):
        lookup = "__".join([name, "exact"])
        return (
            queryset.exclude(**{lookup: ""})
            if value
            else queryset.filter(**{lookup: ""})
        )


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
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node, info.context.user, BerthApplication, BerthLease, CustomerProfile
        )


class WinterStorageAreaChoiceType(DjangoObjectType):
    harbor = graphene.Field("resources.schema.HarborNode", required=True)
    winter_storage_section_ids = graphene.List(graphene.ID)

    class Meta:
        model = WinterStorageAreaChoice
        exclude = ("id", "application")

    def resolve_winter_storage_section_ids(self, info, **kwargs):
        return list(
            to_global_id("WinterStorageSectionNode", section.id)
            for section in self.winter_storage_area.sections.all()
        )


class WinterStorageApplicationFilter(django_filters.FilterSet):
    no_customer = django_filters.BooleanFilter(
        field_name="customer", lookup_expr="isnull"
    )
    order_by = django_filters.OrderingFilter(
        fields=("created_at",), label="Supports only `createdAt` and `-createdAt`.",
    )
    name = django_filters.CharFilter(method="filter_name")

    def filter_name(self, qs, name, value):
        for part in value.split():
            qs = qs.filter(Q(first_name__icontains=part) | Q(last_name__icontains=part))
        return qs


class WinterStorageApplicationNode(DjangoObjectType):
    boat_type = graphene.String()
    winter_storage_area_choices = graphene.List(WinterStorageAreaChoiceType)
    status = ApplicationStatusEnum(required=True)
    storage_method = WinterStorageMethodEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode")

    class Meta:
        model = WinterStorageApplication
        interfaces = (graphene.relay.Node,)
        exclude = ("chosen_areas", "winterstorageareachoice_set")
        connection_class = CountConnection

    def resolve_boat_type(self, info, **kwargs):
        if self.boat_type:
            return self.boat_type.id
        return None

    def resolve_winter_storage_area_choices(self, info, **kwargs):
        if self.winterstorageareachoice_set.count():
            return self.winterstorageareachoice_set.all()
        return None

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node,
            info.context.user,
            WinterStorageApplication,
            WinterStorageLease,
            CustomerProfile,
        )
