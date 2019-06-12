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
                    # try to capture the error directly
                    capture_exception(error)
                except Exception as e:
                    # or send this one if the previous
                    # error variable was not the right type
                    capture_exception(e)
        return result
