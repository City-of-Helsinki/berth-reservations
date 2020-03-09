import json

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory
from graphene.test import Client as GrapheneClient

from berth_reservations.new_schema import new_schema
from berth_reservations.schema import schema


class ApiClient(GrapheneClient):
    def execute(self, *args, **kwargs):
        """
        Custom wrapper on the execute method, that allows passing
        "input" as a keyword argument, which get passed to
        kwargs["variables"]["input"] to comply with the relay
        spec for mutations.
        """

        input = kwargs.pop("input", {})
        if input:
            assert (
                "variables" not in kwargs
            ), 'Do not pass both "variables" and "input" at the same time'
            kwargs["variables"] = {"input": input}
        return super().execute(*args, **kwargs)


def create_api_client(user=None, graphql_v2=True):
    if not user:
        # Django's AuthenticationMiddleware inserts AnonymousUser
        # for all requests, where user is not authenticated.
        user = AnonymousUser()

    if graphql_v2:
        request = RequestFactory().post("/graphql_v2")
        request.user = user
        client = ApiClient(new_schema, context=request)

    else:
        request = RequestFactory().post("/graphql")
        request.user = user
        client = ApiClient(schema, context=request)

    client.user = user

    return client


class GraphQLDjangoTestClient(Client):
    """
    Custom test client to allow configuring language header.
    Standard graphene.test.Client does not allow doing that.
    """

    def execute(
        self,
        query="",
        op_name=None,
        variables=None,
        graphql_url="/graphql/",
        lang="en",
        user=None,
    ):
        """
        Function that posts the passed query to our project's GraphQL endpoint.

        :param query: GraphQL query to run
        :type query: str
        :param op_name: If the query is a mutation or named query, you must
                        supply the op_name.  For annon queries ("{ ... }"),
                        should be None (default).
        :type op_name: str
        :param variables: If provided, the $input variable in GraphQL will be set
                          to this value
        :type variables: None | dict
        :param lang: Language to be set in the "Accept-Language" header.
        :type lang: str
        :param user: In case the query requires authentication, a "user" with the
                     desired permissions can be passed. It will only attempt to
                     login if a user is passed.
        :type user: users.models.User

        :return: response from graphql endpoint.  The response has the "data" key.
                 It will have the "error" key if any error happened.
        :rtype: dict
        """

        body = {"query": query}
        if op_name:
            body["operation_name"] = op_name
        if variables:
            body["variables"] = {"input": variables}

        if user:
            self.force_login(user)

        resp = self.post(
            graphql_url,
            json.dumps(body),
            content_type="application/json",
            HTTP_ACCEPT_LANGUAGE=lang,
        )

        response_json = json.loads(resp.content.decode())
        return response_json


def assert_not_enough_permissions(executed):
    errors = str(executed["errors"])
    assert "You do not have permission to perform this action" in errors


def assert_doesnt_exist(model, executed):
    errors = str(executed["errors"])
    assert f"{model} matching query does not exist" in errors


def assert_field_duplicated(field_name, executed):
    errors = str(executed["errors"])
    assert field_name in errors
    assert "already exists" in errors


def assert_field_missing(field_name, executed):
    errors = str(executed["errors"])
    assert field_name in errors
    assert "found null" in errors


def assert_invalid_enum(field_name, expected_value, executed):
    errors = str(executed["errors"])
    assert expected_value in errors
    assert field_name in errors
    assert f'Expected type "{expected_value}"' in errors


def assert_in_errors(message, executed):
    errors = str(executed["errors"])
    assert message in errors
