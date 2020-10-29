from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from graphene.test import Client as GrapheneClient
from requests import RequestException

from ..new_schema import new_schema
from ..schema import schema


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


class MockResponse:
    def __init__(self, data, status_code=200):
        self.json_data = data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise RequestException(
                "Mock request error with status_code {}.".format(self.status_code)
            )
        pass


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
    assert str(message) in errors
