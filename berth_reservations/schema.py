import graphene

import applications.schema
import harbors.schema
from payments.schema import OldAPIMutation


class Query(harbors.schema.Query, applications.schema.Query, graphene.ObjectType):
    pass


class Mutation(applications.schema.Mutation, OldAPIMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
