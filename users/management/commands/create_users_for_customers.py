from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from customers.models import CustomerProfile
from users.utils import get_berth_customers_group

User = get_user_model()


class Command(BaseCommand):
    help = "Create django users for existing customers"

    def handle(self, *args, **kwargs):
        berth_customer_group = get_berth_customers_group()

        created = 0
        customers = CustomerProfile.objects.filter(user__isnull=True)

        count = customers.count()
        self.stdout.write("Creating users for profiles")
        self.stdout.write(f"{count} profiles pending")

        batch_users = []
        batch_customers = []

        for customer in customers:
            customer.user = User.objects.create()
            batch_customers.append(customer)
            batch_users.append(customer.user)
            created += 1

        CustomerProfile.objects.bulk_update(batch_customers, ["user"])
        berth_customer_group.user_set.add(*batch_users)

        self.stdout.write(self.style.SUCCESS(f"Created {created} users"))
