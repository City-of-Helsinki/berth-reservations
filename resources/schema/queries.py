import graphene
from django.db.models import Prefetch
from graphene import relay
from graphene_django.fields import DjangoConnectionField, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField

from ..models import (
    AvailabilityLevel,
    Berth,
    BoatType,
    Harbor,
    Pier,
    WinterStorageArea,
    WinterStoragePlace,
    WinterStorageSection,
)
from .types import (
    AvailabilityLevelType,
    BerthNode,
    BoatTypeType,
    HarborNode,
    PierNode,
    WinterStorageAreaNode,
    WinterStoragePlaceNode,
    WinterStoragePlaceTypeNode,
    WinterStorageSectionNode,
)
from .utils import resolve_piers


class Query:
    availability_levels = DjangoListField(AvailabilityLevelType)
    boat_types = DjangoListField(BoatTypeType)

    berth = relay.Node.Field(BerthNode)
    berths = DjangoFilterConnectionField(
        BerthNode,
        description="**Requires permissions** to query `leases` field. "
        "Otherwise, everything is available",
    )

    pier = relay.Node.Field(PierNode)
    piers = DjangoFilterConnectionField(
        PierNode,
        min_berth_width=graphene.Float(),
        min_berth_length=graphene.Float(),
        for_application=graphene.ID(),
        description="`Piers` allows to filter, among other fields, by `minBerthWidth` and `minBerthLength`.\n\n"
        "This filter is recommended over the filter in `berths`, because it yields better results. "
        "It will only return the `pier`s which contain `berth`s matching the filter, when the other will "
        "return all the available `pier`s with an empty list of `berth`s in case there's no matches.\n\n"
        "If you use both filters in the same query, you might get some empty `berth` results where both "
        "queries overlap.\n\n"
        "To filter the piers suitable for an application, you can use the `forApplication` argument. "
        "**Requires permissions** to access applications."
        "\n\nErrors:"
        "\n* Filter `forApplication` with a user without enough permissions"
        "\n * Filter `forApplication` combined with either dimension (width, length) filter",
    )

    harbor = relay.Node.Field(HarborNode)
    harbor_by_servicemap_id = graphene.Field(
        HarborNode, servicemap_id=graphene.String(required=True)
    )
    harbors = DjangoFilterConnectionField(
        HarborNode, servicemap_ids=graphene.List(graphene.String)
    )

    winter_storage_place = relay.Node.Field(WinterStoragePlaceNode)
    winter_storage_places = DjangoConnectionField(WinterStoragePlaceNode)

    winter_storage_place_type = relay.Node.Field(WinterStoragePlaceTypeNode)
    winter_storage_place_types = DjangoConnectionField(WinterStoragePlaceTypeNode)

    winter_storage_section = relay.Node.Field(WinterStorageSectionNode)
    winter_storage_sections = DjangoFilterConnectionField(WinterStorageSectionNode)

    winter_storage_area = relay.Node.Field(WinterStorageAreaNode)
    winter_storage_areas = DjangoFilterConnectionField(WinterStorageAreaNode)

    def resolve_availability_levels(self, info, **kwargs):
        return AvailabilityLevel.objects.all()

    def resolve_boat_types(self, info, **kwargs):
        return BoatType.objects.all()

    def resolve_berths(self, info, **kwargs):
        return Berth.objects.prefetch_related(
            "pier__suitable_boat_types",
            "pier__harbor__translations",
            "pier__harbor__availability_level__translations",
            "pier__harbor__municipality__translations",
        ).select_related(
            "pier",
            "pier__harbor",
            "pier__harbor__availability_level",
            "pier__harbor__municipality",
        )

    def resolve_piers(self, info, **kwargs):
        return resolve_piers(info, **kwargs)

    def resolve_harbor_by_servicemap_id(self, info, **kwargs):
        return Harbor.objects.filter(servicemap_id=kwargs.get("servicemap_id")).first()

    def resolve_harbors(self, info, **kwargs):
        # TODO: optimize this further
        # currently, still results in too many DB queries
        # although, django-graphene might introduce fixes for this
        # so, check the state of this against a newer version later

        servicemap_ids = kwargs.get("servicemap_ids", None)
        qs = (
            Harbor.objects.filter(servicemap_id__in=servicemap_ids)
            if servicemap_ids
            else Harbor.objects.all()
        )
        return qs.prefetch_related(
            "translations",
            Prefetch(
                "piers",
                queryset=Pier.objects.prefetch_related(
                    Prefetch("berths", queryset=Berth.objects.all())
                ),
            ),
            "piers__suitable_boat_types",
        ).select_related("availability_level", "municipality")

    def resolve_winter_storage_places(self, info, **kwargs):
        return WinterStoragePlace.objects.prefetch_related(
            "winter_storage_section__area__translations",
            "winter_storage_section__area__availability_level__translations",
            "winter_storage_section__area__municipality__translations",
        ).select_related(
            "winter_storage_section",
            "winter_storage_section__area",
            "winter_storage_section__area__availability_level",
            "winter_storage_section__area__municipality",
        )

    def resolve_winter_storage_sections(self, info, **kwargs):
        return WinterStorageSection.objects.prefetch_related(
            "places",
            "area__translations",
            "area__availability_level__translations",
            "area__municipality__translations",
        ).select_related("area", "area__availability_level", "area__municipality")

    def resolve_winter_storage_areas(self, info, **kwargs):
        # TODO: optimize this further
        # currently, still results in too many DB queries
        # although, django-graphene might introduce fixes for this
        # so, check the state of this against a newer version later

        return WinterStorageArea.objects.prefetch_related(
            "translations",
            Prefetch(
                "sections",
                queryset=WinterStorageSection.objects.prefetch_related(
                    Prefetch("places", queryset=WinterStoragePlace.objects.all())
                ),
            ),
        ).select_related("availability_level", "municipality")
