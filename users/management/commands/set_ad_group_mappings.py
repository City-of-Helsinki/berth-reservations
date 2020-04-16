from django.core.management import BaseCommand
from helusers.models import ADGroup, ADGroupMapping

# Group order:
BERTH_SERVICES = 0
BERTH_HANDLER = 1
BERTH_SUPERVISOR = 2
HARBOR_SERVICES = 3

AD_GROUP_MAP = {
    BERTH_SERVICES: {"display_name": "Berth services", "ad_group_name": "paakayttaja"},
    BERTH_SUPERVISOR: {
        "display_name": "Berth supervisor",
        "ad_group_name": "katselija",
    },
    BERTH_HANDLER: {"display_name": "Berth handler", "ad_group_name": "kasittelija"},
    HARBOR_SERVICES: {
        "display_name": "Harbor services",
        "ad_group_name": "satamapalvelu",
    },
}


class Command(BaseCommand):
    help = "Sets predefined AD group mappings for the predefined Venepaikka groups"

    def handle(self, *args, **options):
        # Clean all Venepaikka-related ADGroups, this also removes the ADGroupMappings
        ADGroup.objects.filter(
            name__icontains="sg_kuva_ad-tunnistamo_venepaikka_"
        ).delete()

        new_groups = 0
        new_mappings = []

        for group_id, ad_group_details in AD_GROUP_MAP.items():
            display_name, ad_group_name = ad_group_details.values()

            full_name = f"helsinki1\\sg_kuva_ad-tunnistamo_venepaikka_{ad_group_name}"
            ad_group, _ = ADGroup.objects.get_or_create(
                name=full_name, display_name=display_name
            )
            mapping, _ = ADGroupMapping.objects.get_or_create(
                ad_group_id=ad_group.id, group_id=group_id
            )
            new_groups += 1
            new_mappings.append(mapping)

        self.stdout.write(
            self.style.SUCCESS(
                f"Groups added: {new_groups}\nMappings added: {len(new_mappings)}"
            )
        )
        for mapping in new_mappings:
            self.stdout.write(
                f"{mapping.ad_group.display_name} ({mapping.ad_group.name}) -> {mapping.group.name}"
            )
