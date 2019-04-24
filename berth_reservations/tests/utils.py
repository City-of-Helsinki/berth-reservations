import json

from django.test import Client


def get(api_client, url, status_code=200):
    return _execute_request(api_client, "get", url, status_code)


def post(api_client, url, data=None, status_code=201):
    return _execute_request(api_client, "post", url, status_code, data)


def put(api_client, url, data=None, status_code=200):
    return _execute_request(api_client, "put", url, status_code, data)


def patch(api_client, url, data=None, status_code=200):
    return _execute_request(api_client, "patch", url, status_code, data)


def delete(api_client, url, status_code=204):
    return _execute_request(api_client, "delete", url, status_code)


def _execute_request(api_client, method, url, status_code, data=None):
    response = getattr(api_client, method)(url, data=data)
    assert (
        response.status_code == status_code
    ), "Expected status code {} but got {} with data {}".format(
        status_code, response.status_code, response.data
    )
    return response.data


def check_disallowed_methods(api_client, urls, methods, status_code=405):
    if isinstance(urls, str):
        urls = (urls,)
    if isinstance(methods, str):
        methods = (methods,)

    for url in urls:
        for method in methods:
            response = getattr(api_client, method)(url)
            assert response.status_code == status_code, (
                "%s %s expected %s, but got %s %s"
                % (method, url, status_code, response.status_code, response.data)
            )


class GraphQLTestClient(Client):
    """
    Custom test client to allow configuring language header.
    Standard graphene.test.Client does not allow doing that.
    """

    def execute(self, query="", op_name=None, variables=None, lang="en"):
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

        :return: response from graphql endpoint.  The response has the "data" key.
                 It will have the "error" key if any error happened.
        :rtype: dict
        """

        body = {"query": query}
        if op_name:
            body["operation_name"] = op_name
        if variables:
            body["variables"] = {"input": variables}

        resp = self.post(
            "/graphql/",
            json.dumps(body),
            content_type="application/json",
            HTTP_ACCEPT_LANGUAGE=lang,
        )
        response_json = json.loads(resp.content.decode())
        return response_json
