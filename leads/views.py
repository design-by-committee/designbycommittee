import logging
from email.utils import formataddr
from urllib.parse import urlencode

from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.urls import reverse

from core.models import SiteSettings

from .forms import FORMS
from .models import FormSubmission

logger = logging.getLogger(__name__)


def handle_submission(request, page):
    """Validate and store a lead form posted to `page`, then email a notification.

    The page's JavaScript posts with `Accept: application/json` and gets JSON back. Without JavaScript, the browser
    is redirected back to the page with ?sent=<form-name> (or ?error=<form-name>) so the template can show the result.
    """
    form_name = request.POST.get("form-name", "")
    if form_name not in FORMS or form_name not in page.form_names():
        return HttpResponseBadRequest("Unknown form")

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

    name, email = form.submitter()
    submission = FormSubmission.objects.create(
        form_name=form_name,
        page=page,
        page_title=page.title,
        name=name,
        email=email,
        answers=form.answers(),
        data={key: value for key, value in form.cleaned_data.items() if key != "bot-field"},
    )
    notify(request, form, submission)
    return _respond(page, form_name, ok=True, wants_json=wants_json)


def notify(request, form, submission):
    """Email the submission to the address in Site settings. A failed email never loses the submission."""
    recipient = SiteSettings.for_request(request).lead_notification_email
    if not recipient:
        return
    name = " ".join(submission.name.split())  # no line breaks in email headers
    message = EmailMessage(
        subject=f"New {form.title.lower()} from {name}",
        body=(
            f"{submission.answers}\n\n"
            f"Sent from: {submission.page_title} ({request.build_absolute_uri()})\n"
            f"All leads: {request.build_absolute_uri(reverse('leads:index'))}\n"
        ),
        to=[recipient],
        reply_to=[formataddr((name, submission.email))],
    )
    try:
        message.send()
    except Exception:
        logger.exception("Could not email lead %s; it is saved in the admin", submission.pk)


def _respond(page, form_name, *, ok, wants_json):
    if wants_json:
        return JsonResponse({"ok": ok})
    query = urlencode({"sent" if ok else "error": form_name})
    return HttpResponseRedirect(f"{page.url}?{query}#{form_name}")
