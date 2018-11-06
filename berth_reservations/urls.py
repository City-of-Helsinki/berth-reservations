from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from harbors.api import BoatTypeViewSet, HarborViewSet
from reservations.api import ReservationViewSet


router = routers.DefaultRouter()
router.register('boat-types', BoatTypeViewSet)
router.register('harbors', HarborViewSet)
router.register('reservations', ReservationViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/', include(router.urls)),
    path('docs/', include_docs_urls(title='Berth reservations')),
]
