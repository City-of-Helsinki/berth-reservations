import graphene

from .types import WinterStorageMethodEnum


class HarborChoiceInput(graphene.InputObjectType):
    harbor_id = graphene.ID(required=True)
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


class WinterStorageAreaChoiceInput(graphene.InputObjectType):
    winter_area_id = graphene.ID(required=True)
    priority = graphene.Int(required=True)


class WinterStorageApplicationInput(BaseApplicationInput):
    storage_method = WinterStorageMethodEnum(required=True)
    trailer_registration_number = graphene.String()
    chosen_areas = graphene.List(
        graphene.NonNull(WinterStorageAreaChoiceInput), required=True
    )
