from rest_framework import mixins, permissions, renderers, serializers, viewsets

from harbors.models import BoatType, Harbor
from .models import HarborChoice, Reservation


class HarborChoiceSerializer(serializers.ModelSerializer):
    harbor = serializers.SlugRelatedField(
        queryset=Harbor.objects.all(),
        slug_field='identifier'
    )

    class Meta:
        model = HarborChoice
        fields = ('priority', 'harbor',)


class ReservationSerializer(serializers.ModelSerializer):
    chosen_harbors = HarborChoiceSerializer(source='harborchoice_set', many=True)
    boat_type = serializers.SlugRelatedField(
        queryset=BoatType.objects.all(),
        slug_field='identifier'
    )

    class Meta:
        model = Reservation
        fields = '__all__'

    def create(self, validated_data):
        # Django REST requires to explicitly write creation logic
        # for ManyToMany relations with a Through model.
        chosen_harbors = validated_data.pop('harborchoice_set')
        reservation = super().create(validated_data)
        if chosen_harbors:
            for choice in chosen_harbors:
                HarborChoice.objects.get_or_create(
                    harbor=choice["harbor"],
                    priority=choice["priority"],
                    reservation=reservation
                )
        return reservation


class ReservationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    renderer_classes = [renderers.JSONRenderer]
    permission_classes = [permissions.AllowAny]
    serializer_class = ReservationSerializer
    queryset = Reservation.objects.all()
