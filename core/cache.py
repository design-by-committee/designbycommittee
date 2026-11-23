"""HTTP caching: which responses Render's edge cache (Cloudflare) may store, and purging it when content changes.

The strategy, also described in the README:

- Static files (WhiteNoise) and image renditions have content hashes in their names and are cached for a year.
- Public pages are cached at the edge for EDGE_HTML_MAX_AGE seconds, but browsers revalidate on every visit
  (max-age=0), so a purged edge is picked up straight away. ETags make those revalidations cheap.
- When content that appears on pages changes (publishing, testimonials, settings, images, redirects), the whole edge
  cache is purged through Render's API, if RENDER_API_KEY is set. Without the key, pages are cached for a few minutes
  so edits still show up quickly. Every deploy purges the edge cache too.
- Anything not marked public is sent as private: admin, previews, form responses, logged-in visitors, URLs with a
  query string (e.g. ?sent= after a form), and password-protected pages.
"""

import json
import logging
import threading
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.db import transaction
from django.utils.cache import patch_cache_control

logger = logging.getLogger(__name__)

PRIVATE = "private, no-cache"


def edge_purge_enabled():
    return bool(getattr(settings, "RENDER_API_KEY", "") and getattr(settings, "RENDER_SERVICE_ID", ""))


def edge_html_max_age():
    if getattr(settings, "EDGE_HTML_MAX_AGE", None) is not None:
        return settings.EDGE_HTML_MAX_AGE
    # With purging, pages can stay cached until something changes; without it, keep edits visible within minutes.
    return 60 * 60 * 24 if edge_purge_enabled() else 60 * 5


def is_public_request(request):
    """A plain GET by an anonymous visitor, whose response is the same for everyone."""
    return (
        request.method in ("GET", "HEAD")
        and not request.GET
        and settings.SESSION_COOKIE_NAME not in request.COOKIES
        and not getattr(request, "is_preview", False)
    )


def cache_publicly(response, max_age=None):
    """Let the edge cache keep `response`; browsers always revalidate it."""
    max_age = edge_html_max_age() if max_age is None else max_age
    if response.status_code != 200 or response.has_header("Set-Cookie") or response.cookies:
        return cache_privately(response)
    patch_cache_control(response, public=True, max_age=0, s_maxage=max_age, stale_while_revalidate=60)
    return response


def cache_privately(response):
    response.headers.pop("Cache-Control", None)
    response["Cache-Control"] = PRIVATE
    return response


# Purging -----------------------------------------------------------------------------------------------------------

# One save can fire several signals (a page publish, its revision, a moved child page...): purge once for all of them.
PURGE_DEBOUNCE_SECONDS = 5
_last_purge = {"at": float("-inf")}
_lock = threading.Lock()


def purge_edge_cache_on_commit():
    """Purge Render's edge cache once the current transaction commits.

    Nothing is purged if the transaction rolls back, so a dry run of the `cms` command never purges.
    """
    if edge_purge_enabled():
        transaction.on_commit(_start_purge)


def _start_purge():
    with _lock:
        now = time.monotonic()
        if now - _last_purge["at"] < PURGE_DEBOUNCE_SECONDS:
            return
        _last_purge["at"] = now
    threading.Thread(target=purge_edge_cache, name="edge-cache-purge", daemon=True).start()


def purge_edge_cache():
    """Ask Render to purge the web service's whole edge cache (https://api-docs.render.com/reference/purge-cache)."""
    url = f"https://api.render.com/v1/services/{settings.RENDER_SERVICE_ID}/cache/purge"
    request = urllib.request.Request(
        url, method="POST", headers={"Authorization": f"Bearer {settings.RENDER_API_KEY}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed https URL)
            logger.info("Edge cache purge requested (HTTP %s)", response.status)
            return True
    except urllib.error.HTTPError as error:
        detail = error.read(300).decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except (ValueError, AttributeError):
            pass
        logger.warning("Edge cache purge failed: HTTP %s %s", error.code, detail)
    except OSError as error:
        logger.warning("Edge cache purge failed: %s", error)
    return False
