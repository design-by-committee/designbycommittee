from django.contrib.auth import get_user_model
from django.core import mail
from wagtail.models import Site

from core.models import SiteSettings
from leads.models import FormSubmission
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
}

ASSESSMENT = {
    "form-name": "landing-page-assessment",
    "url": "https://example.com/landing",
    "factors": "YES",
    "ux": "YES",
    "details": "",
    "first-name": "Sam",
    "last-name": "Visitor",
    "email": "sam@example.com",
    "date": "11-26-2026",
    "time": "10:00",
    "timezone": "Europe/Amsterdam",
}


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
