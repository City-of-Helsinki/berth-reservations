from graphene_django.views import GraphQLView
from sentry_sdk import capture_exception


class SentryGraphQLView(GraphQLView):
    def execute_graphql_request(self, *args, **kwargs):
        """
        Extract any exceptions and send them to Sentry
        """
        result = super().execute_graphql_request(*args, **kwargs)
        if result and result.errors:
            for error in result.errors:
                try:
                    raise error.original_error
                except Exception as e:
                    capture_exception(e)
        return result
