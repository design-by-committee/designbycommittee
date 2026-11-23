from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_safe
from django.views.static import serve

from core.cache import cache_publicly
from core.storage import is_hashed_rendition

ONE_YEAR = 60 * 60 * 24 * 365


def is_indexable_host(request):
    """Only the live domain is indexed; staging (*.onrender.com) and local hosts are not."""
    return request.get_host().split(":")[0] in settings.INDEXABLE_HOSTS


@require_safe
def robots_txt(request):
    if is_indexable_host(request):
        lines = ["User-agent: *", "Disallow:", "", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    else:
        lines = ["User-agent: *", "Disallow: /"]
    return cache_publicly(HttpResponse("\n".join(lines) + "\n", content_type="text/plain"))


@require_safe
def media(request, path):
    """Serve uploaded images and documents from the media folder (the persistent disk on Render).

    Image renditions have a content hash in their names (core/storage.py), so browsers and Render's edge cache can
    keep them for a year. Other files (originals, documents) can change under the same name: an hour at most.
    """
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    if is_hashed_rendition(path):
        patch_cache_control(response, public=True, max_age=ONE_YEAR, immutable=True)
    else:
        patch_cache_control(response, public=True, max_age=60 * 60)
    return response


def sitemap(request, *args, **kwargs):
    from wagtail.contrib.sitemaps.views import sitemap as wagtail_sitemap

    response = wagtail_sitemap(request, *args, **kwargs)
    response.render()
    return cache_publicly(response)
