from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from ..models import CustomerProfile


class CustomerProfileLoader(DataLoader):
    def batch_load_fn(self, customer_ids):
        customers = defaultdict(CustomerProfile)

        for customer in CustomerProfile.objects.filter(id__in=customer_ids).iterator():
            customers[customer.id] = customer

        return Promise.resolve(
            [customers.get(customer_id) for customer_id in customer_ids]
        )
