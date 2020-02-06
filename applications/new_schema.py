import django_filters
import graphene
from django.db import transaction
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required, superuser_required
from graphql_relay import from_global_id

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile

from .models import BerthApplication, BerthSwitch, HarborChoice
from .schema import BerthSwitchType as OldBerthSwitchType


class HarborChoiceType(DjangoObjectType):
    harbor = graphene.String()

    class Meta:
        model = HarborChoice
        exclude = ("id", "application")

    def resolve_harbor(self, info, **kwargs):
        if self.harbor:
            return self.harbor.servicemap_id
        return None


class BerthSwitchType(OldBerthSwitchType):
    harbor = graphene.String()

    class Meta:
        model = BerthSwitch
        exclude = ("berthapplication_set",)

    def resolve_harbor(self, info, **kwargs):
        if self.harbor:
            return self.harbor.servicemap_id
        return None


class BerthApplicationFilter(django_filters.FilterSet):
    switch_applications = django_filters.BooleanFilter(
        field_name="berth_switch", method="filter_berth_switch"
    )

    def filter_berth_switch(self, queryset, name, value):
        lookup = "__".join([name, "isnull"])
        return queryset.filter(**{lookup: not value})


class BerthApplicationNode(DjangoObjectType):
    boat_type = graphene.String()
    harbor_choices = graphene.List(HarborChoiceType)

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
    @login_required
    @superuser_required
    # TODO: Should check if the user has permissions to access this specific object
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
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to perform the following changes
        berth_application_id = from_global_id(input.get("id"))[1]
        customer_id = from_global_id(input.get("customer_id"))[1]

        try:
            application = BerthApplication.objects.get(pk=berth_application_id)
            customer = CustomerProfile.objects.get(pk=customer_id)

            application.customer = customer
            application.save()
        except (BerthApplication.DoesNotExist, CustomerProfile.DoesNotExist) as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateBerthApplication(berth_application=application)


class Query:
    berth_application = graphene.relay.Node.Field(BerthApplicationNode)
    berth_applications = DjangoFilterConnectionField(
        BerthApplicationNode, filterset_class=BerthApplicationFilter
    )

    @login_required
    @superuser_required
    # TODO: Should check if the user has permissions to access these objects
    def resolve_berth_applications(self, info, **kwargs):
        return BerthApplication.objects.select_related(
            "boat_type", "berth_switch", "berth_switch__harbor", "berth_switch__reason",
        ).prefetch_related(
            "berth_switch__reason__translations",
            "harborchoice_set",
            "harborchoice_set__harbor",
        )


class Mutation:
    update_berth_application = UpdateBerthApplication.Field()
