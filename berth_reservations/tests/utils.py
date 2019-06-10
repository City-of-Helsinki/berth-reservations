import json

from django.test import Client


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
