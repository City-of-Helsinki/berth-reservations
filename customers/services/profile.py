import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from uuid import UUID

import requests
from django.db import transaction

from customers.exceptions import (
    MultipleProfilesException,
    NoProfilesException,
    ProfileServiceException,
)
from utils.relay import from_global_id, to_global_id

PROFILE_API_URL = "PROFILE_API_URL"
BATCH_SIZE = 100


@dataclass
class HelsinkiProfileUser:
    id: UUID
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    postal_code: str = ""
    city: str = ""


class ProfileService:
    profile_token: str
    api_url: str

    def __init__(self, profile_token, **kwargs):
        if "config" in kwargs:
            self.config = kwargs.get("config")

        self.api_url = self.config.get(PROFILE_API_URL)
        self.profile_token = profile_token

    @staticmethod
    def get_config_template():
        return {
            PROFILE_API_URL: str,
        }

    def get_all_profiles(
        self, profile_ids: List[UUID] = None
    ) -> Dict[UUID, HelsinkiProfileUser]:
        query = """
            query GetProfiles {{
                profiles(serviceType: BERTH, first: {first}, after: "{after}", id: {ids}) {{
                    pageInfo {{
                        endCursor
                        hasNextPage
                    }}
                    edges {{
                        node {{
                            id
                            first_name: firstName
                            last_name: lastName
                            primary_email: primaryEmail {{
                                email
                            }}
                            primary_phone: primaryPhone {{
                                phone
                            }}
                            primary_address: primaryAddress {{
                                address
                                postal_code: postalCode
                                city
                            }}
                        }}
                    }}
                }}
            }}
        """

        def _exec_query(after="", ids: List[Union[str, UUID]] = None):
            if ids is not None:
                # json.dumps forces the converted strings to use double quotes
                # instead of single
                ids = [
                    str(original_id) for original_id in ids if original_id is not None
                ]
                first = len(ids)
            else:
                ids = []
                first = BATCH_SIZE

            parsed_query = query.format(first=first, after=after, ids=json.dumps(ids))
            response = self.query(parsed_query)
            response_edges = response.get("profiles", {}).get("edges", [])

            page_info = response.get("profiles", {}).get("pageInfo", {})
            response_has_next = page_info.get("hasNextPage", False)
            response_end_cursor = page_info.get("endCursor", "")
            return response_edges, response_has_next, response_end_cursor

        returned_users = []
        end_cursor = ""
        has_next = True
        next_batch_ids = []
        id_batches = (
            [
                profile_ids[x : x + BATCH_SIZE]
                for x in range(0, len(profile_ids), BATCH_SIZE)
            ]
            if profile_ids
            else []
        )

        try:
            while has_next or (profile_ids and len(id_batches) > 0):
                if profile_ids:
                    next_batch_ids = id_batches.pop(0)
                    end_cursor = ""

                edges, has_next, end_cursor = _exec_query(
                    after=end_cursor, ids=next_batch_ids
                )
                returned_users += edges

        # Catch network errors
        except requests.exceptions.RequestException:
            pass

        # Parse the users received from the Profile Service
        users = {}
        for edge in returned_users:
            user = self.parse_user_edge(edge)
            users[user.id] = user

        return users

    def get_profile(self, id: UUID) -> HelsinkiProfileUser:
        from ..schema import ProfileNode

        global_id = to_global_id(ProfileNode, id)

        query = f"""
            query GetProfile {{
                profile(serviceType: BERTH, id: "{global_id}") {{
                    id
                    first_name: firstName
                    last_name: lastName
                    primary_email: primaryEmail {{
                        email
                    }}
                    primary_phone: primaryPhone {{
                        phone
                    }}
                    primary_address: primaryAddress {{
                        address
                        postal_code: postalCode
                        city
                    }}
                }}
            }}
        """

        response = self.query(query)
        user = self.parse_user(response.pop("profile"))
        return user

    def get_my_profile(self) -> Optional[HelsinkiProfileUser]:
        query = """
            query MyProfile {
                my_profile: myProfile {
                    id
                    first_name: firstName
                    last_name: lastName
                    primary_email: primaryEmail {
                        email
                    }
                    primary_phone: primaryPhone {
                        phone
                    }
                    primary_address: primaryAddress {
                        address
                        postal_code: postalCode
                        city
                    }
                }
            }
        """

        response = self.query(query)
        my_profile = response.get("my_profile")
        return self.parse_user(my_profile) if my_profile else None

    def find_profile(
        self,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        phone: str = "",
        address: str = "",
        order_by: str = "",
        ids: List[str] = None,
        first: int = None,
        last: int = None,
        before: str = "",
        after: str = "",
        force_only_one: bool = True,
        recursively_fetch_all: bool = False,
        ids_only: bool = False,
    ) -> Union[List[HelsinkiProfileUser], HelsinkiProfileUser]:
        """
        Find the profile based on the passed criteria, the missing parameters
        are replaced by empty values.

        force_only_one: bool -> If more than one profile is found, it will raise an error
        recursively_fetch_all: bool -> If all the pages are needed
        ids_only; bool -> Fetch only Helsinki profile ids: No names or addresses.
        """
        FIND_PROFILE_QUERY_FIELDS = """
                edges {
                    node {
                        id
                        first_name: firstName
                        last_name: lastName
                        primary_email: primaryEmail {
                            email
                        }
                        primary_phone: primaryPhone {
                            phone
                        }
                    }
                }
            """

        FIND_PROFILE_IDS_QUERY_FIELDS = "edges { node { id } }"

        query = (
            """query FindProfile (
                    $id: [UUID!],
                    $firstName: String,
                    $lastName: String,
                    $email: String,
                    $phone: String,
                    $address: String,
                    $orderBy: String,
                    $first: Int,
                    $last: Int,
                    $before: String,
                    $after: String
                ) {
                profiles(
                    serviceType: BERTH,
                    id: $id,
                    firstName: $firstName,
                    lastName: $lastName,
                    emails_Email: $email,
                    phones_Phone: $phone,
                    addresses_Address: $address,
                    orderBy: $orderBy,
                    first: $first,
                    last: $last,
                    before: $before,
                    after: $after
                ){
                pageInfo {
                    has_next_page: hasNextPage,
                    has_previous_page: hasPreviousPage,
                    start_cursor: startCursor,
                    end_cursor: endCursor
                }
                %s
            }
        }
        """
            % FIND_PROFILE_IDS_QUERY_FIELDS
            if ids_only
            else FIND_PROFILE_QUERY_FIELDS
        )

        variables = {
            "id": ids,
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "phone": phone,
            "address": address,
            "orderBy": order_by,
            "first": first,
            "last": last,
            "before": before,
            "after": after,
        }
        response = self.query(query, variables)
        pageInfo = (
            response.get("profiles", {}).get("pageInfo", [])
            if response and response.get("profiles", {}).get("pageInfo")
            else None
        )
        profiles = (
            response.get("profiles", {}).get("edges", [])
            if response and response.get("profiles", {}).get("edges")
            else []
        )

        if force_only_one:
            if len(profiles) > 1:
                ids = [
                    from_global_id(profile_node.get("node", {}).get("id"))
                    for profile_node in profiles
                ]
                raise MultipleProfilesException(ids=ids)
            elif len(profiles) == 0:
                raise NoProfilesException

        users = []
        for profile_edge in profiles:
            users.append(self.parse_user_edge(profile_edge))

        if force_only_one:
            return users[0]

        # NOTE: This rescursive fetch should never be needed,
        # but it's here because the Open city profile responds with a connection timeout.
        if (
            recursively_fetch_all
            and pageInfo.get("has_next_page")
            and pageInfo.get("end_cursor")
        ):
            users = users + self.find_profile(
                ids=ids,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                order_by=order_by,
                first=first,
                last=last,
                after=pageInfo.get("end_cursor"),
                recursively_fetch_all=True,
                force_only_one=False,
                ids_only=ids_only,
            )

        return users

    @transaction.atomic
    def create_profile(
        self, first_name: str, last_name: str, email: str = None, phone: str = None
    ):
        from ..models import CustomerProfile

        variables = {
            "input": {"profile": {"firstName": first_name, "lastName": last_name}}
        }
        if email:
            variables["input"]["profile"]["addEmails"] = [
                {"primary": True, "email": email, "emailType": "NONE"}
            ]
        if phone:
            variables["input"]["profile"]["addPhones"] = [
                {"primary": True, "phone": phone, "phoneType": "NONE"}
            ]

        mutation = """
        mutation CreateProfile($input: CreateProfileMutationInput!) {
            createProfile(input: $input) {
                profile {
                    id
                }
            }
        }
        """
        response = self.query(query=mutation, variables=variables)
        global_id = response.get("createProfile", {}).get("profile", {}).get("id")
        profile_id = UUID(from_global_id(global_id))
        profile = CustomerProfile.objects.create(id=profile_id)
        return profile

    def parse_user_edge(self, gql_edge: Dict[str, dict]) -> HelsinkiProfileUser:
        return self.parse_user(gql_edge.get("node"))

    def parse_user(self, profile: Dict[str, dict]) -> HelsinkiProfileUser:
        user_id = from_global_id(profile.pop("id"))
        email = None
        phone = None
        if "primary_email" in profile:
            primary_email = profile.pop("primary_email")
            email = (primary_email is not None and primary_email.get("email")) or None
        if "primary_phone" in profile:
            primary_phone = profile.pop("primary_phone")
            phone = (primary_phone is not None and primary_phone.get("phone")) or None

        primary_address = profile.pop("primary_address", {}) or {}
        address = primary_address.get("address")
        postal_code = primary_address.get("postal_code")
        city = primary_address.get("city")

        return HelsinkiProfileUser(
            UUID(user_id),
            email=email,
            phone=phone,
            address=address,
            postal_code=postal_code,
            city=city,
            **profile,
        )

    def query(self, query: str, variables: Optional[dict] = None) -> Dict[str, dict]:
        # TODO: Implement cache for this profile fetching
        body = {"query": query}
        if variables:
            body["variables"] = variables

        headers = {"Authorization": "Bearer %s" % self.profile_token}
        r = requests.post(url=self.api_url, json=body, headers=headers, timeout=30)
        r.raise_for_status()
        response = r.json()
        if errors := response.get("errors"):
            raise ProfileServiceException(str(errors))
        return response.get("data", {})
