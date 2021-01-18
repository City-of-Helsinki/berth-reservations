from django.db.models import Count, Prefetch, Q
from django.utils.translation import gettext_lazy as _

from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from users.utils import user_has_view_permission
from utils.relay import get_node_from_global_id

from ..models import Berth, BerthType, Pier


def resolve_piers(info, **kwargs):
    min_width = kwargs.get("min_berth_width", 0)
    min_length = kwargs.get("min_berth_length", 0)
    application_global_id = kwargs.get("for_application")
    harbor_id = kwargs.get("harbor_id")

    # Filter out piers with no berths that fit the
    # passed dimensions only if the dimensions were given.
    # Otherwise, return the whole list of piers.
    has_dimensions_filter = any(
        ["min_berth_width" in kwargs, "min_berth_length" in kwargs]
    )

    if has_dimensions_filter and application_global_id:
        raise VenepaikkaGraphQLError(
            _(
                "You cannot filter by dimension (width, length) and application a the same time."
            )
        )

    if application_global_id:
        user = info.context.user
        if (
            user
            and user.is_authenticated
            and user_has_view_permission(user, BerthApplication)
        ):
            application = get_node_from_global_id(
                info, application_global_id, only_type=BerthApplicationNode
            )

            min_width = application.boat_width
            min_length = application.boat_length
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action")
            )

    if harbor_id:
        query = Pier.objects.filter(harbor_id=harbor_id)
    else:
        query = Pier.objects.all()

    suitable_berth_types = BerthType.objects.filter(
        width__gte=min_width, length__gte=min_length
    )
    berth_queryset = Berth.objects.select_related("berth_type").filter(
        berth_type__in=suitable_berth_types
    )

    query = query.prefetch_related(
        Prefetch("berths", queryset=berth_queryset),
        "suitable_boat_types",
        "harbor__translations",
        "harbor__availability_level__translations",
        "harbor__municipality__translations",
    ).select_related("harbor", "harbor__availability_level", "harbor__municipality")

    if has_dimensions_filter:
        query = query.annotate(
            berth_count=Count(
                "berths",
                filter=Q(berths__berth_type__width__gte=min_width)
                & Q(berths__berth_type__length__gte=min_length),
            )
        ).filter(berth_count__gt=0)

    return query
