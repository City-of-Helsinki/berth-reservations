from collections import defaultdict
from datetime import date

from promise import Promise
from promise.dataloader import DataLoader

from payments.enums import OfferStatus
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


class OfferedBerthSwichOffersForBerthLoader(DataLoader):
    def batch_load_fn(self, berth_ids):

        offers_by_berths = {
            offer.berth.id: offer
            for offer in BerthSwitchOffer.objects.filter(
                berth_id__in=berth_ids,
                status=OfferStatus.OFFERED,
                due_date__gte=date.today(),
            ).order_by("due_date")
        }

        return Promise.resolve(
            [offers_by_berths.get(berth_id, None) for berth_id in berth_ids]
        )
