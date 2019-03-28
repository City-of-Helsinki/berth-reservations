import graphene

import harbors.schema
import reservations.schema


class Query(harbors.schema.Query, graphene.ObjectType):
    pass


class Mutation(reservations.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
