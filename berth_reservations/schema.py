import graphene

import applications.schema
import harbors.schema
from payments.schema import OldAPIMutation, OldAPIQuery


class Query(
    harbors.schema.Query, applications.schema.Query, OldAPIQuery, graphene.ObjectType
):
    pass


class Mutation(applications.schema.Mutation, OldAPIMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
