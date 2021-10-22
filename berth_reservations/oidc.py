from helusers.oidc import ApiTokenAuthentication


class GraphQLApiTokenAuthentication(ApiTokenAuthentication):
    """
    Custom wrapper for the helusers.oidc.ApiTokenAuthentication backend.
    Needed to make it work with graphql_jwt.middleware.JSONWebTokenMiddleware,
    which in turn calls django.contrib.auth.middleware.AuthenticationMiddleware.
    Authenticate function should:
    1. accept kwargs, or django's auth middleware will not call it
    2. return only the user object, or django's auth middleware will fail
    """

    def authenticate(self, request, **kwargs):
        user_auth_tuple = super().authenticate(request)
        if not user_auth_tuple:
            return None
        user, auth = user_auth_tuple
        return user

    def __convert_amr_to_list(self, id_token):
        """
        OIDC's amr validation fails, since Tunnistamo sends the amr as a string
        instead of a list:
        https://github.com/City-of-Helsinki/tunnistamo/commit/a1b434bbbff92466a144f914a98985008d0ea836.
        To fix the claim validation issue, convert the id_token amr to list
        when a string is given.

        Stolen from https://github.com/City-of-Helsinki/palvelutarjotin/blob/39be680396096ad249db026809efec29d8f91519/palvelutarjotin/oidc.py  # noqa
        """
        if id_token["amr"] and not isinstance(id_token["amr"], list):
            id_token["amr"] = [id_token["amr"]]

    def validate_claims(self, id_token):
        self.__convert_amr_to_list(id_token)
        super().validate_claims(id_token)
