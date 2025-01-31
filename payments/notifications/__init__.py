from django.db import ProgrammingError
from django_ilmoitin.registry import notifications

from .dummy_context import load_dummy_context
from .types import NotificationType

for value, label in NotificationType.choices:
    notifications.register(value, label)

# The reason to check for this is that there are some race conditions when running the initial migrations.
# Since the load_dummy_context is executed on the module __init__, it's loaded even before the migrations are executed.
#
# So there were some conflicts when running the tests and calling the dummy context before the content types
# were migrated. By adding this check, we just "dismiss" the loading of the dummy context so the application
# can be loaded correctly.
#
# Note that this is not a critical issue or anything of that sort, since
# (1) the content types are already on any running system, that's why this was only failing on fresh test environments,
# (2) even if the dummy context were not loaded, on the next system reboot/deploy it would be loaded
# once the content types are loaded to the db.
try:
    load_dummy_context()
except ProgrammingError as e:
    if "django_content_type" in str(e):
        pass
    else:
        raise e


__all__ = ["NotificationType"]
