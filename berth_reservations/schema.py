import graphene

import applications.schema
import harbors.schema


class Query(harbors.schema.Query, applications.schema.Query, graphene.ObjectType):
    pass


class Mutation(applications.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
