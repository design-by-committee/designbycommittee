from django.conf import settings
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail import views as wagtail_views
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from core.indexnow import key_file as indexnow_key_file
from core.views import llms_txt, media, robots_txt, security_txt, sitemap


urlpatterns = [
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("sitemap.xml", sitemap),
    path("robots.txt", robots_txt),
    path("llms.txt", llms_txt),
    path(".well-known/security.txt", security_txt),
    # IndexNow key file (core/indexnow.py); any other /<name>.txt is a 404
    path("<str:key>.txt", indexnow_key_file),
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
    # Pages are served without Django's CSRF cookie, so the edge can cache them (core/cache.py). The only thing that
    # posts to a page is a lead form, which checks the request's Origin instead (leads/views.py).
    re_path(wagtail_urls.serve_pattern, csrf_exempt(wagtail_views.serve), name="wagtail_serve"),
    path("", include(wagtail_urls)),
]
