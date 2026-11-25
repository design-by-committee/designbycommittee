import io
import json
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from pages.content_ops import ContentError, resolve_block
from pages.models import HomePage, LandingPage
from pages.tests import SiteTestCase


class PageEditTests(SiteTestCase):
    def edit(self, page, changes, *flags):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(changes, f)
        out = io.StringIO()
        call_command("cms", "pages", "edit", page, "--data-file", f.name, *flags, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def live_home(self):
        return HomePage.objects.get().specific

    def test_search_and_structured_data_fields(self):
        self.edit(
            "/comedy/",
            [
                {"op": "set_field", "field": "show_in_menus", "value": True},
                {"op": "set_field", "field": "service_name", "value": "Websites for comedians"},
                {"op": "set_field", "field": "extra_json_ld", "value": '{"@type": "Event", "name": "Showcase"}'},
            ],
            "--publish",
        )
        comedy = LandingPage.objects.get(slug="comedy")
        self.assertTrue(comedy.show_in_menus)
        self.assertEqual(comedy.service_name, "Websites for comedians")

    def test_extra_json_ld_is_validated(self):
        with self.assertRaises(CommandError):
            self.edit("/comedy/", [{"op": "set_field", "field": "extra_json_ld", "value": "not json"}], "--publish")

    def test_dry_run_validates_and_saves_nothing(self):
        revisions = self.home.revisions.count()
        out = self.edit("/", [{"op": "set", "block": "feature:3", "path": "points.0", "value": "Match copy to each ad"}])

        self.assertIn('+', out)
        self.assertIn("Match copy to each ad", out)
        self.assertIn("Dry run", out)
        self.assertEqual(self.home.revisions.count(), revisions)

    def test_draft_leaves_the_live_page_alone(self):
        self.edit("/", [{"op": "set", "block": "feature:3", "path": "points.0", "value": "Draft point"}], "--draft")

        home = self.live_home()
        self.assertTrue(home.has_unpublished_changes)
        # body[4] is the third "feature" block; the live page still has the original first point
        self.assertEqual(home.body[4].value["points"][0], "Analyze website data for conversion signals")
        draft = home.get_latest_revision()
        self.assertEqual(draft.user.username, "claude")
        self.assertEqual(draft.as_object().body[4].value["points"][0], "Draft point")

    def test_publish(self):
        self.edit("/comedy/", [{"op": "set_field", "field": "seo_title", "value": "New title"}], "--publish")

        comedy = LandingPage.objects.get(slug="comedy")
        self.assertEqual(comedy.seo_title, "New title")
        self.assertFalse(comedy.has_unpublished_changes)
        self.assertContains(self.client.get("/comedy/"), "<title>New title</title>")

    def test_claude_user_cannot_sign_in(self):
        self.edit("/", [{"op": "set_field", "field": "title", "value": "Home"}, {"op": "set_field", "field": "seo_title", "value": "x"}], "--draft")
        claude = get_user_model().objects.get(username="claude")
        self.assertFalse(claude.is_active)
        self.assertFalse(claude.has_usable_password())

    def test_insert_move_and_remove_blocks(self):
        self.edit(
            "/comedy/",
            [
                {"op": "insert", "type": "text", "after": "steps", "value": {"heading": "Extra", "body": "<p>Hello</p>"}},
                {"op": "move", "block": "faq", "before": "packages"},
                {"op": "remove", "block": "timeline"},
            ],
            "--publish",
        )
        types = [block.block_type for block in LandingPage.objects.get(slug="comedy").body]
        self.assertEqual(
            types, ["screenshot_hero", "cards", "columns", "steps", "text", "faq", "packages", "cards", "enquiry_form"]
        )

    def test_invalid_content_is_rejected(self):
        with self.assertRaisesMessage(CommandError, "isn't valid"):
            self.edit("/comedy/", [{"op": "set", "block": "steps", "path": "heading", "value": ""}], "--publish")
        with self.assertRaisesMessage(CommandError, "isn't allowed"):
            self.edit("/comedy/", [{"op": "insert", "type": "hero", "value": {}}])
        with self.assertRaisesMessage(CommandError, "no field 'nope'"):
            self.edit("/comedy/", [{"op": "set", "block": "steps", "path": "nope", "value": "x"}])
        with self.assertRaisesMessage(CommandError, "can't be edited here"):
            self.edit("/comedy/", [{"op": "set_field", "field": "live", "value": False}])
        self.assertFalse(LandingPage.objects.get(slug="comedy").has_unpublished_changes)

    def test_sets_a_field_added_after_the_content_was_saved(self):
        # The imported work cards were saved before cards had a screenshot field, so their stored data has no "image" key
        image = self.any_image()
        out = self.edit("/comedy/", [{
            "op": "set", "block": "cards:2", "path": "cards.0.image",
            "value": {"image": image.pk, "alt_text": "The Fallout Theater homepage", "decorative": False},
        }], "--publish")

        self.assertNotIn('-                "colour"', out)  # only the new field shows up in the diff
        card = LandingPage.objects.get(slug="comedy").body[6].value["cards"][0]
        self.assertEqual(card["image"].pk, image.pk)
        self.assertContains(self.client.get("/comedy/"), 'alt="The Fallout Theater homepage"')

    def any_image(self):
        from wagtail.images import get_image_model

        return get_image_model().objects.first()

    def test_publish_refuses_to_publish_someone_elses_draft(self):
        editor = get_user_model().objects.create_superuser("andres", "a@example.com", "x")
        comedy = LandingPage.objects.get(slug="comedy")
        comedy.title = "Their draft"
        comedy.save_revision(user=editor)

        change = [{"op": "set_field", "field": "seo_title", "value": "Mine"}]
        with self.assertRaisesMessage(CommandError, "would also publish that draft"):
            self.edit("/comedy/", change, "--publish")
        self.edit("/comedy/", change, "--draft")  # a draft on top of theirs is fine

        latest = LandingPage.objects.get(slug="comedy").get_latest_revision().as_object()
        self.assertEqual((latest.title, latest.seo_title), ("Their draft", "Mine"))


class PageShowTests(SiteTestCase):
    def test_lists_pages_and_shows_block_ids(self):
        out = io.StringIO()
        call_command("cms", "pages", "list", stdout=out)
        self.assertEqual([page["url"] for page in json.loads(out.getvalue())], ["/", "/comedy/"])

        out = io.StringIO()
        call_command("cms", "pages", "show", "/comedy/", stdout=out)
        data = json.loads(out.getvalue())
        self.assertEqual(data["page"]["type"], "LandingPage")
        self.assertTrue(all(block["id"] for block in data["body"]))


class ResolveBlockTests(SiteTestCase):
    blocks = [
        {"type": "hero", "id": "aaaa1111"},
        {"type": "feature", "id": "bbbb2222"},
        {"type": "feature", "id": "cccc3333"},
    ]

    def test_references(self):
        self.assertEqual(resolve_block(self.blocks, "hero"), 0)
        self.assertEqual(resolve_block(self.blocks, "feature:2"), 2)
        self.assertEqual(resolve_block(self.blocks, "#2"), 1)
        self.assertEqual(resolve_block(self.blocks, "cccc3333"), 2)
        self.assertEqual(resolve_block(self.blocks, "bbbb"), 1)
        with self.assertRaisesMessage(ContentError, "use feature:1"):
            resolve_block(self.blocks, "feature")
        with self.assertRaisesMessage(ContentError, "No block matches"):
            resolve_block(self.blocks, "faq")
