from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.urls import re_path
from django.views import defaults as default_views
from django.views.static import serve

from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView

from core.health import HealthCheckView
from core.views import home_view

urlpatterns = [
    # Health check (no auth required)
    path("health/", HealthCheckView.as_view(), name="health"),
    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),
    # Dashboard
    path("", home_view, name="home"),
    # Account (login/logout/invitation acceptance)
    path("account/", include("core.account_urls", namespace="account")),
    # REST API (DRF router + JWT + OpenAPI)
    path("api/v1/", include("config.api_urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Media files (served by Django in dev)
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

admin.site.site_header = "Gold7 Administration"
admin.site.site_title = "Gold7 Admin"
admin.site.site_url = "/"

# Custom error handlers
handler403 = "core.views.permission_denied_view"

if settings.DEBUG:
    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
