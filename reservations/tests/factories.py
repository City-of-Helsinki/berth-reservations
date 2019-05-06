import factory

from ..models import BerthReservation


class BerthReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BerthReservation
