import graphene
from graphene_django.types import DjangoObjectType
from graphql_relay.node.node import from_global_id

from .models import BerthSwitch, BoatType, Harbor, HarborChoice, Reservation
from .signals import reservation_saved


class HarborChoiceType(DjangoObjectType):
    class Meta:
        model = HarborChoice


class ReservationType(DjangoObjectType):
    class Meta:
        model = Reservation


class BerthSwitchType(DjangoObjectType):
    class Meta:
        model = BerthSwitch


class HarborChoiceInput(graphene.InputObjectType):
    harbor_id = graphene.String()
    priority = graphene.Int()


class BerthSwitchInput(graphene.InputObjectType):
    harbor_id = graphene.String(required=True)
    pier = graphene.String()
    berth_number = graphene.String(required=True)


class ReservationInput(graphene.InputObjectType):
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    phone_number = graphene.String()
    address = graphene.String()
    zip_code = graphene.String()
    municipality = graphene.String()
    company_name = graphene.String()
    business_id = graphene.String()
    boat_type = graphene.Int()
    boat_registration_number = graphene.String()
    boat_name = graphene.String()
    boat_model = graphene.String()
    boat_length = graphene.Float()
    boat_width = graphene.Float()
    boat_draught = graphene.Float()
    boat_weight = graphene.Float()
    accessibility_required = graphene.Boolean()
    boat_propulsion = graphene.String()
    boat_hull_material = graphene.String()
    boat_intended_use = graphene.String()
    renting_period = graphene.String()
    rent_from = graphene.String()
    rent_till = graphene.String()
    boat_is_inspected = graphene.Boolean()
    boat_is_insured = graphene.Boolean()
    agree_to_terms = graphene.Boolean()
    accept_boating_newsletter = graphene.Boolean()
    accept_fitness_news = graphene.Boolean()
    accept_library_news = graphene.Boolean()
    accept_other_culture_news = graphene.Boolean()
    information_accuracy_confirmed = graphene.Boolean()
    application_code = graphene.String()
    choices = graphene.List(HarborChoiceInput)


class CreateReservation(graphene.Mutation):
    class Arguments:
        reservation = ReservationInput(required=True)
        berth_switch = BerthSwitchInput()

    ok = graphene.Boolean()
    reservation = graphene.Field(ReservationType)

    def mutate(self, info, **kwargs):
        reservation_data = kwargs.pop("reservation")

        boat_type_id = reservation_data.pop("boat_type", None)
        if boat_type_id:
            reservation_data["boat_type"] = BoatType.objects.get(id=boat_type_id)

        switch_data = kwargs.pop("berth_switch", None)
        if switch_data:
            harbor_id = from_global_id(switch_data.get("harbor_id"))[1]
            old_harbor = Harbor.objects.get(id=harbor_id)
            berth_switch = BerthSwitch.objects.create(
                harbor=old_harbor,
                pier=switch_data.get("pier"),
                berth_number=switch_data.get("berth_number"),
            )
            reservation_data["berth_switch"] = berth_switch

        choices = reservation_data.pop("choices", [])

        reservation = Reservation.objects.create(**reservation_data)

        for choice in choices:
            harbor_id = from_global_id(choice.get("harbor_id"))[1]
            harbor = Harbor.objects.get(id=harbor_id)
            HarborChoice.objects.get_or_create(
                harbor=harbor, priority=choice.get("priority"), reservation=reservation
            )

        # Send notifications when all m2m relations are saved
        reservation_saved.send(sender="CreateReservation", reservation=reservation)

        ok = True
        return CreateReservation(reservation=reservation, ok=ok)


class Mutation(graphene.ObjectType):
    create_reservation = CreateReservation.Field()
