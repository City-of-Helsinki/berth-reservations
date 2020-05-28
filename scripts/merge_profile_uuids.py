"""
This script merges together two json files with the specific names and format:

1. "berth_profile_uuids.json" - the output of helsinki profile's import view.
It contains a dict of key-value pairs where the key is the customer_id and the
value is the UUID of the newly created profile object for that customer.

2. "berth_profile_stubs.json" - the output of "parse_berth_customers_data_csv.py"
script - which has a dict of key-value pairs where the key is the customer_id and
the value is another dict with data to be imported into the berth-reservations
backend.

This script will inject the UUIDs from the first file into appropriate customers'
data dict from the second file under the key "id". The dicts with customers' data
will be dumped as a list into the "berth_profiles.json" file. This is how that
file's format will look like:
    ...
    {
        "customer_id": "313431",
        "leases": [
            {
                "harbor_servicemap_id": "41074",
                "berth_number": 4,
                "start_date": "2019-06-10",
                "end_date": "2019-09-14",
                "boat_index": 0
            }
        ],
        "boats": [
            {
                "boat_type": "Perämoottorivene",
                "name": "McBoatface 111",
                "registration_number": "31123A",
                "width": "2.00",
                "length": "5.30",
                "draught": null,
                "weight": null
            }
        ],
        "orders": [
            {
                "created_at": "2019-12-02 00:00:00.000",
                "order_sum": "251.00",
                "vat_percentage": "25.0",
                "berth": {
                    "harbor_id": "41074",
                    "berth_number": 4
                },
                "comment": "Laskunumero: 247509 RAMSAYRANTA A 004"
            }
        ],
        "organization": {
            "type": "company",
            "name": "Nice Profitable Firm Ltd.",
            "address": "Mannerheimintie 1 A 1",
            "postal_code": "00100",
            "city": "Helsinki"
        },
        "comment": "VENEPAIKKA PERUTTU 9.1.2012 Hetu/Y-tunnus Timmistä: 01018000T"
        "id": "98edea83-4c92-4dda-bb90-f22e9dafe94c"
    },
    {
        "customer_id": "313432",
        "leases": [
            {
                "harbor_servicemap_id": "40897",
                "berth_number": 17,
                "start_date": "2019-06-10",
                "end_date": "2019-09-14"
            }
        ],
        "boats": [
            {
                "boat_type": "Jollavene",
                "name": "My Boaty",
                "registration_number": "",
                "width": "1.40",
                "length": "3.30",
                "draught": null,
                "weight": 500
            }
        ],
        "orders": [],
        "comment": "",
        "id": "48319ebc-5eaf-4285-a565-15848225614b"
    },
    ...

This file will then be imported into berth-reservations backend using custom
import view in Django admin, that is expecting json file with this structure.
Profiles will be created using the UUIDs in the "id" field in order to have
them federated between berth-reservations and helsinki profile services.

If some of the customer_ids could not be found in the "berth_profile_uuids.json",
they will be dumped as a list into "customers_missing_uuids.txt" and displayed
as the standard error output of this script.
"""

import json
import sys


def do_merge():
    profile_stubs = {}
    profile_uuids = {}
    customers_missing_uuids = []

    with open("berth_profile_stubs.json", "r") as stubs_json_file:
        profile_stubs = json.load(stubs_json_file)

    with open("berth_profile_uuids.json", "r") as uuids_json_file:
        profile_uuids = json.load(uuids_json_file)

    for customer_id, profile_stub in profile_stubs.items():
        profile_uuid = profile_uuids.get(customer_id)
        if profile_uuid:
            profile_stub["id"] = profile_uuid
        else:
            customers_missing_uuids.append(customer_id)

    with open("berth_profiles.json", "w") as json_file:
        json.dump(list(profile_stubs.values()), json_file, ensure_ascii=False, indent=2)

    if customers_missing_uuids:
        with open("customers_missing_uuids.txt", "w") as txt_file:
            txt_file.write("\n".join(customers_missing_uuids))

        sys.stderr.write("Could not find UUIDs for the following customers:\n")
        for customer_id in customers_missing_uuids:
            sys.stderr.write(customer_id + "\n")


if __name__ == "__main__":
    do_merge()
