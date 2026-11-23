import io
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from wagtail.contrib.redirects.models import Redirect
from wagtail.images import get_image_model
from wagtail.models import PageLogEntry, Site

from core.models import SiteSettings, Testimonial
from leads.models import FormSubmission
from pages.models import HomePage, LandingPage
from pages.tests import SiteTestCase


def cms(*args, stdin=None):
    out = io.StringIO()
    if stdin is not None:
        import sys

        original, sys.stdin = sys.stdin, stdin
        try:
            call_command("cms", *args, stdout=out, stderr=io.StringIO())
        finally:
            sys.stdin = original
    else:
        call_command("cms", *args, stdout=out, stderr=io.StringIO())
    return out.getvalue()


class PageActionTests(SiteTestCase):
    NEW_PAGE = {
        "title": "Festivals",
        "seo_title": "Websites for festivals",
        "body": [{"type": "text", "value": {"heading": "Hello", "body": "<p>Festival sites.</p>"}}],
    }

    def test_create_is_a_dry_run_by_default(self):
        out = cms("pages", "create", "/", "LandingPage", "--data", json.dumps(self.NEW_PAGE))
        self.assertIn("Dry run", out)
        self.assertFalse(LandingPage.objects.filter(slug="festivals").exists())

    def test_create_publish_unpublish_and_delete(self):
        cms("pages", "create", "/", "LandingPage", "--data", json.dumps(self.NEW_PAGE), "--publish")
        page = LandingPage.objects.get(slug="festivals")
        self.assertTrue(page.live)
        self.assertEqual(page.get_latest_revision().user.username, "claude")
        self.assertContains(self.client.get("/festivals/"), "Festival sites.")

        cms("pages", "unpublish", "/festivals/", "--apply")
        self.assertEqual(self.client.get("/festivals/").status_code, 404)

        cms("pages", "delete", "/festivals/", "--apply")
        self.assertFalse(LandingPage.objects.filter(slug="festivals").exists())

    def test_create_validates_like_the_admin(self):
        with self.assertRaisesMessage(CommandError, "can't go under"):
            cms("pages", "create", "/comedy/", "LandingPage", "--data", '{"title": "Nested"}')
        with self.assertRaisesMessage(CommandError, "can't go under"):
            cms("pages", "create", "/", "HomePage", "--data", '{"title": "Second home"}')
        bad_block = {**self.NEW_PAGE, "body": [{"type": "text", "value": {"heading": ""}}]}
        with self.assertRaisesMessage(CommandError, "isn't valid"):
            cms("pages", "create", "/", "LandingPage", "--data", json.dumps(bad_block), "--draft")
        with self.assertRaisesMessage(CommandError, "slug"):
            cms("pages", "create", "/", "LandingPage", "--data", '{"title": "Comedy"}', "--draft")

    def test_copy_move_and_revert(self):
        cms("pages", "copy", "/comedy/", "/", "--title", "Comedy copy", "--slug", "comedy-copy", "--apply")
        copy = LandingPage.objects.get(slug="comedy-copy")
        self.assertFalse(copy.live)  # copies are drafts unless --keep-live

        cms("pages", "move", "/comedy-copy/", "/comedy/", "--position", "left", "--apply")
        self.assertEqual([p.slug for p in HomePage.objects.get().get_children()], ["comedy-copy", "comedy"])

        original = self.comedy.live_revision_id
        cms("pages", "edit", "/comedy/", "--data", '[{"op": "set_field", "field": "seo_title", "value": "Changed"}]', "--publish")
        cms("pages", "revert", "/comedy/", str(original), "--publish", "--apply")
        self.assertEqual(LandingPage.objects.get(slug="comedy").seo_title, self.comedy.seo_title)

    def test_home_page_is_protected(self):
        for action in ("delete", "unpublish", "move"):
            args = ["pages", action, "/"] + (["/comedy/"] if action == "move" else []) + ["--apply"]
            with self.assertRaisesMessage(CommandError, "home page"):
                cms(*args)

    def test_delete_refuses_linked_pages_without_force(self):
        cms("pages", "create", "/", "LandingPage", "--publish", "--data", json.dumps(
            {"title": "Linker", "body": [{"type": "text", "value": {"heading": "Link", "body": f'<p><a linktype="page" id="{self.comedy.pk}">Comedy</a></p>'}}]}
        ))
        with self.assertRaisesMessage(CommandError, "linked from"):
            cms("pages", "delete", "/comedy/", "--apply")
        self.assertTrue(LandingPage.objects.filter(slug="comedy").exists())

    def test_lock_and_actions_are_logged(self):
        cms("pages", "lock", "/comedy/", "--apply")
        self.assertTrue(LandingPage.objects.get(slug="comedy").locked)
        with self.assertRaisesMessage(CommandError, "locked"):
            cms("pages", "edit", "/comedy/", "--data", '[{"op": "set_field", "field": "seo_title", "value": "x"}]')
        cms("pages", "unlock", "/comedy/", "--apply")
        actions = set(PageLogEntry.objects.filter(page=self.comedy, user__username="claude").values_list("action", flat=True))
        self.assertTrue({"wagtail.lock", "wagtail.unlock"} <= actions)


class RecordTests(SiteTestCase):
    def test_snippet_update_dry_run_and_apply(self):
        testimonial = Testimonial.objects.get(name="Aaron Walther")
        out = cms("snippets", "update", "testimonial", str(testimonial.pk), "--data", '{"role": "Founder"}')
        self.assertIn('"Co-Founder" → "Founder"', out)
        self.assertIn("Dry run", out)
        testimonial.refresh_from_db()
        self.assertEqual(testimonial.role, "Co-Founder")

        cms("snippets", "update", "testimonial", str(testimonial.pk), "--data", '{"role": "Founder"}', "--apply")
        testimonial.refresh_from_db()
        self.assertEqual(testimonial.role, "Founder")
        self.assertEqual(testimonial.logo_id, Testimonial.objects.get(pk=testimonial.pk).logo_id)  # untouched fields kept

    def test_snippet_validation_and_in_use_protection(self):
        with self.assertRaisesMessage(CommandError, "Not valid"):
            cms("snippets", "create", "testimonial", "--data", '{"name": "No quote"}', "--apply")
        with self.assertRaisesMessage(CommandError, "Unknown field"):
            cms("snippets", "update", "testimonial", "1", "--data", '{"colour": "red"}')
        used = Testimonial.objects.get(name="Aaron Walther")
        with self.assertRaisesMessage(CommandError, "used in"):
            cms("snippets", "delete", "testimonial", str(used.pk), "--apply")

    def test_settings_update(self):
        cms("settings", "update", "sitesettings", "--data", '{"lead_notification_email": "new@example.com"}', "--apply")
        self.assertEqual(SiteSettings.for_site(Site.objects.get()).lead_notification_email, "new@example.com")
        with self.assertRaisesMessage(CommandError, "Not valid"):
            cms("settings", "update", "sitesettings", "--data", '{"lead_notification_email": "not-an-email"}', "--apply")

    def test_redirects(self):
        cms("redirects", "create", "--data", json.dumps({"old_path": "/old-comedy", "redirect_page": self.comedy.pk, "is_permanent": True}), "--apply")
        redirect = Redirect.objects.get()
        self.assertEqual(redirect.old_path, "/old-comedy")
        self.assertRedirects(self.client.get("/old-comedy"), "/comedy/", status_code=301)

    def test_leads(self):
        lead = FormSubmission.objects.create(form_name="comedy-enquiry", name="Jo", email="jo@example.com", answers="x")
        cms("leads", "update", str(lead.pk), "--data", '{"handled": true}', "--apply")
        lead.refresh_from_db()
        self.assertTrue(lead.handled)
        self.assertIn("jo@example.com", cms("leads", "export"))
        cms("leads", "delete", str(lead.pk), "--apply")
        self.assertFalse(FormSubmission.objects.exists())


class ImageTests(SiteTestCase):
    def test_upload_from_stdin_update_and_delete(self):
        svg = Path(settings.BASE_DIR, "static/img/testimonial-fallout-theater.svg").read_bytes()

        class Stdin:
            buffer = io.BytesIO(svg)

        out = cms("images", "upload", "--file", "-", "--filename", "logo.svg", "--data", '{"title": "New logo"}', stdin=Stdin())
        self.assertIn("Dry run", out)
        self.assertFalse(get_image_model().objects.filter(title="New logo").exists())

        Stdin.buffer = io.BytesIO(svg)
        cms("images", "upload", "--file", "-", "--filename", "logo.svg", "--data", '{"title": "New logo"}', "--apply", stdin=Stdin())
        image = get_image_model().objects.get(title="New logo")

        cms("images", "update", str(image.pk), "--data", '{"title": "Renamed", "tags": ["logos"]}', "--apply")
        image.refresh_from_db()
        self.assertEqual((image.title, list(image.tags.names())), ("Renamed", ["logos"]))

        self.assertIn("would delete", cms("images", "delete", str(image.pk)))
        cms("images", "delete", str(image.pk), "--apply")
        self.assertFalse(get_image_model().objects.filter(pk=image.pk).exists())

    def test_images_in_use_are_protected(self):
        used = Testimonial.objects.get(name="Aaron Walther").logo
        with self.assertRaisesMessage(CommandError, "used in"):
            cms("images", "delete", str(used.pk), "--apply")


class UserTests(SiteTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser("owner", "owner@example.com", "pw")

    def test_create_user_without_password(self):
        out = cms("users", "create", "--data", '{"username": "editor", "email": "editor@example.com", "first_name": "Ed"}', "--apply")
        self.assertIn("Forgot password", out)
        editor = get_user_model().objects.get(username="editor")
        self.assertFalse(editor.has_usable_password())

    def test_password_hash_never_shown(self):
        out = cms("users", "show", str(self.owner.pk))
        self.assertNotIn("pbkdf2", out)
        self.assertNotIn("password", json.loads(out))

    def test_last_superuser_is_protected(self):
        with self.assertRaisesMessage(CommandError, "last active superuser"):
            cms("users", "update", str(self.owner.pk), "--data", '{"is_superuser": false}', "--apply")
        with self.assertRaisesMessage(CommandError, "last active superuser"):
            cms("users", "delete", str(self.owner.pk), "--force", "--apply")

    def test_claude_user_cannot_be_changed(self):
        cms("snippets", "update", "testimonial", str(Testimonial.objects.first().pk), "--data", '{"role": "x"}', "--apply")
        claude = get_user_model().objects.get(username="claude")
        with self.assertRaisesMessage(CommandError, "managed by this tool"):
            cms("users", "update", str(claude.pk), "--data", '{"is_active": true}', "--apply")
