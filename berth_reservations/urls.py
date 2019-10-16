from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from helusers.admin_site import admin

from .schema import new_schema
from .views import SentryGraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(SentryGraphQLView.as_view(graphiql=True))),
    path(
        "graphql_v2/",
        csrf_exempt(SentryGraphQLView.as_view(schema=new_schema, graphiql=True)),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
