from django.core.management import BaseCommand

from leases.stickers import create_ws_sticker_sequences


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("Creating WS lease sticker sequences")

        create_ws_sticker_sequences()

        self.stdout.write(self.style.SUCCESS("done!"))
