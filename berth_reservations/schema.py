import graphene

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


class NewQuery(resources.schema.Query, graphene.ObjectType):
    pass


new_schema = graphene.Schema(query=NewQuery)
