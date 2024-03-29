from django.conf import settings

from customers.schema import CustomerProfileLoader
from leases.schema import BerthLeaseForBerthLoader
from payments.schema.loaders import (
    BerthSwichOffersForLeasesLoader,
    OfferedBerthSwichOffersForBerthLoader,
)
from resources.schema import (
    BerthLoader,
    BerthTypeLoader,
    HarborLoader,
    PierLoader,
    PiersForHarborLoader,
    SuitableBoatTypeLoader,
    WSAreaLoader,
)

__all__ = ["HostFixupMiddleware", "GQLDataLoaders"]

LOADERS = {
    "leases_for_berth_loader": BerthLeaseForBerthLoader,
    "switch_offers_for_leases_loader": BerthSwichOffersForLeasesLoader,
    "piers_for_harbor_loader": PiersForHarborLoader,
    "offered_switch_offer_for_berth_loader": OfferedBerthSwichOffersForBerthLoader,
    "customer_loader": CustomerProfileLoader,
    "harbor_loader": HarborLoader,
    "ws_area_loader": WSAreaLoader,
    "pier_loader": PierLoader,
    "berth_loader": BerthLoader,
    "suitable_boat_type_loader": SuitableBoatTypeLoader,
    "berth_type_loader": BerthTypeLoader,
}


class HostFixupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Forces X_FORWARDED_HOST to a fixed value, for
        those nasty proxy setups there
        """
        request.META["HTTP_X_FORWARDED_HOST"] = settings.FORCED_HOST
        return self.get_response(request)


class GQLDataLoaders:
    def __init__(self):
        self.cached_loaders = {}

    def resolve(self, next, root, info, **kwargs):
        context = info.context

        for loader_name, loader_class in LOADERS.items():
            if loader_name not in self.cached_loaders:
                loader = loader_class()
                self.cached_loaders[loader_name] = loader
                setattr(context, loader_name, loader)

        return next(root, info, **kwargs)
