import requests
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from munigeo.models import Municipality

from harbors.models import Harbor


class Command(BaseCommand):
    @staticmethod
    def _get_servicemap_url(sm_id):
        return "https://api.hel.fi/servicemap/v2/unit/{}/".format(sm_id)

    def handle(self, **options):
        updated_harbors = 0

        for harbor in Harbor.objects.all():
            with transaction.atomic():
                self.stdout.write(
                    "Fetching info for harbor with servicemap ID {}".format(
                        harbor.servicemap_id
                    )
                )

                sm_response = requests.get(
                    self._get_servicemap_url(harbor.servicemap_id)
                )
                sm_info = sm_response.json()

                harbor.zip_code = sm_info["address_zip"]
                harbor.www_url = sm_info["www"]["fi"]  # only FI for now
                harbor.email = sm_info["email"]
                harbor.phone = sm_info["phone"]

                harbor.municipality = Municipality.objects.get(
                    id=sm_info["municipality"]
                )

                longitude, latitude = sm_info["location"]["coordinates"]
                harbor.location = Point(longitude, latitude, srid=settings.DEFAULT_SRID)

                harbor.save()

                for lang, value in sm_info["name"].items():
                    harbor.set_current_language(lang)
                    harbor.name = value
                    harbor.save()

                for lang, value in sm_info["street_address"].items():
                    harbor.set_current_language(lang)
                    harbor.street_address = value
                    harbor.save()

                updated_harbors += 1

        self.stdout.write("Successfully updated {} harbors".format(updated_harbors))
