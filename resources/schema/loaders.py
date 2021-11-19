from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from utils.dataloaders import model_loader

from ..models import Berth, BerthType, BoatType, Harbor, Pier, WinterStorageArea

BerthTypeLoader = model_loader(BerthType)
HarborLoader = model_loader(Harbor)
WSAreaLoader = model_loader(WinterStorageArea)


class PierLoader(DataLoader):
    def batch_load_fn(self, pier_ids):
        piers = defaultdict(Pier)

        for pier in (
            Pier.objects.filter(id__in=pier_ids)
            .prefetch_related("suitable_boat_types")
            .iterator()
        ):
            piers[pier.id] = pier

        return Promise.resolve([piers.get(pier_id) for pier_id in pier_ids])


class PiersForHarborLoader(DataLoader):
    def batch_load_fn(self, harbor_ids):
        piers_for_harbor = defaultdict(list)

        for pier in Pier.objects.filter(harbor_id__in=harbor_ids).iterator():
            piers_for_harbor[pier.harbor_id].append(pier)

        return Promise.resolve(
            [piers_for_harbor.get(harbor_id, []) for harbor_id in harbor_ids]
        )


class BerthLoader(DataLoader):
    def batch_load_fn(self, berth_ids):
        berths = defaultdict(Berth)

        for berth in (
            Berth.objects.filter(id__in=berth_ids)
            .select_related("berth_type")
            .iterator()
        ):
            berths[berth.id] = berth

        return Promise.resolve([berths.get(berth_id) for berth_id in berth_ids])


class SuitableBoatTypeLoader(DataLoader):
    def batch_load_fn(self, boat_type_ids):
        boat_types = defaultdict(BoatType)

        for boat_type in (
            BoatType.objects.filter(id__in=boat_type_ids)
            .prefetch_related("translations")
            .iterator()
        ):
            boat_types[boat_type.id] = boat_type

        return Promise.resolve(
            [boat_types.get(boat_type_id) for boat_type_id in boat_type_ids]
        )
