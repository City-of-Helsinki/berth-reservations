from rest_framework import mixins, permissions, renderers, serializers, viewsets

from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = '__all__'


class ReservationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    renderer_classes = [renderers.JSONRenderer]
    permission_classes = [permissions.AllowAny]
    serializer_class = ReservationSerializer
    queryset = Reservation.objects.all()
