from django.contrib.auth.models import Group, Permission
from django.core.management import BaseCommand

PERMISSION_TYPES = (
    "view",
    "add",
    "change",
    "delete",
)

# Group order:
BERTH_SERVICES = 0
BERTH_HANDLER = 1
BERTH_SUPERVISOR = 2
HARBOR_SERVICES = 3

# Format to add a model:
# {
#     "app_name": {
#         "model": {
#             ROLE1: ("perm1", "perm2"),
#             ROLE2: None
#         }
#     }
# }
DEFAULT_MODELS_PERMS = {
    "applications": {
        "harborchoice": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "winterstorageareachoice": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "berthswitchreason": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view",),
        },
        "berthswitch": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "berthapplication": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "winterstorageapplication": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
    },
    "customers": {
        "customerprofile": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "company": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "boat": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "boatcertificate": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
    },
    "resources": {
        "boattype": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "availabilitylevel": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "harbor": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstoragearea": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "harbormap": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstorageareamap": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "pier": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstoragesection": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "berthtype": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstorageplacetype": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "berth": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstorageplace": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
    },
    "leases": {
        "berthlease": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view", "add", "change", "delete",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "winterstoragelease": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view", "add", "change", "delete",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "berthleasechange": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view", "add", "change", "delete",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
        "winterstorageleasechange": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view", "add", "change", "delete",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: None,
        },
    },
    "harbors": {
        "boattype": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "availabilitylevel": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "harbor": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
        "winterstoragearea": {
            BERTH_SERVICES: ("view", "add", "change", "delete",),
            BERTH_HANDLER: ("view",),
            BERTH_SUPERVISOR: ("view",),
            HARBOR_SERVICES: ("view", "add", "change", "delete",),
        },
    },
}


class Command(BaseCommand):
    def handle(self, *args, **options):  # noqa: C901
        # Parse permission tree
        groups = {group.id: group for group in Group.objects.all()}
        permissions = {
            f"{perm.content_type.app_label}.{perm.codename}": perm
            for perm in Permission.objects.all()
        }

        group_permissions = []

        for app_name, models in DEFAULT_MODELS_PERMS.items():
            for model_name, group_perms in models.items():
                for group_id, perms in group_perms.items():
                    if not perms:
                        continue

                    for perm in perms:
                        if perm in permissions:
                            permission = permissions[perm]
                        else:
                            try:
                                permission = permissions[
                                    f"{app_name}.{perm}_{model_name}"
                                ]
                            except (ValueError, KeyError):
                                self.stderr.write(
                                    self.style.ERROR(
                                        f"Couldn't find permission {app_name}.{perm}_{model_name}"
                                    )
                                )
                                continue

                        group_permissions.append(
                            Group.permissions.through(
                                group=groups[group_id], permission=permission
                            )
                        )

        # Clean previous permissions
        Group.permissions.through.objects.all().delete()

        # Add new permissions
        Group.permissions.through.objects.bulk_create(group_permissions)

        self.stdout.write(
            self.style.SUCCESS(f"Permissions added ({len(group_permissions)})")
        )
        for group in Group.objects.all():
            self.stdout.write(f"{group.name}:")
            for perm in Group.permissions.through.objects.filter(
                group_id=group.id
            ).order_by("permission__codename"):
                self.stdout.write(f"- {perm.permission.codename}")
            self.stdout.write("\n")
