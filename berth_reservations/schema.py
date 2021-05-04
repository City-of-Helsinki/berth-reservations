import graphene

import applications.schema
import contracts
import harbors.schema
from payments.schema import OldAPIMutation, OldAPIQuery


class Query(
    harbors.schema.Query,
    applications.schema.Query,
    contracts.schema.Query,
    OldAPIQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    applications.schema.Mutation,
    contracts.schema.Mutation,
    OldAPIMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
