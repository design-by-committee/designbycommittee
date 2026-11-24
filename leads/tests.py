import threading
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from wagtail.models import Site

from core.models import SiteSettings
from core.cms import records
from leads.models import FormSubmission
from leads.spam import RATE_LIMIT, hash_ip
from pages.tests import SiteTestCase

# Browsers send Origin with every form POST; the lead forms check it (leads.views.is_same_origin)
ORIGIN = {"HTTP_ORIGIN": "http://testserver"}
JSON = {"HTTP_ACCEPT": "application/json", **ORIGIN}

ENQUIRY = {
    "form-name": "comedy-enquiry",
    "name": "Jo Comic",
    "email": "jo@example.com",
    "client-type": "Performer",
    "link": "instagram.com/jocomic",
    "details": "A Fringe hour",
    "bot-field": "",
    "fill-time": "40",  # added by comedy.js: seconds since the page opened
}

def weekday_ahead(days):
    """The first weekday at least `days` from today, as the date field sends it (YYYY-MM-DD)."""
    day = timezone.localdate() + timedelta(days=days)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


ASSESSMENT = {
    "form-name": "landing-page-assessment",
    "url": "https://example.com/landing",
    "factors": "YES",
    "ux": "YES",
    "details": "",
    "first-name": "Sam",
    "last-name": "Visitor",
    "email": "sam@example.com",
    "date": weekday_ahead(2),
    "time": "10:00",
    "timezone": "Europe/Amsterdam",
    "fill-time": "95",
}


@override_settings(LEAD_EMAILS_IN_BACKGROUND=False)  # so mail.outbox is filled before the response
class LeadFormTests(SiteTestCase):
    def setUp(self):
        settings = SiteSettings.for_site(Site.objects.get(is_default_site=True))
        settings.lead_notification_email = "leads@example.com"
        settings.save()

    def test_enquiry_is_saved_and_emailed(self):
        response = self.client.post("/comedy/", ENQUIRY, **JSON)

        self.assertEqual(response.json(), {"ok": True})
        submission = FormSubmission.objects.get()
        self.assertEqual((submission.form_name, submission.name, submission.email), ("comedy-enquiry", "Jo Comic", "jo@example.com"))
        self.assertEqual(submission.page.specific, self.comedy)
        self.assertIn("I’m a…: Performer", submission.answers)
        self.assertNotIn("Package", submission.answers)
        self.assertEqual(submission.data["client-type"], "Performer")

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["leads@example.com"])
        self.assertEqual(email.reply_to, ["Jo Comic <jo@example.com>"])
        self.assertEqual(email.subject, "New comedy enquiry from Jo Comic")
        # One field per paragraph in the email; the admin keeps the compact one-per-line version
        self.assertIn("Email: jo@example.com\n\nI’m a…: Performer\n\nCurrent website, if any: instagram.com/jocomic", email.body)
        self.assertIn("Email: jo@example.com\nI’m a…: Performer\n", submission.answers)
        self.assertTrue(email.body.startswith("Your name: Jo Comic\n\nEmail:"))

    def test_assessment_is_saved(self):
        response = self.client.post("/", ASSESSMENT, **JSON)

        self.assertEqual(response.json(), {"ok": True})
        submission = FormSubmission.objects.get()
        self.assertEqual(submission.name, "Sam Visitor")
        self.assertIn("Update my landing page to fix UX issues and increase conversions: Yes", submission.answers)
        self.assertNotIn("Test a new offer", submission.answers)  # unchecked boxes are left out

    def test_assessment_needs_an_interest(self):
        data = {key: value for key, value in ASSESSMENT.items() if key not in ("factors", "ux")}
        response = self.client.post("/", data, **JSON)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(FormSubmission.objects.exists())

    def test_invalid_enquiry_is_rejected(self):
        response = self.client.post("/comedy/", {**ENQUIRY, "email": "not-an-email", "client-type": "Juggler"}, **JSON)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["errors"]), {"email", "client-type"})
        self.assertFalse(FormSubmission.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_honeypot_submissions_are_discarded_quietly(self):
        response = self.client.post("/comedy/", {**ENQUIRY, "bot-field": "http://spam.example"}, **JSON)

        self.assertEqual(response.json(), {"ok": True})
        self.assertFalse(FormSubmission.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_a_page_only_accepts_its_own_forms(self):
        self.assertEqual(self.client.post("/", ENQUIRY, **JSON).status_code, 400)
        self.assertEqual(self.client.post("/comedy/", {**ENQUIRY, "form-name": "other"}, **JSON).status_code, 400)
        self.assertFalse(FormSubmission.objects.exists())

    def test_without_javascript_the_visitor_returns_to_the_page(self):
        response = self.client.post("/comedy/", ENQUIRY, **ORIGIN)
        self.assertRedirects(response, "/comedy/?sent=comedy-enquiry#comedy-enquiry", fetch_redirect_response=False)

        page = self.client.get("/comedy/?sent=comedy-enquiry")
        self.assertContains(page, '<div class="c-form__thanks" id="enquiryThanks">')  # no longer hidden

        response = self.client.post("/comedy/", {**ENQUIRY, "email": ""}, **ORIGIN)
        self.assertRedirects(response, "/comedy/?error=comedy-enquiry#comedy-enquiry", fetch_redirect_response=False)

    def test_no_notification_address_still_saves(self):
        SiteSettings.objects.update(lead_notification_email="")
        self.client.post("/comedy/", ENQUIRY, **JSON)

        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertEqual(mail.outbox, [])

    def test_forms_only_accept_posts_from_this_site(self):
        from django.test import Client

        # No CSRF token is needed (pages are cacheable), but the Origin (or Referer) must be this site
        client = Client(enforce_csrf_checks=True)
        accept = {"HTTP_ACCEPT": "application/json"}
        self.assertEqual(client.post("/comedy/", ENQUIRY, **JSON).status_code, 200)
        self.assertEqual(client.post("/comedy/", ENQUIRY, **accept, HTTP_REFERER="http://testserver/comedy/").status_code, 200)
        self.assertEqual(client.post("/comedy/", ENQUIRY, **accept, HTTP_ORIGIN="https://evil.example").status_code, 403)
        self.assertEqual(client.post("/comedy/", ENQUIRY, **accept, HTTP_ORIGIN="null").status_code, 403)
        self.assertEqual(client.post("/comedy/", ENQUIRY, **accept).status_code, 403)
        self.assertEqual(FormSubmission.objects.count(), 2)


@override_settings(LEAD_EMAILS_IN_BACKGROUND=False)  # so mail.outbox is filled before the response
class LeadAdminTests(SiteTestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "test-password")
        self.client.force_login(self.admin)
        self.client.post("/comedy/", ENQUIRY, **JSON)

    def test_leads_are_listed_and_exportable(self):
        response = self.client.get("/admin/leads/")
        self.assertContains(response, "Jo Comic")

        export = self.client.get("/admin/leads/?export=csv")
        self.assertEqual(export.status_code, 200)
        self.assertIn(b"jo@example.com", b"".join(export.streaming_content))

    def test_leads_cannot_be_added_by_hand(self):
        self.assertEqual(self.client.get("/admin/leads/new/").status_code, 302)  # permission denied redirect
        self.assertNotContains(self.client.get("/admin/leads/"), 'href="/admin/leads/new/"')

    def test_lead_can_be_inspected_and_marked_handled(self):
        submission = FormSubmission.objects.get()
        self.assertContains(self.client.get(f"/admin/leads/inspect/{submission.pk}/"), "A Fringe hour")

        self.client.post(f"/admin/leads/edit/{submission.pk}/", {"handled": "on"})
        submission.refresh_from_db()
        self.assertTrue(submission.handled)


@override_settings(LEAD_EMAILS_IN_BACKGROUND=False)  # so mail.outbox is filled before the response
class SpamTests(SiteTestCase):
    """Likely spam is saved under Leads → Spam with no email, and the sender sees the usual success response."""

    def setUp(self):
        SiteSettings.objects.update(lead_notification_email="leads@example.com")

    def assertSpam(self, url, data, reason):
        response = self.client.post(url, data, **JSON)
        self.assertEqual(response.json(), {"ok": True})
        submission = FormSubmission.objects.latest("submitted_at")
        self.assertTrue(submission.is_spam, data)
        self.assertIn(reason, submission.spam_reason)
        self.assertEqual(mail.outbox, [])
        submission.delete()

    def test_real_leads_are_not_flagged(self):
        self.client.post("/comedy/", ENQUIRY, **JSON)
        self.client.post("/", ASSESSMENT, **JSON)
        self.assertFalse(FormSubmission.objects.filter(is_spam=True).exists())
        self.assertEqual(len(mail.outbox), 2)

    def test_sent_without_javascript_or_too_fast(self):
        without = {key: value for key, value in ENQUIRY.items() if key != "fill-time"}
        self.assertSpam("/comedy/", without, "without the page’s JavaScript")
        self.assertSpam("/comedy/", {**ENQUIRY, "fill-time": "1"}, "sent 1s after the page opened")

    def test_html_or_lots_of_links(self):
        self.assertSpam("/comedy/", {**ENQUIRY, "details": "great app <a href=spam.shop>spam</a>"}, "HTML in")
        links = "https://a.example https://b.example www.c.example"
        self.assertSpam("/comedy/", {**ENQUIRY, "details": links}, "more than 2 links")

        self.client.post("/comedy/", {**ENQUIRY, "details": "Our site is https://jocomic.example"}, **JSON)
        self.assertFalse(FormSubmission.objects.get().is_spam)

    def test_assessment_dates_and_times_the_page_wouldnt_allow(self):
        self.assertSpam("/", {**ASSESSMENT, "date": "1983-01-02"}, "outside the next two weeks")
        saturday = timezone.localdate() + timedelta(days=(5 - timezone.localdate().weekday()) % 7 or 7)
        self.assertSpam("/", {**ASSESSMENT, "date": saturday.isoformat()}, "weekend")
        self.assertSpam("/", {**ASSESSMENT, "date": "soon"}, "date isn’t a date")
        self.assertSpam("/", {**ASSESSMENT, "time": "02:41"}, "outside 09:00–18:00")
        self.assertSpam("/", {**ASSESSMENT, "first-name": "pinco_x", "last-name": "Pinco_X"}, "same first and last name")

    def test_the_spam_that_got_through(self):
        # Lead 11 on the live site, which only the honeypot was there to stop
        spam = {
            **ASSESSMENT,
            "url": "https://spam.example",
            "details": "установить приложение <a href=spam.example>установить приложение</a>",
            "first-name": "pinco_izpl",
            "last-name": "pinco_izpl",
            "date": "1983-01-02",
            "time": "02:41",
            "timezone": "",
        }
        del spam["fill-time"]
        self.assertSpam("/", spam, "without the page’s JavaScript")

    def test_rate_limit_per_address(self):
        for _ in range(RATE_LIMIT):
            self.client.post("/comedy/", ENQUIRY, **JSON, HTTP_CF_CONNECTING_IP="203.0.113.7")
        self.assertFalse(FormSubmission.objects.filter(is_spam=True).exists())
        self.client.post("/comedy/", ENQUIRY, **JSON, HTTP_CF_CONNECTING_IP="198.51.100.2")  # another address is fine
        self.assertFalse(FormSubmission.objects.filter(is_spam=True).exists())

        self.client.post("/comedy/", ENQUIRY, **JSON, HTTP_CF_CONNECTING_IP="203.0.113.7")
        flagged = FormSubmission.objects.get(is_spam=True)
        self.assertIn(f"{RATE_LIMIT + 1} submissions from one address within an hour", flagged.spam_reason)

    def test_only_a_hash_of_the_address_is_stored(self):
        self.client.post("/comedy/", ENQUIRY, **JSON, HTTP_CF_CONNECTING_IP="203.0.113.7")
        submission = FormSubmission.objects.get()
        self.assertEqual(submission.ip_hash, hash_ip("203.0.113.7"))
        self.assertNotIn("203.0.113.7", str(submission.data) + submission.answers + submission.ip_hash)

    def test_spam_has_its_own_admin_list_and_can_be_moved_back(self):
        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "test-password")
        self.client.force_login(admin)
        self.client.post("/comedy/", {**ENQUIRY, "fill-time": "0", "name": "Spammy McSpam"}, **JSON)
        spam = FormSubmission.objects.get()

        self.assertNotContains(self.client.get("/admin/leads/"), "Spammy McSpam")
        self.assertContains(self.client.get("/admin/spam/"), "Spammy McSpam")
        self.assertContains(self.client.get(f"/admin/spam/inspect/{spam.pk}/"), "sent 0s after the page opened")

        self.client.post(f"/admin/spam/edit/{spam.pk}/", {})  # untick Spam
        self.assertContains(self.client.get("/admin/leads/"), "Spammy McSpam")

    def test_cms_lists_spam_separately(self):
        self.client.post("/comedy/", ENQUIRY, **JSON)
        self.client.post("/comedy/", {**ENQUIRY, "fill-time": "0", "name": "Spammy McSpam"}, **JSON)
        self.assertNotIn("Spammy", records.leads_list())
        self.assertIn("Spammy", records.leads_list(spam=True))
        self.assertNotIn("Spammy", records.leads_export())


class BackgroundEmailTests(SiteTestCase):
    """The visitor's reply doesn't wait for the notification email (LEAD_EMAILS_IN_BACKGROUND, on by default)."""

    def setUp(self):
        SiteSettings.objects.update(lead_notification_email="leads@example.com")

    def test_reply_comes_before_the_email_is_sent(self):
        release = threading.Event()
        started = []
        real_send = mail.EmailMessage.send

        def slow_send(message, *args, **kwargs):
            release.wait(5)  # stands in for a slow SMTP relay
            return real_send(message, *args, **kwargs)

        real_thread = threading.Thread

        def record_thread(*args, **kwargs):
            thread = real_thread(*args, **kwargs)
            started.append(thread)
            return thread

        with mock.patch("leads.views.EmailMessage.send", slow_send), mock.patch("leads.views.threading.Thread", record_thread):
            response = self.client.post("/comedy/", ENQUIRY, **JSON)
            self.assertEqual(response.json(), {"ok": True})
            self.assertEqual(mail.outbox, [])  # replied while the email was still waiting
            release.set()
            started[0].join(5)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "New comedy enquiry from Jo Comic")
        self.assertFalse(started[0].daemon)  # a deploy's shutdown waits for it

    def test_a_failed_email_is_logged_and_the_lead_kept(self):
        with mock.patch("leads.views.EmailMessage.send", side_effect=OSError("relay down")):
            with self.assertLogs("leads.views", "ERROR"):
                with override_settings(LEAD_EMAILS_IN_BACKGROUND=False):
                    self.client.post("/comedy/", ENQUIRY, **JSON)
        self.assertEqual(FormSubmission.objects.count(), 1)

