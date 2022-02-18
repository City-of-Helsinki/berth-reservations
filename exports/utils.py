from typing import Type

from graphene_django import DjangoObjectType
from graphql_relay import from_global_id
from rest_framework import serializers

from applications.models import HarborChoice, WinterStorageAreaChoice


def from_global_ids(global_ids: [str], node_type: Type[DjangoObjectType]) -> [str]:
    return [_get_node_id_from_global_id(gid, node_type) for gid in global_ids]


def _get_node_id_from_global_id(
    global_id: str, node_type: Type[DjangoObjectType]
) -> str:
    try:
        name, id = from_global_id(global_id)
    except Exception:
        raise serializers.ValidationError("ID is not in correct format.")
    if name != node_type._meta.name:
        raise serializers.ValidationError("Node type does not match.")
    return id


def parse_choices_to_multiline_string(choices):
    """
    Turns a Queryset of HarborChoice or WinterStorageAreaChoice
    objects into a nice user-friendly string.

    Example of the returned string:

        '1: Aurinkosatama'
        '2: Mustikkamaan satama'

    :type choices: django.db.models.query.QuerySet
    :rtype: str
    """
    choices_str = ""
    for choice in choices:
        if isinstance(choice, HarborChoice):
            single_choice_line = "{}: {}".format(choice.priority, choice.harbor.name)
        elif isinstance(choice, WinterStorageAreaChoice):
            single_choice_line = "{}: {}".format(
                choice.priority, choice.winter_storage_area.name
            )
        else:
            single_choice_line = ""

        if choices_str:
            choices_str += "\n" + single_choice_line
        else:
            choices_str += single_choice_line
    return choices_str


def parse_berth_switch_str(berth_switch):
    """
    Parse a string with berth switch information.

    Examples:

        'Aurinkosatama (B): 5'
        'Mustikkamaan satama: 6'

    :type berth_switch: applications.models.BerthSwitch
    :rtype: str
    """

    berth_switch_str = "{} ({}): {}".format(
        berth_switch.berth.pier.harbor.name,
        berth_switch.berth.pier.identifier,
        berth_switch.berth.number,
    )

    return berth_switch_str
