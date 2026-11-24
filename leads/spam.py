"""Quiet spam checks for the lead forms.

Nothing here is visible to visitors: a submission that looks like spam gets the same "thanks" response as any other,
but it's saved under Leads → Spam and no notification email goes out. Because suspected spam is kept, not deleted,
a real lead caught by mistake can be moved back by unticking "Spam" in the admin.

The hidden honeypot field (leads/forms.py) is separate: anything that fills it in is a bot for sure and is dropped.
"""

import hashlib
import hmac
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

# The form scripts send "fill-time": whole seconds from opening the page to sending the form.
FILL_TIME_FIELD = "fill-time"
MIN_FILL_SECONDS = 3

# At most this many submissions from one IP address per hour; any more are treated as spam.
RATE_LIMIT = 5
RATE_WINDOW = timedelta(hours=1)

# Free-text answers with HTML in them, or more than a couple of links, are almost always spam.
HTML_TAG = re.compile(r"<\s*/?\s*[a-z][^>]*>", re.IGNORECASE)
LINK = re.compile(r"https?://|www\.", re.IGNORECASE)
MAX_LINKS = 2


def spam_reasons(request, form):
    """Reasons `form` (validated) looks like spam; an empty list if it looks real."""
    reasons = []

    fill_time = request.POST.get(FILL_TIME_FIELD, "")
    if not fill_time.isdigit():
        reasons.append("sent without the page’s JavaScript")
    elif int(fill_time) < MIN_FILL_SECONDS:
        reasons.append(f"sent {fill_time}s after the page opened")

    for name, field in form.fields.items():
        value = form.cleaned_data.get(name)
        if not isinstance(value, str) or not value:
            continue
        if HTML_TAG.search(value):
            reasons.append(f"HTML in “{field.label}”")
        elif len(LINK.findall(value)) > MAX_LINKS:
            reasons.append(f"more than {MAX_LINKS} links in “{field.label}”")

    reasons += form.spam_reasons()

    ip_hash = hash_ip(client_ip(request))
    recent = request_count(ip_hash)
    if ip_hash and recent >= RATE_LIMIT:
        reasons.append(f"{recent + 1} submissions from one address within an hour")

    return reasons


def request_count(ip_hash):
    from .models import FormSubmission

    if not ip_hash:
        return 0
    since = timezone.now() - RATE_WINDOW
    return FormSubmission.objects.filter(ip_hash=ip_hash, submitted_at__gte=since).count()


def client_ip(request):
    """The visitor's IP address. Render's edge (Cloudflare) sets CF-Connecting-IP and overwrites any value a client
    sends; X-Forwarded-For and REMOTE_ADDR are fallbacks for other setups and local development."""
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return request.headers.get("CF-Connecting-IP") or forwarded or request.META.get("REMOTE_ADDR", "")


def hash_ip(ip):
    """A keyed hash of `ip`: enough to count submissions from one address without storing the address."""
    if not ip:
        return ""
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()
