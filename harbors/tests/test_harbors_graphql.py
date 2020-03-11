def test_get_boat_type(boat_type, old_schema_api_client):
    query = """
        {
            boatTypes {
                name
            }
        }
    """
    executed = old_schema_api_client.execute(query)
    assert executed["data"]["boatTypes"] == [{"name": boat_type.name}]


def test_get_harbors(harbor, old_schema_api_client):
    query = """
        {
            harbors {
                edges {
                    node {
                        properties {
                            name
                            zipCode
                        }
                    }
                }
            }
        }
    """
    executed = old_schema_api_client.execute(query)
    assert executed["data"]["harbors"]["edges"] == [
        {"node": {"properties": {"name": harbor.name, "zipCode": harbor.zip_code}}}
    ]
