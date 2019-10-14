# -*- coding: utf-8 -*-
"""
This script parses harbors' data from a CSV file, provided by the City Of Helsinki.
As such it was designed with this specific CSV file's structure in mind.

It collects the data about single berth places
and groups them by piers and harbors:
- harbors are represented by their servicemap ids
- piers are represented by their identifiers
- dimensions are stored in cm

It dumps resulting JSON into a file at the given output path.
This JSON will have the following structure for its items:

"40393": {
    "piers": {
        "A": {
            "3": {
                "width": "200",
                "length": "400",
                "type": "ILMAN PERÄKIINNITYSTÄ"
            },
            "4": {
                "width": "200",
                "length": "400",
                "type": "AISAPAIKKA"
            }
            "5": {
                "width": "200",
                "length": "400",
                "type": "PERÄPOIJUPAIKKA"
            } ...
        } ...
    }
}, ...

"""
import argparse
import csv
import json

# all of these IDs were manually taken from the servicemap,
# based on the given CSV and the data at hel.fi
HARBORS_TO_SERVICEMAP_IDS_MAP = {
    "AIRORANTA": "40393",
    "AURINKOLAHTI": "41636",
    "EHRENSTRÖMINTIE": "40971",
    "ELÄINTARHANLAHTI": "39913",
    "HIETALAHDENALLAS": "41390",
    "HONKALUOTO": "40672",
    "HOPEASALMI": "41926",
    "ISO-SARVASTO": "40166",
    "JAALARANTA": "40827",
    "KATAJANOKKA": "48272",
    "KELLOSAARENRANTA": "40310",
    "KIPPARLAHTI": "41189",
    "KOIVUNIEMEN VENESATAMA": "39950",
    "LAIVALAHTI": "40864",
    "LÄHTEELÄ": "40290",
    "MERIHAKA": "41454",
    "MERI-RASTILA": "41066",
    "MERISATAMA": "40948",
    "MERISATAMARANTA": "45995",
    "MUSTIKKAMAA": "40359",
    "NANDELSTADH": "42225",
    "NAURISSALMI": "40712",
    "PAJALAHTI": "41359",
    "PIKKU KALLAHDEN VENESATAMA": "40590",
    "PITKÄNSILLANRANTA": "41669",
    "POHJOISRANTA": "41150",
    "PORSLAHDEN VENESATAMA": "40842",
    "PUOTILA": "40897",
    "PURSILAHTI": "40800",
    "RAMSAYNRANTA": "41074",
    "RUOHOLAHDEN KANAVA": "40203",
    "SALMISAARI": "40535",
    "SAUKONPAASI": "40627",
    "SAUNALAHTI": "41857",
    "SILTAVUOREN VENESATAMA": "40876",
    "STRÖMSINLAHTI": "42276",
    "TAMMASAARENALLAS": "41472",
    "TERVASAARI": "42136",
    "VASIKKASAARI": "41415",
    "VUOSAARI": "41637",
    "VÄHÄNIITTY": "42130",
}

ROWS_TO_BE_SKIPPED = [  # random lines with no other values
    "RUOHOLAHTI",
    "HUMALLAHTI",
    "VARSASAARI",
]

PIERS_TO_HARBOR_NAME_MAP = {  # some lines have actually pier names in "SATAMA" column
    "EHRENSTRÖMINTIE 21": "EHRENSTRÖMINTIE",
    "EHRENSTRÖMINTIE 22": "EHRENSTRÖMINTIE",
    "PAJALAHTI 10": "PAJALAHTI",
    "PAJALAHTI 11": "PAJALAHTI",
    "PAJALAHTI 19": "PAJALAHTI",
    "VUOSAARENLAHDEN VENESATAMA": "VUOSAARI",
    "VUOSAARI A": "VUOSAARI",
    "VUOSAARI E": "VUOSAARI",
    "VUOSAARI F": "VUOSAARI",
}

final_harbors_dict = {}


def m_to_cm(meters_string):
    return int(float(meters_string) * 100)


def pull_data_from_row(row, target_dict):
    # check that this row has a berth place number, i.e. is an actual berth
    if not row["NRO"]:
        return

    # get servicemap id for the harbor
    harbor_name = row["SATAMA"]
    harbor_servicemap_id = HARBORS_TO_SERVICEMAP_IDS_MAP.get(harbor_name)

    # parse pier identifier for the current row's pier
    if row["LAITURI"] == harbor_name:
        pier_identifier = "-"
    else:
        pier_identifier = row["LAITURI"].replace(harbor_name + " ", "")

    if harbor_servicemap_id not in target_dict:
        target_dict.update(
            {
                harbor_servicemap_id: {
                    "piers": {
                        pier_identifier: {
                            row["NRO"]: {
                                "length": m_to_cm(row["PITUUS"] or 0),
                                "width": m_to_cm(row["LEVEYS"] or 0),
                                "type": row["LAITURIPAIKAN_TYYPPI"],
                            }
                        }
                    }
                }
            }
        )
    else:
        if pier_identifier in target_dict[harbor_servicemap_id]["piers"]:
            target_dict[harbor_servicemap_id]["piers"][pier_identifier][row["NRO"]] = {
                "length": m_to_cm(row["PITUUS"] or 0),
                "width": m_to_cm(row["LEVEYS"] or 0),
                "type": row["LAITURIPAIKAN_TYYPPI"],
            }
        else:
            target_dict[harbor_servicemap_id]["piers"][pier_identifier] = {
                row["NRO"]: {
                    "length": m_to_cm(row["PITUUS"] or 0),
                    "width": m_to_cm(row["LEVEYS"] or 0),
                    "type": row["LAITURIPAIKAN_TYYPPI"],
                }
            }


parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument(
    "-i", action="store", dest="input_file", help="Path to CSV file with harbors' data"
)
parser.add_argument(
    "-o",
    action="store",
    dest="output_file",
    help="Path to JSON file, where resulting data will be dumped",
)
args = parser.parse_args()


# read the CSV file
with open(args.input_file, "r", encoding="ISO-8859-1") as harbors_csv:
    csv_file_reader = csv.DictReader(harbors_csv, delimiter=";")
    previous_row = None
    for row in csv_file_reader:
        if row["SATAMA"] in ROWS_TO_BE_SKIPPED:
            continue

        if row["SATAMA"] == " ":
            # combine this and previous row into one due to a bug in original csv file
            # this row then becomes just a regular dict, while others are OrderedDict,
            # but it should not be a problem for this script
            actual_row_values = (
                list(previous_row.values())[:7] + list(row.values())[1:]
            )[: len(row)]
            row = dict(zip(csv_file_reader.fieldnames, actual_row_values))
            # this also means that previous row was incomplete
            previous_row = None

        if row["SATAMA"] in PIERS_TO_HARBOR_NAME_MAP:
            row["SATAMA"] = PIERS_TO_HARBOR_NAME_MAP.get(row["SATAMA"])

        if previous_row:
            pull_data_from_row(previous_row, final_harbors_dict)

        previous_row = row

    # do this once more for the last row in csv file
    pull_data_from_row(previous_row, final_harbors_dict)


# save results in a JSON file
with open(args.output_file, "w") as json_file:
    json.dump(final_harbors_dict, json_file, ensure_ascii=False, indent=2)
