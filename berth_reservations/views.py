import sentry_sdk
from graphene_file_upload.django import FileUploadGraphQLView

from .exceptions import VenepaikkaGraphQLError


class SentryGraphQLView(FileUploadGraphQLView):
    def execute_graphql_request(self, request, data, query, *args, **kwargs):
        """
        Extract any exceptions and send some of them to Sentry.
        Avoid sending "common" errors, as objects not found and other stuff that is not relevant to be logged.
        """
        result = super().execute_graphql_request(request, data, query, *args, **kwargs)

        if result and result.errors and not result.invalid:
            errors = [
                e
                for e in result.errors
                if not isinstance(
                    getattr(e, "original_error", None), VenepaikkaGraphQLError
                )
            ]
            if errors:
                self._capture_sentry_exceptions(result.errors, query)
        return result

    def _capture_sentry_exceptions(self, errors, query):
        with sentry_sdk.configure_scope() as scope:
            scope.set_extra("graphql_query", query)
            for error in errors:
                if hasattr(error, "original_error"):
                    error = error.original_error
                sentry_sdk.capture_exception(error)
