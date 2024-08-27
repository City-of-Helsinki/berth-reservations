"""
Generate test data for testing berth lease invoicing.

Example run of script:
python scripts/create_dummy_profiles_json.py 5 -e haavikko@dataflow.fi -p city_profiles.json -c customer_profiles.json

This script creates two JSON data files:

1. JSON data file that is suitable for importing to the Helsinki profile service,
   specified with the -p command line argument.
   For more details, see open-city-profile project, models.Profile.import_customer_data

2. JSON data file that contains the customer profiles, specified with the -c command line argument.
   See CustomerProfileManager.import_customer_data for details.

Use -e argument to specify the email addresses for dummy customers.
If multiple emails are specified, then each dummy customer is assigned a random address from the list.
Use -e RANDOM to generate random emails.

NOTE: the second file needs additional processing before importing.
CustomerProfile needs to have UUID of the profile in the Helsinki profile service,
and the UUID is generated by the Helsinki profile service at import time.
When file (1) is imported, the Helsinki profile admin UI view returns a JSON file containing
a mapping customer_id -> actual UUID, by default named export.json

After processing, run merge_profile_uuids.py script as follows:
python scripts/merge_profile_uuids.py -b <profiles_file_name> -m export.json
This script creates files named berth_profiles_<NN>.json, which can be imported via the admin UI.

api_url - use to fetch data about berths, piers and harbors. Running this script only reads data from the API,
it does not change data in the server. The data is used to:
* assign dummy customers to berths that are actually available
* ensure dummy boats that fit in their berth

-e flag can be used to specify the email address(es) to use for dummy users.
If we actually send lots of emails while testing, then the
recipient address should probably be a real email address, not something random.
Mailgun (email service used as of 2020-12) has spammer detection logic and if it sees a lot of
undeliverable mail, it might decide we are up to no good. "Mailgun has thresholds in place that if
exceeded will result in a domain being temporarily disabled."

For more help on available arguments, run the script with -h flag.

Last name of the generated profiles starts with "Berth" so that the generated profiles
can be identified in the database.

"""

import argparse
import datetime
import json
import os
import random
import string
import sys
import traceback
import uuid

import django
from faker import Faker
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from payments.models import DEFAULT_TAX_PERCENTAGE
from payments.utils import tax_percentage_as_string

fake = Faker("fi_FI")

HELSINKI_PROFILE_TEMPLATE = {
    "customer_id": lambda: str(uuid.uuid4()),
    "first_name": fake.first_name,
    "last_name": lambda: "Berth" + fake.last_name(),
    "email": lambda: f"{fake.pystr(min_chars=10, max_chars=10)}@{fake.pystr(min_chars=10, max_chars=10)}.com",
    "address": {
        "postal_code": fake.postcode,
        "address": fake.street_address,
        "city": fake.city,
    },
    "phones": [fake.phone_number],
}

COMPANY_TEMPLATE = {
    "type": "company",
    "name": fake.company,
    "address": fake.address,
    "postal_code": fake.postcode,
    "city": fake.city,
}


def generate_organization():
    if random.random() > 0.9:
        return COMPANY_TEMPLATE
    else:
        return None


# place for variables that are used while applying a template
template_context = {}

LEASE_TEMPLATE = {
    "harbor_servicemap_id": lambda: template_context["berth"]["harbor_servicemap_id"],
    "pier_id": lambda: template_context["berth"]["pier_identifier"],
    "berth_number": lambda: int(template_context["berth"]["number"]),
    "start_date": lambda: calculate_season_start_date(
        datetime.date(template_context["season_year"], 1, 1)
    ).isoformat(),
    "end_date": lambda: calculate_season_end_date(
        datetime.date(template_context["season_year"], 1, 1)
    ).isoformat(),
    "boat_index": lambda: template_context["boat_index"],
}


def _order_created_at():
    return fake.date_between_dates(
        datetime.date(template_context["season_year"], 1, 1),
        calculate_season_end_date(datetime.date(template_context["season_year"], 1, 1)),
    ).isoformat()


ORDER_TEMPLATE = {
    "order_sum": lambda: str(random_price()),
    "vat_percentage": tax_percentage_as_string(DEFAULT_TAX_PERCENTAGE),
    "is_paid": lambda: random_bool(),
    "created_at": _order_created_at,
    "berth": {
        "harbor_servicemap_id": lambda: template_context["berth"][
            "harbor_servicemap_id"
        ],
        "pier_id": lambda: template_context["berth"]["pier_identifier"],
        "berth_number": lambda: int(template_context["berth"]["number"]),
    },
    "comment": lambda: "Dummy berth " + fake.pystr(min_chars=10, max_chars=10),
}
BOAT_TEMPLATE = {
    "boat_type": lambda: random.choice(
        template_context["berth"]["pier_suitable_boat_types"]
    ),
    "name": fake.first_name,
    "registration_number": lambda: fake.pystr_format(
        string_format="?-#####", letters=string.ascii_uppercase
    ),
    "width": lambda: str(
        template_context["berth"]["width"] - random.choice([0, 0.5, 1])
    ),
    "length": lambda: str(
        template_context["berth"]["length"] - random.choice([0, 0.5, 1])
    ),
    "draught": None,
    "weight": None,
}

# NOTE: boats, leases and orders added separately to profile
CUSTOMER_PROFILE_TEMPLATE = {
    "id": "REPLACE_WITH_UUID_FROM_HELSINKI_PROFILE",
    "comment": "Dummy user",
    "customer_id": "",
    "boats": [],
    "leases": [],
    "orders": [],
    "organization": generate_organization,
}


def fill_template(template):
    if isinstance(template, dict):
        return {k: fill_template(v) for k, v in template.items()}
    elif isinstance(template, list):
        return [fill_template(v) for v in template]
    elif callable(template):
        return fill_template(template())
    else:
        return template


def generate_helsinki_profile(emails):
    if emails:
        HELSINKI_PROFILE_TEMPLATE["email"] = lambda: random.choice(emails)
    return fill_template(HELSINKI_PROFILE_TEMPLATE)


def generate_customer_profile(customer_id, berths, season_year):
    CUSTOMER_PROFILE_TEMPLATE["customer_id"] = customer_id
    customer = fill_template(CUSTOMER_PROFILE_TEMPLATE)
    n_boats = random.choice(
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 3]
    )  # most customers should have just one boat
    for boat_index in range(n_boats):
        template_context["berth"] = berths.pop()
        template_context["boat_index"] = boat_index
        template_context["season_year"] = season_year
        customer["boats"].append(fill_template(BOAT_TEMPLATE))
        customer["leases"].append(fill_template(LEASE_TEMPLATE))
        customer["orders"].append(fill_template(ORDER_TEMPLATE))

    return customer


def generate_profiles_json(
    berths,
    n_profiles,
    helsinki_profile_output_file,
    customer_profile_output_file,
    emails,
    season_year,
):
    helsinki_profiles = []
    customer_profiles = []
    random.shuffle(berths)
    for _ in range(n_profiles):
        helsinki_profiles.append(generate_helsinki_profile(emails))
        customer_id = helsinki_profiles[-1][
            "customer_id"
        ]  # used to match the created Helsinki profiili
        customer_profiles.append(
            generate_customer_profile(customer_id, berths, season_year)
        )

    helsinki_profile_output_file.write(json.dumps(helsinki_profiles, indent=4))
    customer_profile_output_file.write(json.dumps(customer_profiles, indent=4))


# note: if starting the query at berths and including pier and harbor data for each berth, the
# request times out. In order to retrieve data fast enough, had to query harbors -> piers -> berths
# and flatten data
ALL_BERTH_DATA_QUERY = """
{
  harbors {
        edges {
            node {
                properties {
                  piers {
                    edges {
                      node {
                        id
                        properties {
                          suitableBoatTypes {
                            id
                            name
                          }
                          identifier
                          berths {
                            edges {
                              node {
                                id
                                number
                                length
                                width
                                depth
                                isAvailable
                                isActive
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                    servicemapId
                    name
                }
            }
        }
    }
}
"""

# customer profile import needs the boat type names in finnish
BERTH_QUERY_HEADERS = {"Accept-Language": "fi"}


def query_berth_data(api_url):
    transport = RequestsHTTPTransport(url=api_url, headers=BERTH_QUERY_HEADERS)

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql(ALL_BERTH_DATA_QUERY)

    result = client.execute(query)
    if "harbors" not in result:
        raise Exception("Failed to get data from server")
    return result


def get_berth_data(api_url, cache_file_name=None):
    if cache_file_name and os.path.exists(cache_file_name):
        with open(cache_file_name, "r", encoding="utf-8") as f:
            result = json.loads(f.read())
    else:
        result = query_berth_data(api_url)
        if cache_file_name:
            with open(cache_file_name, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)

    # flatten data into a more suitable format for berth assignment
    berths = []
    for harbor_data in result["harbors"]["edges"]:
        for pier_data in harbor_data["node"]["properties"]["piers"]["edges"]:
            for berth_data in pier_data["node"]["properties"]["berths"]["edges"]:
                berth = berth_data["node"]
                if not berth["isAvailable"] or not berth["isActive"]:
                    continue
                berth["harbor_servicemap_id"] = harbor_data["node"]["properties"][
                    "servicemapId"
                ]
                berth["pier_identifier"] = pier_data["node"]["properties"]["identifier"]
                berth["pier_suitable_boat_types"] = [
                    bt["name"]
                    for bt in pier_data["node"]["properties"]["suitableBoatTypes"]
                ]
                if not berth["pier_suitable_boat_types"]:
                    continue
                berths.append(berth)
    if not berths:
        raise Exception("No berths found")
    return berths


if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(PROJECT_ROOT)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "berth_reservations.settings")
    django.setup()

    from leases.utils import calculate_season_end_date, calculate_season_start_date
    from payments.tests.utils import random_bool, random_price

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "n_profiles", type=int, default=10, help="Number of dummy profiles to create"
    )

    parser.add_argument(
        "api_url",
        type=str,
        default="https://venepaikka-api.test.kuva.hel.ninja/graphql_v2/",
        help="Berth API url",
        nargs="?",
    )

    parser.add_argument(
        "-b",
        dest="berth_cache_file",
        type=str,
        help="cache file for berth data, to avoid slow api calls",
    )
    parser.add_argument(
        "-p",
        default=sys.stdout,
        type=argparse.FileType("w", encoding="UTF-8"),
        dest="helsinki_profile_output_file",
        help="Output file name for Helsinki city profile JSON",
    )
    parser.add_argument(
        "-c",
        default=sys.stdout,
        type=argparse.FileType("w", encoding="UTF-8"),
        dest="customer_profile_output_file",
        help="Output file name for berth customer profile JSON",
    )
    parser.add_argument(
        "-e",
        type=str,
        dest="emails",
        nargs="+",
        required=True,
        help="Use fixed email address(es) for all profiles",
    )
    parser.add_argument(
        "-s",
        type=int,
        dest="season_year",
        default=datetime.date.today().year,
        choices=list(
            range(datetime.date.today().year - 3, datetime.date.today().year + 3)
        ),
        help="The year for the generated berth leases (see leases.utils.calculate_season_start_date)",
    )

    args = parser.parse_args()

    if len(args.emails) == 1 and args.emails[0] == "RANDOM":
        # if caller wants really random addresses, it must be set explicitly
        args.emails = []

    try:
        generate_profiles_json(
            get_berth_data(args.api_url, args.berth_cache_file),
            args.n_profiles,
            args.helsinki_profile_output_file,
            args.customer_profile_output_file,
            args.emails,
            args.season_year,
        )
    except Exception:
        traceback.print_exc()
        import pdb

        pdb.post_mortem()
