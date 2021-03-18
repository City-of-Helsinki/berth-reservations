from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from resources.models import Harbor, Pier

from ...models import Harbor as OldHarbor

HARBOR_TO_HARBOR_MAPPINGS = {
    # New harbor id: Old harbor id
    "70481d5c-9264-4c81-87af-e5cf7fb4efa0": 2,
    "01b75ef7-82d5-4b38-8aa1-b7bddb2b2019": 29,
    "2cf50e2f-e101-48bd-8dfd-cf0d7501b654": 4,
    "5bf79d9b-b983-46b7-9b9f-2999827a0b0c": 25,
    "13054f0b-8392-4d0f-8731-9af4093a5303": 6,
    "f7c6ab86-84cb-40f0-9eb2-3f82124b648b": 7,
    "5141e8c0-3491-46b2-898a-16523c54df48": 13,
    "5299c27c-3cdb-4117-9f69-54bf3576927b": 15,
    "e01a17fc-1702-4a4e-99a7-60ea027b935d": 17,
    "9190743a-f883-4f92-8923-f572157bf6ab": 16,
    "8f2296b1-86b7-4059-8a24-efdcd726207d": 18,
    "a909810e-cff1-4360-8005-79c8d0269c6b": 19,
    "97c033ad-5470-4225-a49b-03958ce910e1": 21,
    "a1c7888b-bfe4-49c8-a0f9-fd6ba67bb877": 22,
    "9a8d8313-eaa2-47d2-8f2d-2bb9893f9bc7": 23,
    "657ee3c0-c787-4e9e-bd7c-64ea3a534835": 24,
    "0fbae9d8-039e-47e4-aec7-9aaa00306af2": 26,
    "78ef4aa0-22db-4bc7-bc2d-92e44f67a0fe": 27,
    "368f0621-b856-48fa-8224-0046cfd923ad": 28,
    "b7148154-dba9-4e3b-9d6e-c5636a25aa39": 30,
    "3c35c79d-8169-4885-bdef-57e343bb43e9": 9,
    "95f0636e-f84e-48a6-bb6a-c716354c40f6": 11,
    "a4d2408c-ccd2-419a-9da8-676b0fd9e73b": 31,
    "63c03361-4530-47fe-9902-37c9d6429034": 32,
    "4e700275-1e3d-43df-8407-b00d91195bf7": 8,
    "c1bf3e03-aa6d-408f-963e-d655bcbd47b2": 33,
    "e30e7a3e-3626-4beb-9d8e-8a0e86f115a4": 34,
    "302ac304-9839-437a-811d-e53e074a999a": 35,
    "bf5a852a-f79a-4afe-b5ad-5d01e52e7bc3": 36,
    "ebc222e2-e7a4-4639-af35-de60075dd336": 38,
    "3d05bb47-4fc1-468b-b326-70bcee5d0cb2": 41,
    "4e982440-d032-4d9e-a827-e1c89e86da51": 39,
    "deb09f00-4ec3-4b5e-95c9-af296acd071b": 40,
}
HARBOR_TO_PIER_MAPPINGS = {
    # Pier id: Old harbor id
    "702634ab-51a3-4e79-85bb-0a284165f929": 1,
    "013d1eb5-03ea-427a-82d8-4ac70c31ecaa": 46,
    "786b229b-9bbd-4374-9f2c-a74c826f3add": 5,
    "e6a51db3-d7ed-46fe-8f70-7f4f5bc4ebba": 10,
    "99bb90e6-ebd5-4bed-8e5a-2a5c41321da6": 42,
    "68e20b31-1493-45fc-ac2c-dc6213d7709b": 12,
    "45ac7c00-f70e-4b08-a816-d6194b2df6b4": 43,
    "a58e0114-6da0-4342-8394-0ace16cafd03": 14,
    "541473a5-9fc9-4d38-874b-6b11448e62b2": 14,
    "8a3558e0-88d3-484d-88f8-9e66c79f4326": 14,
    "3eff925b-a7a5-423d-baa7-70cb4148972d": 14,
    "caecb1e6-ce4b-4b60-bb15-f258bc250d04": 48,
    "345fc0b2-0a6a-4833-abc3-f72fcba2501c": 47,
    "a66c0e04-9593-4ba3-85f4-91d7c8cf407f": 3,
    "4c62cec8-a1ad-4a03-80e6-f97ddcac6ed6": 50,
    "2dc196bb-ec3a-4924-a46e-4fde3950455c": 20,
    "551b02f3-2c46-4bc4-9c26-82db3442e44d": 20,
    "2d8cd0cb-cae3-401e-9fc8-cd20e39c419a": 44,
    "204dfbfc-9bb5-429b-9c92-46953735d142": 37,
    "1c0b58f0-b66b-4593-8d77-964e26fc6101": 51,
}


class Command(BaseCommand):
    def handle(self, **options):
        cleaned_harbors = 0
        cleaned_piers = 0
        updated_harbors = 0
        updated_piers = 0
        failed_harbors = []
        failed_piers = []

        for harbor in OldHarbor.objects.filter(resources_harbor__isnull=False):
            harbor.resources_harbor = None
            harbor.save()
            cleaned_harbors += 1
        self.stdout.write("Harbors cleaned: " + str(cleaned_harbors))

        for pier in Pier.objects.filter(harbors_harbor__isnull=False):
            pier.harbors_harbor = None
            pier.save()
            cleaned_piers += 1
        self.stdout.write("Piers cleaned: " + str(cleaned_piers))

        for new_id, old_id in HARBOR_TO_HARBOR_MAPPINGS.items():
            try:
                old_harbor: OldHarbor = OldHarbor.objects.get(id=old_id)
                new_harbor: Harbor = Harbor.objects.get(id=new_id)

                old_harbor.resources_harbor = new_harbor
                old_harbor.save()
                updated_harbors += 1
            except (OldHarbor.DoesNotExist, Harbor.DoesNotExist, ValidationError) as e:
                failed_harbors.append({new_id: str(e)})
        self.stdout.write(
            self.style.SUCCESS("Harbors updated: " + str(updated_harbors))
        )

        for pier_id, harbor_id in HARBOR_TO_PIER_MAPPINGS.items():
            try:
                old_harbor: OldHarbor = OldHarbor.objects.get(id=harbor_id)
                pier: Pier = Pier.objects.get(id=pier_id)

                pier.harbors_harbor = old_harbor
                pier.save()
                updated_piers += 1
            except (OldHarbor.DoesNotExist, Harbor.DoesNotExist, ValidationError) as e:
                failed_piers.append({pier_id: str(e)})
        self.stdout.write(self.style.SUCCESS("Piers updated: " + str(updated_piers)))

        self.stdout.write(self.style.ERROR("Harbors failed:"))
        self.stdout.write(str(failed_harbors))
        self.stdout.write(self.style.ERROR("Piers failed:"))
        self.stdout.write(str(failed_piers))
