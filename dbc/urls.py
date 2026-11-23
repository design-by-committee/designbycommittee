from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from core.views import media, robots_txt


def healthz(request):
    """Render's health check: answers without touching the database or Wagtail's page tree."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("sitemap.xml", sitemap),
    path("robots.txt", robots_txt),
    # Old static-site address of the home page
    path("index.html", RedirectView.as_view(url="/", permanent=True)),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [re_path(r"^media/(?P<path>.+)$", media)]

urlpatterns += [
    # Everything else is a Wagtail page. Keep this last.
    path("", include(wagtail_urls)),
]
