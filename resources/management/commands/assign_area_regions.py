from django.core.management.base import BaseCommand

from resources.enums import AreaRegion
from resources.models import Harbor, WinterStorageArea

HARBOR_REGIONS = {
    AreaRegion.EAST: [
        "Airorannan venesatama A",
        "Airorannan venesatama B",
        "Aurinkolahden venesatama (Aurinkoranta)",
        "Aurinkolahden venesatama (Pursilahdenranta)",
        "Honkaluoto / Venesatama",
        "Hopeasalmen venesatama",
        "Kipparlahden venesatama",
        "Koivuniemen venesatama",
        "Laivalahden venesatama",
        "Meri-Rastilan venesatama",
        "Mustikkamaan venesatama",
        "Nandelstadhin venesatama",
        "Naurissalmen venesatama (Kipparlahdensilmukka 9)",
        "Pikku Kallahden venesatama",
        "Porslahden venesatama",
        "Puotilan venesatama",
        "Sarvaston venesatama",
        "Strömsinlahden venesatama",
        "Vasikkasaaren venesatama",
        "Vuosaarenlahden venesatama",
        "Vähäniityn venesatama",
    ],
    AreaRegion.WEST: [
        "Eläintarhanlahden venesatama (Pitkänsillanranta)",
        "Eläintarhanlahden venesatama",
        "Hietalahdenallas / Venesatama",
        "Katajanokan venesatama",
        "Lähteelä retkisatama",
        "Merihaan venesatama (Hakaniemenranta 30)",
        "Merisatama (Ehrenströmintie 22)",
        "Merisatama (Ehrenströmintie ranta)",
        "Merisatama (Merisatama 28)",
        "Merisatama (Merisatamanranta 20)",
        "Pajalahden venesatama (Meripuistotie) / Venesatama",
        "Pohjoisranta 3 / Venesatama",
        "Ramsaynrannan venesatama (Ramsaynranta 4)",
        "Ruoholahden venesatama (Jaalaranta)",
        "Ruoholahden venesatama (Kellosaarenranta)",
        "Ruoholahden venesatama (Ruoholahden kanava)",
        "Salmisaaren venesatama",
        "Saukonpaaden venesatama",
        "Saunalahden venesatama (Ramsaynranta 6)",
        "Siltavuoren venesatama",
        "Tammasaaren allas (paikat 1-31)",
        "Tammasaaren allas (paikat 32-75)",
        "Tervasaari (Tervasaarenkannas 1) / Venesatama",
    ],
}

WINTER_STORAGE_AREA_REGIONS = {
    AreaRegion.EAST: [
        "Iso-Sarvasto",
        "Laivalahti",
        "Marjaniemi",
        "Porslahti",
        "Puotila",
        "Ruusuniemi I",
        "Ruusuniemi II",
        "Strömsinlahti",
    ],
    AreaRegion.WEST: [
        "Hernesaari",
        "Kaisaniemi",
        "Lähteelä",
        "Pajalahti",
        "Rajasaari",
    ],
}


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("Assigning Harbor regions")
        self._assign_area_regions(Harbor, HARBOR_REGIONS)
        self.stdout.write("-----")
        self.stdout.write("Assigning Winter Storage Area regions")
        self._assign_area_regions(WinterStorageArea, WINTER_STORAGE_AREA_REGIONS)

    def _assign_area_regions(self, model, regions):
        successful = {}
        total_successful = 0
        failed = []

        for region, areas in regions.items():
            successful[region.label] = 0
            for area_name in areas:
                try:
                    area = model.objects.translated("fi", name=area_name).first()

                    if not area:
                        raise area.DoesNotExist()

                    area.region = region.value
                    area.save()
                    successful[region.label] += 1
                    total_successful += 1
                except (Exception) as e:
                    failed.append({area_name: str(e)})
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned {model._meta.verbose_name.title()} regions: {total_successful}"
            )
        )

        for region, total in successful.items():
            self.stdout.write(f"{region}: {total}")

        if failed:
            self.stdout.write(self.style.ERROR(f"Failed to import {len(failed)} areas"))
            for failed_area in failed:
                self.stdout.write(str(failed_area) + "\n")
