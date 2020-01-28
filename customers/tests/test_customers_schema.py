from berth_reservations.tests.utils import GraphQLTestClient

client = GraphQLTestClient()


def test_profile_node_gets_extended_properly():
    query = """
        {
            _service {
                sdl
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert (
        # TODO: remove the second "@key" when/if graphene-federartion fixes itself
        'extend type ProfileNode  implements Node  @key(fields: "id") '
        ' @key(fields: "id") {   id: ID! @external'
        in executed["data"]["_service"]["sdl"]
    )
