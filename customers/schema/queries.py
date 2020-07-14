import graphene
from graphene_django.filter import DjangoFilterConnectionField

from applications.models import BerthApplication
from leases.models import BerthLease
from users.decorators import view_permission_required

from ..models import CustomerProfile
from .types import ProfileNode


class Query:
    berth_profile = graphene.relay.Node.Field(ProfileNode)
    berth_profiles = DjangoFilterConnectionField(ProfileNode)

    @view_permission_required(CustomerProfile, BerthApplication, BerthLease)
    def resolve_berth_profiles(self, info, **kwargs):
        return CustomerProfile.objects.all()
