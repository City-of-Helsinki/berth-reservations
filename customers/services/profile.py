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

    ALL_PROFILES_QUERY = """
        query GetProfiles {
            profiles(serviceType: BERTH, first: %d, after: "%s") {
                pageInfo {
                    endCursor
                    hasNextPage
                }
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
                        primary_address: primaryAddress {
                            address
                            postal_code: postalCode
                            city
                        }
                    }
                }
            }
        }
    """

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

    def get_all_profiles(self) -> Dict[UUID, HelsinkiProfileUser]:
        def _exec_query(after=""):
            response = self.query(self.ALL_PROFILES_QUERY % (100, after))
            edges = response.get("profiles", {}).get("edges", [])

            page_info = response.get("profiles", {}).get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            end_cursor = page_info.get("endCursor", "")
            return edges, has_next, end_cursor

        returned_users = []
        try:
            end_cursor = ""
            while True:
                edges, has_next, end_cursor = _exec_query(after=end_cursor)
                returned_users += edges
                if not has_next:
                    break
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

    def find_profile(
        self,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        phone: str = "",
        force_only_one: bool = True,
    ) -> Union[List[HelsinkiProfileUser], HelsinkiProfileUser]:
        """
        Find the profile based on the passed criteria, the missing parameters
        are replaced by empty values.

        force_only_one: bool -> If more than one profile is found, it will raise an error
        """
        query = f"""
            query FindProfile {{
                profiles(
                    serviceType: BERTH,
                    firstName: "{first_name}",
                    lastName: "{last_name}",
                    emails_Email: "{email}",
                    phones_Phone: "{phone}"
                ) {{
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
                        }}
                    }}
                }}
            }}
        """
        response = self.query(query)
        profiles = (
            response.get("profiles", {}).get("edges", [])
            if response
            and response.get("profiles", {})
            and response.get("profiles", {}).get("edges")
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
        profile_id = from_global_id(global_id)
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
        body = {"query": query}
        if variables:
            body["variables"] = variables

        headers = {"Authorization": "Bearer %s" % self.profile_token}
        r = requests.post(url=self.api_url, json=body, headers=headers)
        r.raise_for_status()
        response = r.json()
        if errors := response.get("errors"):
            raise ProfileServiceException(str(errors))
        return response.get("data", {})
