from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = ""

    def handle(self, **options):
        ct = ContentType.objects.filter(app_label="harbors")

        for c in ct:
            c.delete()

        with connection.schema_editor() as schema_editor:
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_availabilitylevel CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_availabilitylevel_id_seq;"
            )
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_availabilitylevel_translation CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_availabilitylevel_translation_id_seq;"
            )
            schema_editor.execute("DROP TABLE IF EXISTS harbors_boattype CASCADE;")
            schema_editor.execute("DROP SEQUENCE IF EXISTS harbors_boattype_id_seq;")
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_boattype_translation CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_boattype_translation_id_seq;"
            )
            schema_editor.execute("DROP TABLE IF EXISTS harbors_harbor CASCADE;")
            schema_editor.execute("DROP SEQUENCE IF EXISTS harbors_harbor_id_seq;")
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_harbor_suitable_boat_types CASCADE"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_harbor_suitable_boat_types_id_seq;"
            )
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_harbor_translation CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_harbor_translation_id_seq;"
            )
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_winterstoragearea CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_winterstoragearea_id_seq;"
            )
            schema_editor.execute(
                "DROP TABLE IF EXISTS harbors_winterstoragearea_translation CASCADE;"
            )
            schema_editor.execute(
                "DROP SEQUENCE IF EXISTS harbors_winterstoragearea_translation_id_seq;"
            )
            schema_editor.execute(
                "DELETE FROM django_migrations WHERE app = 'harbors';"
            )
