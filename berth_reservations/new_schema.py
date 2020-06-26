import django_ilmoitin.api.schema as django_ilmoitin_schema
import graphene
from django_ilmoitin.models import NotificationTemplate
from graphene_federation import build_schema

import applications.new_schema
import customers.schema
import leases.schema
import payments.schema
import resources.schema
from users.decorators import view_permission_required

# =====================================================
# New GraphQL API for the new 'resources' app
#
# Needed to avoid conflicting types and names with
# the old resources from the 'harbors' app.
# =====================================================


class Query(
    applications.new_schema.Query,
    customers.schema.Query,
    leases.schema.Query,
    resources.schema.Query,
    payments.schema.Query,
    django_ilmoitin_schema.Query,
    graphene.ObjectType,
):
    @staticmethod
    @view_permission_required(NotificationTemplate)
    def resolve_notification_templates(parent, info, **kwargs):
        return django_ilmoitin_schema.Query.resolve_notification_templates(
            parent, info, **kwargs
        )


class Mutation(
    applications.new_schema.Mutation,
    customers.schema.Mutation,
    leases.schema.Mutation,
    resources.schema.Mutation,
    payments.schema.Mutation,
    graphene.ObjectType,
):
    pass


# We need to list all the extended types separately,
# otherwise graphene will not generate their schemas.
extended_types = [customers.schema.ProfileNode]


new_schema = build_schema(query=Query, mutation=Mutation, types=extended_types)
