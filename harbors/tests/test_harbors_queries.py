from graphql_relay.node.node import to_global_id

from harbors.schema import HarborType, WinterStorageAreaType
from harbors.tests.factories import HarborFactory, WinterStorageAreaFactory

CUSTOMER_UI_BOATS_BERTH_TYPES_QUERY = """
      query BoatTypesBerthsQuery {
        boatTypes {
          id
          name
        }
        harbors {
          edges {
            node {
              id
              geometry {
                coordinates
              }
              properties {
                name
                servicemapId
                streetAddress
                zipCode
                municipality
                phone
                email
                wwwUrl
                imageFile
                mooring
                electricity
                water
                wasteCollection
                gate
                lighting
                suitableBoatTypes {
                  id
                }
                availabilityLevel {
                  id
                  title
                  description
                }
                numberOfPlaces
                maximumWidth
                maximumLength
                maximumDepth
              }
            }
          }
        }
      }
    """


def test_get_boat_type(boat_type, old_schema_api_client):
    harbor = HarborFactory()

    executed = old_schema_api_client.execute(CUSTOMER_UI_BOATS_BERTH_TYPES_QUERY)

    harbor_node = executed["data"]["harbors"]["edges"][0]["node"]
    assert harbor_node["id"] == to_global_id(HarborType._meta.name, harbor.id)
    assert harbor_node["properties"]["name"] == harbor.name
    assert harbor_node["properties"]["zipCode"] == harbor.zip_code

    assert executed["data"]["boatTypes"] == [
        {"id": str(boat_type.id), "name": boat_type.name}
    ]


CUSTOMER_UI_WS_AREAS_QUERY = """
      query WinterAreasQuery {
        winterStorageAreas {
          edges {
            node {
              id
              geometry {
                coordinates
              }
              properties {
                name
                streetAddress
                zipCode
                imageFile
                numberOfMarkedPlaces
                maximumWidth: maxWidth
                maximumLength: maxLength
                numberOfSectionSpaces
                servicemapId
                maxLengthOfSectionSpaces
                numberOfUnmarkedSpaces
                electricity
                water
                gate
                repairArea
                summerStorageForDockingEquipment
                summerStorageForTrailers
                summerStorageForBoats
                municipality
                wwwUrl
                availabilityLevel {
                  id
                  title
                  description
                }
              }
            }
          }
        }
      }
    """


def test_get_ws_areas(boat_type, old_schema_api_client):
    area = WinterStorageAreaFactory()

    executed = old_schema_api_client.execute(CUSTOMER_UI_WS_AREAS_QUERY)

    area_node = executed["data"]["winterStorageAreas"]["edges"][0]["node"]
    assert area_node["id"] == to_global_id(WinterStorageAreaType._meta.name, area.id)
    assert area_node["properties"]["name"] == area.name
