import factory

from ..models import BerthReservation, WinterStorageReservation


class BerthReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BerthReservation


class WinterStorageReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WinterStorageReservation
