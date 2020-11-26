import json
from dataclasses import dataclass
from typing import Dict
from uuid import UUID

import requests
from django.http import HttpRequest

from utils.relay import from_global_id, to_global_id

PROFILE_API_URL = "PROFILE_API_URL"
PROFILE_TOKEN_SERVICE = "PROFILE_TOKEN_SERVICE"


@dataclass
class HelsinkiProfileUser:
    id: UUID
    first_name: str = ""
    last_name: str = ""
    email: str = ""


class ProfileService:
    profile_token: str
    api_url: str
    token_service_name: str

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
                    }
                }
            }
        }
    """

    def __init__(self, request, **kwargs):
        if "config" in kwargs:
            self.config = kwargs.get("config")

        self.api_url = self.config.get(PROFILE_API_URL)
        self.token_service_name = self.config.get(PROFILE_TOKEN_SERVICE)
        self.profile_token = self._get_city_profile_token(request)

    @staticmethod
    def get_config_template():
        return {
            PROFILE_API_URL: str,
            PROFILE_TOKEN_SERVICE: str,
        }

    def _get_city_profile_token(self, request: HttpRequest):
        api_tokens = request.META.get("HTTP_API_TOKENS")
        if not api_tokens:
            raise Exception("Missing tokens")

        parsed_api_tokens = json.loads(api_tokens)
        profile_token = parsed_api_tokens.get(self.token_service_name)
        if not profile_token:
            raise Exception("No token found in the request")

        return profile_token

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
                }}
            }}
        """

        response = self.query(query)
        user = self.parse_user(response.pop("profile"))
        return user

    def parse_user_edge(self, gql_edge: Dict[str, dict]) -> HelsinkiProfileUser:
        return self.parse_user(gql_edge.get("node"))

    def parse_user(self, profile: Dict[str, dict]) -> HelsinkiProfileUser:
        user_id = from_global_id(profile.pop("id"))
        email = (profile.pop("primary_email") or {}).get("email")
        return HelsinkiProfileUser(UUID(user_id), email=email, **profile)

    def query(self, query: str) -> Dict[str, dict]:
        query = {"query": query}
        headers = {"Authorization": "Bearer %s" % self.profile_token}
        r = requests.post(url=self.api_url, json=query, headers=headers)
        return r.json().get("data", {})
