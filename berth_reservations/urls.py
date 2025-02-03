from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from helusers.admin_site import admin

from contracts.services import get_contract_service
from payments import urls as payment_urls
from payments.models import Order

from .views import SentryGraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(SentryGraphQLView.as_view(graphiql=True))),
    path("payments/", include(payment_urls)),
    path("exports/", include("exports.urls")),
    path("gdpr-api/", include("helsinki_gdpr.urls")),
]

if settings.ENABLE_PROFILING_TOOLS:
    urlpatterns += [re_path(r"^silk/", include("silk.urls", namespace="silk"))]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#
# Kubernetes liveness & readiness probes
#
def healthz(*args, **kwargs):
    return HttpResponse(status=200)


def readiness(*args, **kwargs):
    return HttpResponse(status=200)


urlpatterns += [
    path("healthz", healthz),
    path("readiness", readiness),
]


#
# Contracts integration: endpoint for downloading documents
#
def download_contract_document(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number)
    except Order.DoesNotExist:
        return HttpResponse(status=404)

    document = get_contract_service().get_document(order.lease.contract)

    return HttpResponse(document, content_type="application/pdf")


urlpatterns += [
    path("contract_document/<str:order_number>", download_contract_document)
]
