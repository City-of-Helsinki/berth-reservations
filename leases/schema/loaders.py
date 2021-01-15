from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from ..models import BerthLease


class BerthLeaseForBerthLoader(DataLoader):
    def batch_load_fn(self, berth_ids):
        leases_by_berth_id = defaultdict(list)

        for lease in BerthLease.objects.filter(berth_id__in=berth_ids).iterator():
            leases_by_berth_id[lease.berth_id].append(lease)

        return Promise.resolve(
            [leases_by_berth_id.get(berth_id, []) for berth_id in berth_ids]
        )
