import graphene

from .types import ApplicationPriorityEnum, WinterStorageMethodEnum


class HarborChoiceInput(graphene.InputObjectType):
    harbor_id = graphene.ID(required=True)
    priority = graphene.Int(required=True)


class BerthSwitchInput(graphene.InputObjectType):
    berth_id = graphene.ID(required=True)
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


class BaseUpdateApplicationInput:
    id = graphene.ID(required=True)
    customer_id = graphene.ID()
    priority = ApplicationPriorityEnum()
    language = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    phone_number = graphene.String()
    address = graphene.String()
    zip_code = graphene.String()
    municipality = graphene.String()
    company_name = graphene.String()
    business_id = graphene.String()
    boat_type = graphene.ID()
    boat_registration_number = graphene.String()
    boat_name = graphene.String()
    boat_model = graphene.String()
    boat_length = graphene.Decimal()
    boat_width = graphene.Decimal()
    application_code = graphene.String()
    accept_boating_newsletter = graphene.Boolean()
    accept_fitness_news = graphene.Boolean()
    accept_library_news = graphene.Boolean()
    accept_other_culture_news = graphene.Boolean()
    boat_draught = graphene.Decimal()
    boat_weight = graphene.Decimal()


class WinterStorageAreaChoiceInput(graphene.InputObjectType):
    winter_area_id = graphene.ID(required=True)
    priority = graphene.Int(required=True)


class WinterStorageApplicationInput(BaseApplicationInput):
    storage_method = WinterStorageMethodEnum(required=True)
    trailer_registration_number = graphene.String()
    chosen_areas = graphene.List(
        graphene.NonNull(WinterStorageAreaChoiceInput), required=True
    )


class UpdateBerthApplicationInput(BaseUpdateApplicationInput):
    accessibility_required = graphene.Boolean()
    boat_propulsion = graphene.String()
    boat_hull_material = graphene.String()
    boat_intended_use = graphene.String()
    rent_from = graphene.String()
    rent_till = graphene.String()
    boat_is_inspected = graphene.Boolean()
    boat_is_insured = graphene.Boolean()
    add_choices = graphene.List(
        graphene.NonNull(HarborChoiceInput),
        description="A list of `HarborChoiceInput` that will be created for the passed application. "
        "They are appended to the list of choices and do not replace the existing ones.",
    )
    remove_choices = graphene.List(
        graphene.NonNull(graphene.Int),
        description='A list of priority "ids" of choices that will be deleted. '
        "It has higher priority than `addChoices` "
        "(i.e. it's executed first)",
    )


class UpdateWinterStorageApplicationInput(BaseUpdateApplicationInput):
    storage_method = WinterStorageMethodEnum()
    trailer_registration_number = graphene.String()
    add_choices = graphene.List(
        graphene.NonNull(WinterStorageAreaChoiceInput),
        description="A list of `WinterStorageAreaChoiceInput` that will be created for the passed application. "
        "They are appended to the list of choices and do not replace the existing ones.",
    )
    remove_choices = graphene.List(
        graphene.NonNull(graphene.ID),
        description="A list of `ID`s of choices that will be deleted. It has higher priority than `addChoices` "
        "(i.e. it's executed first)",
    )
