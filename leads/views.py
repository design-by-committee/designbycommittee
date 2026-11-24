import logging
import threading
from email.utils import formataddr
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.urls import reverse

from core.models import SiteSettings

from .forms import FORMS
from .models import FormSubmission
from .spam import client_ip, hash_ip, spam_reasons

logger = logging.getLogger(__name__)


def handle_submission(request, page):
    """Validate and store a lead form posted to `page`, then email a notification.

    The page's JavaScript posts with `Accept: application/json` and gets JSON back. Without JavaScript, the browser
    is redirected back to the page with ?sent=<form-name> (or ?error=<form-name>) so the template can show the result.
    """
    form_name = request.POST.get("form-name", "")
    if form_name not in FORMS or form_name not in page.form_names():
        return HttpResponseBadRequest("Unknown form")
    if not is_same_origin(request):
        logger.warning("Rejected a %s submission from another site (Origin %r)", form_name, request.headers.get("Origin"))
        return HttpResponseForbidden("Forms can only be sent from this site.")

    wants_json = "application/json" in request.headers.get("Accept", "")
    form = FORMS[form_name](request.POST)

    # Bots that fill in the hidden honeypot field get the normal success response, but nothing is stored or sent.
    if form.is_spam():
        logger.info("Discarded a %s submission that filled in the honeypot field", form_name)
        return _respond(page, form_name, ok=True, wants_json=wants_json)

    if not form.is_valid():
        if wants_json:
            return JsonResponse({"ok": False, "errors": form.errors.get_json_data()}, status=400)
        return _respond(page, form_name, ok=False, wants_json=False)

    # Likely spam is saved under Leads → Spam without an email, and the sender sees the usual thanks (leads/spam.py)
    reasons = spam_reasons(request, form)
    name, email = form.submitter()
    submission = FormSubmission.objects.create(
        form_name=form_name,
        page=page,
        page_title=page.title,
        name=name,
        email=email,
        answers=form.answers(),
        data={key: value for key, value in form.cleaned_data.items() if key != "bot-field"},
        is_spam=bool(reasons),
        spam_reason="; ".join(reasons)[:500],
        ip_hash=hash_ip(client_ip(request)),
    )
    if reasons:
        logger.info("Saved %s submission %s as spam: %s", form_name, submission.pk, submission.spam_reason)
    else:
        notify(request, form, submission)
    return _respond(page, form_name, ok=True, wants_json=wants_json)


def is_same_origin(request):
    """True if the form was posted from a page on this site.

    Pages are served without Django's CSRF cookie so they can be cached (core/cache.py), so this takes the place of
    Django's CSRF check: browsers send an Origin header with every form POST (Referer as a fallback), and another
    site can't fake it. Requests with neither header are refused, as Django's CSRF check does over HTTPS.
    """
    source = request.headers.get("Origin") or request.headers.get("Referer")
    if not source or source == "null":
        return False
    parts = urlsplit(source)
    return parts.scheme == request.scheme and parts.netloc == request.get_host()


def notify(request, form, submission):
    """Email the submission to the address in Site settings. A failed email never loses the submission."""
    recipient = SiteSettings.for_request(request).lead_notification_email
    if not recipient:
        return
    name = " ".join(submission.name.split())  # no line breaks in email headers
    message = EmailMessage(
        subject=f"New {form.title.lower()} from {name}",
        body=(
            f"{form.email_answers()}\n\n"
            "---\n\n"
            f"Sent from: {submission.page_title} ({request.build_absolute_uri()})\n"
            f"All leads: {request.build_absolute_uri(reverse('leads:index'))}\n"
        ),
        to=[recipient],
        reply_to=[formataddr((name, submission.email))],
    )
    send_in_background(message, submission.pk)


def send_in_background(message, lead_pk):
    """Send `message` without making the visitor wait for it (sending through Resend's SMTP relay takes a few
    seconds). The lead is already saved, so a failed email only means a log entry.

    A normal (non-daemon) thread: when the server process is told to stop, e.g. during a deploy, Python waits for
    the email to finish (EMAIL_TIMEOUT caps how long). LEAD_EMAILS_IN_BACKGROUND = False sends in the request instead.
    """

    def send():
        try:
            message.send()
        except Exception:
            logger.exception("Could not email lead %s; it is saved in the admin", lead_pk)

    if not getattr(settings, "LEAD_EMAILS_IN_BACKGROUND", True):
        send()
        return None
    thread = threading.Thread(target=send, name=f"lead-email-{lead_pk}")
    thread.start()
    return thread


def _respond(page, form_name, *, ok, wants_json):
    if wants_json:
        return JsonResponse({"ok": ok})
    query = urlencode({"sent" if ok else "error": form_name})
    return HttpResponseRedirect(f"{page.url}?{query}#{form_name}")
