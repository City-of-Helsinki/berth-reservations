from rest_framework import mixins, permissions, renderers, serializers, viewsets

from harbors.models import BoatType, Harbor

from .models import BerthReservation, HarborChoice
from .signals import reservation_saved


class HarborChoiceSerializer(serializers.ModelSerializer):
    harbor = serializers.SlugRelatedField(
        queryset=Harbor.objects.all(), slug_field="identifier"
    )

    class Meta:
        model = HarborChoice
        fields = ("priority", "harbor")


class ReservationSerializer(serializers.ModelSerializer):
    chosen_harbors = HarborChoiceSerializer(source="harborchoice_set", many=True)
    boat_type = serializers.SlugRelatedField(
        queryset=BoatType.objects.all(), slug_field="identifier"
    )

    boat_length = serializers.DecimalField(
        decimal_places=2, max_digits=5, localize=True, required=False
    )
    boat_width = serializers.DecimalField(
        decimal_places=2, max_digits=5, localize=True, required=False
    )
    boat_draught = serializers.DecimalField(
        decimal_places=2, max_digits=5, localize=True, required=False
    )
    boat_weight = serializers.DecimalField(
        decimal_places=2, max_digits=10, localize=True, required=False
    )

    class Meta:
        model = BerthReservation
        fields = "__all__"

    def create(self, validated_data):
        # Django REST requires to explicitly write creation logic
        # for ManyToMany relations with a Through model.
        chosen_harbors = validated_data.pop("harborchoice_set")
        reservation = super().create(validated_data)
        if chosen_harbors:
            for choice in chosen_harbors:
                HarborChoice.objects.get_or_create(
                    harbor=choice["harbor"],
                    priority=choice["priority"],
                    reservation=reservation,
                )
        # Send notifications when all m2m relations are saved
        reservation_saved.send(sender=self.__class__, reservation=reservation)
        return reservation


class ReservationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    renderer_classes = [renderers.JSONRenderer]
    permission_classes = [permissions.AllowAny]
    serializer_class = ReservationSerializer
    queryset = BerthReservation.objects.all()
