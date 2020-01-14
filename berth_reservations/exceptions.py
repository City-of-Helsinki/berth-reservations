from graphql import GraphQLError


class VenepaikkaGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""
