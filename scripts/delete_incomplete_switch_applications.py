import csv

from applications.models import BerthApplication
from resources.models import Berth, Harbor, Pier

old_harbor_mapping = {
    1: "40393",
    2: "41636",
    3: "40971",
    4: "39913",
    5: "41390",
    6: "40672",
    7: "41926",
    8: "40166",
    9: "40827",
    10: "48272",
    11: "40310",
    12: "41189",
    13: "39950",
    14: "40864",
    15: "40290",
    16: "41454",
    17: "41066",
    18: "40948",
    19: "45995",
    20: "40359",
    21: "42225",
    22: "40712",
    23: "41359",
    24: "40590",
    25: "41669",
    26: "41150",
    27: "40842",
    28: "40897",
    29: "40800",
    30: "41074",
    31: "40203",
    32: "40535",
    33: "40627",
    34: "41857",
    35: "40876",
    36: "42276",
    37: "41472",
    38: "42136",
    39: "41415",
    40: "41637",
    41: "42130",
    42: "48272",
    43: "41189",
    44: "40359",
    45: "41359",
    46: "40393",
    47: "40864",
    48: "40864",
    49: "41454",
    50: "40971",
    51: "41472",
    52: "41390",
}

customers = []

for application in BerthApplication.objects.filter(berth_switch__isnull=False):
    switch = application.berth_switch
    try:
        harbor_servicemap_id = old_harbor_mapping[int(switch.harbor.id)]
        harbor = Harbor.objects.get(servicemap_id=harbor_servicemap_id)
        pier = Pier.objects.filter(
            harbor=harbor, identifier__iexact=switch.pier
        ).first()
        if not pier and harbor.piers.count() == 1:
            pier = harbor.piers.first()
        _ = Berth.objects.get(pier=pier, number=switch.berth_number,)
    except (Berth.DoesNotExist, Pier.DoesNotExist, Harbor.DoesNotExist):
        customers.append(
            [
                application.id,
                application.first_name,
                application.last_name,
                application.email,
                application.phone_number,
                switch.harbor.name,
                switch.pier,
                switch.berth_number,
            ]
        )

with open("customers.csv", mode="w+") as csvfile:
    writer = csv.writer(csvfile, delimiter=",", quotechar='"',)
    for customer in customers:
        writer.writerow(customer)
