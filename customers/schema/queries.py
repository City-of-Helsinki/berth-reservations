import graphene
import graphene_django_optimizer as gql_optimizer
from django.db.models import Case, Count, Q, When
from graphene_django.filter import DjangoFilterConnectionField

from applications.enums import ApplicationAreaType
from applications.models import BerthApplication
from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.models import BerthLease
from leases.schema import LeaseStatusEnum
from resources.schema import (
    BerthNode,
    HarborNode,
    PierNode,
    WinterStorageAreaNode,
    WinterStoragePlaceNode,
)
from users.decorators import view_permission_required

from ..models import CustomerProfile
from ..utils import from_global_ids
from .types import CustomerGroupEnum, InvoicingTypeEnum, ProfileFilterSet, ProfileNode

HELSINKI_PROFILES_FILTERS = ["first_name", "last_name", "email", "address", "sort_by"]


def _filter_winter_storage_leases(
    marked_winter_storage_areas, marked_winter_storage_places, qs
):
    qs = qs.filter(
        winter_storage_leases__isnull=False,
        winter_storage_leases__application__area_type=ApplicationAreaType.MARKED,
    )
    if marked_winter_storage_areas:
        marked_winter_storage_area_ids = from_global_ids(
            marked_winter_storage_areas, WinterStorageAreaNode
        )
        qs = qs.filter(
            Q(
                winter_storage_leases__place__winter_storage_section__area__id__in=marked_winter_storage_area_ids
            )
            | Q(
                winter_storage_leases__section__area__id__in=marked_winter_storage_area_ids
            )
        )
    if marked_winter_storage_places:
        marked_winter_storage_place_ids = from_global_ids(
            marked_winter_storage_places, WinterStoragePlaceNode
        )
        qs = qs.filter(
            winter_storage_leases__place__id__in=marked_winter_storage_place_ids
        )
    return qs


def _filter_unmarked_winter_storage_leases(qs, unmarked_winter_storage_areas):
    qs = qs.filter(
        winter_storage_leases__isnull=False,
        winter_storage_leases__application__area_type=ApplicationAreaType.UNMARKED,
    )
    if unmarked_winter_storage_areas:
        unmarked_winter_storage_area_ids = from_global_ids(
            unmarked_winter_storage_areas, WinterStorageAreaNode
        )
        qs = qs.filter(
            Q(
                winter_storage_leases__place__winter_storage_section__area__id__in=unmarked_winter_storage_area_ids
            )
            | Q(
                winter_storage_leases__section__area__id__in=unmarked_winter_storage_area_ids
            )
        )
    return qs


def _filter_berth_leases(berths, harbors, piers, qs):
    qs = qs.filter(berth_leases__isnull=False)
    if harbors:
        harbor_ids = from_global_ids(harbors, HarborNode)
        qs = qs.filter(berth_leases__berth__pier__harbor_id__in=harbor_ids)
    if piers:
        pier_ids = from_global_ids(piers, PierNode)
        qs = qs.filter(berth_leases__berth__pier__id__in=pier_ids)
    if berths:
        berth_ids = from_global_ids(berths, BerthNode)
        qs = qs.filter(berth_leases__berth_id__in=berth_ids)
    return qs


def _general_filters(params, qs):
    invoicing_types = params.pop("invoicing_types", [])
    customer_groups = params.pop("customer_groups", [])
    lease_statuses = params.pop("lease_statuses", [])
    lease_start = params.pop("lease_start", None)
    lease_end = params.pop("lease_end", None)
    lease_count = params.pop("lease_count", None)
    boat_types = params.pop("boat_types", [])
    boat_registration_number = params.pop("boat_registration_number", None)
    if invoicing_types:
        qs = qs.filter(invoicing_type__in=invoicing_types)
    if customer_groups:
        qs = qs.filter(customer_group__in=customer_groups)
    if boat_types:
        qs = qs.filter(boats__boat_type__in=boat_types)
    if lease_count:
        qs = qs.annotate(
            sum_leases=Count("berth_leases") + Count("winter_storage_leases")
        ).filter(sum_leases__gt=1)
    if boat_registration_number:
        qs = qs.filter(boats__registration_number__icontains=boat_registration_number)
    if lease_start:
        qs = qs.filter(
            Q(berth_leases__start_date__gte=lease_start)
            | Q(winter_storage_leases__start_date__gte=lease_start)
        )
    if lease_end:
        qs = qs.filter(
            Q(berth_leases__end_date__lte=lease_end)
            | Q(winter_storage_leases__end_date__lte=lease_end)
        )
    if lease_statuses:
        qs = qs.filter(
            Q(berth_leases__status__in=lease_statuses)
            | Q(winter_storage_leases__status__in=lease_statuses)
        )
    return qs


def _get_ids_from_profile_service(kwargs, profile_token):
    params = {
        "first_name": kwargs.pop("first_name", ""),
        "last_name": kwargs.pop("last_name", ""),
        "email": kwargs.pop("email", ""),
        "address": kwargs.pop("address", ""),
        "order_by": kwargs.pop("sort_by", ""),
        "first": kwargs.pop("first", None),
    }
    from customers.services import ProfileService

    profile_service = ProfileService(profile_token=profile_token)
    users = profile_service.find_profile(**params, force_only_one=False)
    return [user.id for user in users]


class Query:
    berth_profile = graphene.relay.Node.Field(ProfileNode)
    berth_profiles = DjangoFilterConnectionField(
        ProfileNode,
        filterset_class=ProfileFilterSet,
        invoicing_types=graphene.List(InvoicingTypeEnum),
        customer_groups=graphene.List(CustomerGroupEnum),
        lease_start=graphene.Date(),
        lease_end=graphene.Date(),
        lease_statuses=graphene.List(LeaseStatusEnum),
        boat_types=graphene.List(graphene.ID),
        boat_registration_number=graphene.String(),
        lease_count=graphene.Boolean(),
        berth_lease_customer=graphene.Boolean(),
        harbors=graphene.List(graphene.String),
        piers=graphene.List(graphene.String),
        berths=graphene.List(graphene.String),
        marked_winter_storage_lease_customer=graphene.Boolean(),
        marked_winter_storage_areas=graphene.List(graphene.String),
        marked_winter_storage_places=graphene.List(graphene.String),
        unmarked_winter_storage_lease_customer=graphene.Boolean(),
        unmarked_winter_storage_areas=graphene.List(graphene.String),
        sticker_number=graphene.String(),
        first_name=graphene.String(
            description="Filter by Helsinki Profile `first_name` field"
        ),
        last_name=graphene.String(
            description="Filter by Helsinki Profile `last_name` field"
        ),
        email=graphene.String(description="Filter by Helsinki Profile `email` field"),
        address=graphene.String(
            description="Filter by Helsinki Profile `address_Address` field"
        ),
        sort_by=graphene.String(description="Order by Helsinki Profile fields"),
        api_token=graphene.String(
            description="API Token is required when using Helsinki Profile filters"
        ),
        description=""" The `invoicingTypes` filter takes a list of `InvoicingType` values
         representing the desired invoicing types of the customers. If an empty list is
         passed, no filter will be applied and all the results will be returned.
        \n\nThe `customerGroups` filter takes a list of `CustomerGroup` values
         representing the desired groups of the customers. If an empty list is passed,
         no filter will be applied and all the results will be returned.
        \n\n When there is any HKI profiles filters (defined in `HELSINKI_PROFILES_FILTERS`) used in the query,
         the API will ask for `apiToken`. Otherwise `apiToken` is not needed
        \n\nThe `leaseStatus` filter take a list of `LeaseStatus` values representing the desired status of the lease
        \n\n**Requires permissions** to access customer profiles.
        \n\nErrors:
        \n* A value passed is not a valid invoicing type
        \n* A value passed is not a valid customer group
        \n* Cannot filter by Helsinki Profile fields without API Token,
        """,
    )

    @view_permission_required(CustomerProfile, BerthApplication, BerthLease)
    def resolve_berth_profiles(self, info, **kwargs):
        berth_lease_customer = kwargs.pop("berth_lease_customer", False)
        harbors = kwargs.pop("harbors", [])
        piers = kwargs.pop("piers", [])
        berths = kwargs.pop("berths", [])

        marked_winter_storage_lease_customer = kwargs.pop(
            "marked_winter_storage_lease_customer", False
        )
        marked_winter_storage_areas = kwargs.pop("marked_winter_storage_areas", [])
        marked_winter_storage_places = kwargs.pop("marked_winter_storage_places", [])

        unmarked_winter_storage_lease_customer = kwargs.pop(
            "unmarked_winter_storage_lease_customer", False
        )
        unmarked_winter_storage_areas = kwargs.pop("unmarked_winter_storage_areas", [])
        sticker_number = kwargs.pop("sticker_number", None)

        qs = CustomerProfile.objects

        # Check if Helsinki Profiles filters are used in the query, if yes, query the
        # profile ids first from there
        if not set(kwargs.keys()).isdisjoint(set(HELSINKI_PROFILES_FILTERS)):
            profile_token = kwargs.pop("api_token", None)
            if not profile_token:
                raise VenepaikkaGraphQLError(
                    "Cannot filter by Helsinki Profile fields without API Token"
                )
            ids = _get_ids_from_profile_service(kwargs, profile_token)
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
            qs = qs.filter(id__in=ids).order_by(preserved)

        # General filters
        qs = _general_filters(kwargs, qs)

        # Berth leases filter
        if berth_lease_customer:
            qs = _filter_berth_leases(berths, harbors, piers, qs)

        # Marked WS leases filter
        if marked_winter_storage_lease_customer:
            qs = _filter_winter_storage_leases(
                marked_winter_storage_areas, marked_winter_storage_places, qs
            )

        # Unmarked WS leases filter
        if unmarked_winter_storage_lease_customer:
            qs = _filter_unmarked_winter_storage_leases(
                qs, unmarked_winter_storage_areas
            )
        if sticker_number:
            qs = qs.filter(winter_storage_leases__sticker_number=sticker_number)

        return gql_optimizer.query(qs, info)
