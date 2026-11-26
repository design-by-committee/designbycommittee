"""IndexNow (https://www.indexnow.org/): tell search engines straight away when a page is added, changed or removed.

One submission to api.indexnow.org is shared with every participating engine (Bing, and through it ChatGPT search;
Yandex, Seznam, Naver, Yep, Amazon). Google doesn't take part; it relies on the sitemap.

Adapted from wagtail-indexnow (https://github.com/RealOrangeOne/wagtail-indexnow, BSD-3-Clause), which this site
doesn't use as-is because:

- its key has `_` and `=` in it, which IndexNow doesn't allow, and its key file doesn't contain the key it submits,
  so the engines can't verify the site;
- it only pings from the admin's edit and create views, not the `cms` command, scheduled publishing, bulk actions or
  workflow approvals, and never for unpublished, deleted, moved or renamed pages;
- it pings inside the editor's request with no timeout and raises on any error, so a slow or failing IndexNow
  turns a successful publish into an error page;
- it pings from every environment, for every host and for pages hidden from search engines.

How it works here:

- The key is INDEXNOW_KEY or, without it, derived from SECRET_KEY. It is served at /<key>.txt (key_file below).
- Publishing, unpublishing, deleting, moving and renaming pages queue their URLs once the transaction commits (so the
  `cms` command's dry runs submit nothing). Only pages search engines may index count, on INDEXABLE_HOSTS.
- Queued URLs are sent in one request a few seconds later from a background thread, which also gives the edge cache
  purge (core/cache.py) time to finish, so crawlers get the new version. Failures are logged, never raised.
- The same URL isn't submitted again within RESUBMIT_SECONDS, as IndexNow asks.
- Only on when INDEXNOW_ENABLED is set (production settings), so local development and tests never submit.
"""

import copy
import hashlib
import hmac
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from urllib.parse import urlsplit

from django.conf import settings
from django.core import checks
from django.db import transaction
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_safe

from core.cache import cache_publicly

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_PATTERN = re.compile(r"^[a-zA-Z0-9-]{8,128}$")
BATCH_SECONDS = 5
RESUBMIT_SECONDS = 5 * 60
MAX_URLS_PER_REQUEST = 10_000


def get_key():
    """INDEXNOW_KEY, or a stable 32-character hex key derived from SECRET_KEY (one-way, so it reveals nothing)."""
    if getattr(settings, "INDEXNOW_KEY", ""):
        return settings.INDEXNOW_KEY
    return hmac.new(settings.SECRET_KEY.encode(), b"indexnow", hashlib.sha256).hexdigest()[:32]


def enabled():
    return bool(getattr(settings, "INDEXNOW_ENABLED", False))


@checks.register()
def check_key(app_configs, **kwargs):
    key = getattr(settings, "INDEXNOW_KEY", "")
    if key and not KEY_PATTERN.match(key):
        return [checks.Error("INDEXNOW_KEY must be 8 to 128 characters: letters, digits and dashes.", id="core.E001")]
    return []


@require_safe
def key_file(request, key):
    """/<key>.txt, which search engines fetch to check that the site sent the submissions."""
    if not constant_time_compare(key, get_key()):
        raise Http404
    return cache_publicly(HttpResponse(key, content_type="text/plain; charset=utf-8"))


# Which URLs to submit ----------------------------------------------------------------------------------------------


def indexable(page):
    return page.specific.is_indexable() if hasattr(page.specific, "is_indexable") else page.live


def hidden_from_search(page):
    """Hidden from search engines (noindex or password-protected), whether or not it's live."""
    page = page.specific
    return getattr(page, "noindex", False) or page.get_view_restrictions().exists()


def full_url(page, url_path=None):
    """The page's full URL, or the one it had at `url_path` (before a move or slug change)."""
    if url_path is not None:
        page = copy.copy(page)
        page.url_path = url_path
    return page.get_full_url()


def on_published(sender, instance, **kwargs):
    if instance.go_live_at and instance.go_live_at > timezone.now():
        return  # scheduled: submitted when it actually goes live
    if indexable(instance):
        submit_on_commit([full_url(instance)])


def on_unpublished(sender, instance, **kwargs):
    # Now a 404, which IndexNow wants to hear about so the page drops out of results
    if not hidden_from_search(instance):
        submit_on_commit([full_url(instance)])


def on_slug_changed(sender, instance, instance_before, **kwargs):
    # The new URL is submitted by on_published; the old one now redirects (Wagtail creates the redirect)
    if instance.live and not hidden_from_search(instance):
        submit_on_commit([full_url(instance_before)])


def on_moved(sender, instance, url_path_before, url_path_after, **kwargs):
    if url_path_before == url_path_after:
        return  # reordered among its siblings
    pages = [instance, *instance.get_descendants().live().specific()]
    urls = []
    for page in pages:
        if page.live and not hidden_from_search(page):
            old_path = url_path_before + page.url_path.removeprefix(url_path_after)
            urls += [full_url(page, old_path), full_url(page)]
    submit_on_commit(urls)


def on_deleted(sender, instance, **kwargs):
    from wagtail.models import Page

    # Deleting a page deletes a row per model it inherits from; the base Page row is the one seen exactly once
    if type(instance) is Page and instance.live and not hidden_from_search(instance):
        submit_on_commit([full_url(instance)])


def connect_signals():
    from django.db.models.signals import pre_delete
    from wagtail.signals import page_published, page_slug_changed, page_unpublished, post_page_move

    page_published.connect(on_published, dispatch_uid="indexnow-published")
    page_unpublished.connect(on_unpublished, dispatch_uid="indexnow-unpublished")
    page_slug_changed.connect(on_slug_changed, dispatch_uid="indexnow-slug-changed")
    post_page_move.connect(on_moved, dispatch_uid="indexnow-moved")
    pre_delete.connect(on_deleted, dispatch_uid="indexnow-deleted")


# Sending -----------------------------------------------------------------------------------------------------------

_outbox = set()
_last_submitted = {}  # URL -> time.monotonic() of its last submission
_lock = threading.Lock()
_timer = {"running": False}


def submit_on_commit(urls):
    """Queue `urls` for submission once the current transaction commits. Nothing is sent if it rolls back."""
    hosts = set(settings.INDEXABLE_HOSTS)
    urls = [url for url in urls if url and urlsplit(url).hostname in hosts]
    if enabled() and urls:
        transaction.on_commit(lambda: _queue(urls))


def _queue(urls):
    with _lock:
        _outbox.update(urls)
        start = not _timer["running"]
        _timer["running"] = True
    if start:
        timer = threading.Timer(BATCH_SECONDS, _flush)
        timer.daemon = True
        timer.start()


def _flush():
    now = time.monotonic()
    with _lock:
        urls = sorted(url for url in _outbox if now - _last_submitted.get(url, float("-inf")) >= RESUBMIT_SECONDS)
        _outbox.clear()
        _timer["running"] = False
        for url in urls:
            _last_submitted[url] = now
    by_host = defaultdict(list)
    for url in urls:
        by_host[urlsplit(url).hostname].append(url)
    for host, host_urls in by_host.items():
        for start in range(0, len(host_urls), MAX_URLS_PER_REQUEST):
            submit(host, host_urls[start : start + MAX_URLS_PER_REQUEST])


def submit(host, urls):
    """Send `urls` (all on `host`) to IndexNow. Returns True if it accepted them."""
    body = json.dumps({"host": host, "key": get_key(), "urlList": urls}).encode()
    request = urllib.request.Request(
        ENDPOINT, data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed https URL)
            # 200: accepted. 202: accepted, key check pending (usual for the first submission).
            logger.info("IndexNow: submitted %s (HTTP %s)", ", ".join(urls), response.status)
            return True
    except urllib.error.HTTPError as error:
        # 400 bad request, 403 key not valid, 422 URLs not on the host or key mismatch, 429 too many requests
        detail = error.read(300).decode("utf-8", "replace")
        logger.warning("IndexNow: submitting %s failed: HTTP %s %s", ", ".join(urls), error.code, detail)
    except OSError as error:
        logger.warning("IndexNow: submitting %s failed: %s", ", ".join(urls), error)
    return False
