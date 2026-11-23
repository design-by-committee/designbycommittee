from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_GET
from django.views.static import serve


def is_indexable_host(request):
    """Only the live domain is indexed; staging (*.onrender.com) and local hosts are not."""
    return request.get_host().split(":")[0] in settings.INDEXABLE_HOSTS


@require_GET
def robots_txt(request):
    if is_indexable_host(request):
        lines = ["User-agent: *", "Disallow:", "", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    else:
        lines = ["User-agent: *", "Disallow: /"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


@require_GET
def media(request, path):
    """Serve uploaded images and documents from the media folder (the persistent disk on Render).

    Fine for this site's traffic. Wagtail gives every image rendition a unique file name, so they can be cached for
    a long time; move media to object storage behind a CDN if traffic grows.
    """
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    patch_cache_control(response, public=True, max_age=60 * 60 * 24 * 30)
    return response
