import graphene
from graphene_federation import build_schema

import customers.schema
import harbors.schema
import reservations.schema
import resources.schema


class Query(harbors.schema.Query, reservations.schema.Query, graphene.ObjectType):
    pass


class Mutation(reservations.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)


# =====================================================
# New GraphQL API for the new 'resources' app
#
# Needed to avoid conflicting types and names with
# the old resources from the 'harbors' app.
# =====================================================


class Query(customers.schema.Query, resources.schema.Query, graphene.ObjectType):
    pass


# We need to list all the extended types separately,
# otherwise graphene will not generate their schemas.
extended_types = [customers.schema.ProfileNode]


new_schema = build_schema(Query, types=extended_types)
