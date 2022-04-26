from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from payments.models import BerthSwitchOffer


class BerthSwichOffersForLeasesLoader(DataLoader):
    def batch_load_fn(self, lease_ids):
        offers_by_leases = defaultdict(list)

        for offer in (
            BerthSwitchOffer.objects.filter(lease_id__in=lease_ids)
            .order_by("lease__start_date")
            .iterator()
        ):
            offers_by_leases[offer.lease_id].append(offer)

        return Promise.resolve(
            [offers_by_leases.get(lease_id, []) for lease_id in lease_ids]
        )
