import graphene
from graphene_django.types import DjangoObjectType
from graphql_relay.node.node import from_global_id

from harbors.models import WinterStorageArea

from .enums import WinterStorageMethod
from .models import (
    BerthApplication,
    BerthSwitch,
    BerthSwitchReason,
    BoatType,
    Harbor,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)
from .signals import application_saved

WinterStorageMethodEnum = graphene.Enum.from_enum(WinterStorageMethod)


class HarborChoiceType(DjangoObjectType):
    class Meta:
        model = HarborChoice


class BerthApplicationType(DjangoObjectType):
    class Meta:
        model = BerthApplication
        exclude = (
            "customer",
            "lease",
        )


class BerthSwitchType(DjangoObjectType):
    class Meta:
        model = BerthSwitch
        exclude = ("berthapplication_set",)


class BerthSwitchReasonType(DjangoObjectType):
    class Meta:
        model = BerthSwitchReason
        exclude_fields = ("berthswitch_set",)

    title = graphene.String()


class WinterStorageApplicationType(DjangoObjectType):
    class Meta:
        model = WinterStorageApplication


class HarborChoiceInput(graphene.InputObjectType):
    harbor_id = graphene.ID(required=True)
    priority = graphene.Int(required=True)


class WinterStorageAreaChoiceInput(graphene.InputObjectType):
    winter_area_id = graphene.ID(required=True)
    priority = graphene.Int(required=True)


class BerthSwitchInput(graphene.InputObjectType):
    harbor_id = graphene.ID(required=True)
    pier = graphene.String()
    berth_number = graphene.String(required=True)
    reason = graphene.ID()


class BaseApplicationInput(graphene.InputObjectType):
    language = graphene.String(required=True)
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone_number = graphene.String(required=True)
    address = graphene.String(required=True)
    zip_code = graphene.String(required=True)
    municipality = graphene.String(required=True)
    company_name = graphene.String()
    business_id = graphene.String()
    boat_type = graphene.ID(required=True)
    boat_registration_number = graphene.String()
    boat_name = graphene.String()
    boat_model = graphene.String()
    boat_length = graphene.Float(required=True)
    boat_width = graphene.Float(required=True)
    application_code = graphene.String()
    accept_boating_newsletter = graphene.Boolean(required=True)
    accept_fitness_news = graphene.Boolean(required=True)
    accept_library_news = graphene.Boolean(required=True)
    accept_other_culture_news = graphene.Boolean(required=True)
    information_accuracy_confirmed = graphene.Boolean(required=True)


class BerthApplicationInput(BaseApplicationInput):
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
    choices = graphene.List(graphene.NonNull(HarborChoiceInput), required=True)


class WinterStorageApplicationInput(BaseApplicationInput):
    storage_method = WinterStorageMethodEnum(required=True)
    trailer_registration_number = graphene.String()
    chosen_areas = graphene.List(
        graphene.NonNull(WinterStorageAreaChoiceInput), required=True
    )


class CreateBerthApplication(graphene.Mutation):
    class Arguments:
        berth_application = BerthApplicationInput(required=True)
        berth_switch = BerthSwitchInput()

    ok = graphene.Boolean()
    berth_application = graphene.Field(BerthApplicationType)

    def mutate(self, info, **kwargs):
        application_data = kwargs.pop("berth_application")

        boat_type_id = application_data.pop("boat_type", None)
        if boat_type_id:
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))

        switch_data = kwargs.pop("berth_switch", None)
        if switch_data:
            harbor_id = from_global_id(switch_data.get("harbor_id"))[1]
            old_harbor = Harbor.objects.get(id=harbor_id)
            reason_id = switch_data.get("reason")
            reason = BerthSwitchReason.objects.get(id=reason_id) if reason_id else None
            berth_switch = BerthSwitch.objects.create(
                harbor=old_harbor,
                pier=switch_data.get("pier", ""),
                berth_number=switch_data.get("berth_number"),
                reason=reason,
            )
            application_data["berth_switch"] = berth_switch

        choices = application_data.pop("choices", [])

        application = BerthApplication.objects.create(**application_data)

        for choice in choices:
            harbor_id = from_global_id(choice.get("harbor_id"))[1]
            harbor = Harbor.objects.get(id=harbor_id)
            HarborChoice.objects.get_or_create(
                harbor=harbor, priority=choice.get("priority"), application=application
            )

        # Send notifications when all m2m relations are saved
        application_saved.send(sender="CreateBerthApplication", application=application)

        ok = True
        return CreateBerthApplication(berth_application=application, ok=ok)


class CreateWinterStorageApplication(graphene.Mutation):
    class Arguments:
        winter_storage_application = WinterStorageApplicationInput(required=True)

    ok = graphene.Boolean()
    winter_storage_application = graphene.Field(WinterStorageApplicationType)

    def mutate(self, info, **kwargs):
        application_data = kwargs.pop("winter_storage_application")

        boat_type_id = application_data.pop("boat_type", None)
        if boat_type_id:
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))

        chosen_areas = application_data.pop("chosen_areas", [])

        application = WinterStorageApplication.objects.create(**application_data)

        for choice in chosen_areas:
            winter_area_id = from_global_id(choice.get("winter_area_id"))[1]
            winter_storage_area = WinterStorageArea.objects.get(id=winter_area_id)
            WinterStorageAreaChoice.objects.get_or_create(
                winter_storage_area=winter_storage_area,
                priority=choice.get("priority"),
                application=application,
            )

        # Send notifications when all m2m relations are saved
        application_saved.send(
            sender="CreateWinterStorageApplication", application=application
        )

        ok = True
        return CreateWinterStorageApplication(
            winter_storage_application=application, ok=ok
        )


class Mutation:
    create_berth_application = CreateBerthApplication.Field()
    create_winter_storage_application = CreateWinterStorageApplication.Field()


class Query:
    berth_switch_reasons = graphene.List(BerthSwitchReasonType)

    def resolve_berth_switch_reasons(self, info, **kwargs):
        return BerthSwitchReason.objects.all()
