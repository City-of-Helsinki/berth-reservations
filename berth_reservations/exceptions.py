from typing import Any, Dict, Optional

from graphql import GraphQLError


class VenepaikkaGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""

    def __init__(self, message: str, extensions: Optional[Dict[str, Any]] = None):
        if type(extensions) is dict:
            extensions = {**extensions, "type": "VENEPAIKKA_ERROR"}
        else:
            extensions = {"type": "VENEPAIKKA_ERROR"}
        super().__init__(message, extensions=extensions)


class VenepaikkaGraphQLWarning(GraphQLError):
    """GraphQLError that is not sent to Sentry."""

    def __init__(self, message: str, extensions: Optional[Dict[str, Any]] = None):
        if type(extensions) is dict:
            extensions = {**extensions, "type": "VENEPAIKKA_WARNING"}
        else:
            extensions = {"type": "VENEPAIKKA_WARNING"}
        super().__init__(message, extensions=extensions)
