import io
import json
import urllib.error
from datetime import timedelta
from unittest import mock

from django.core import checks
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from wagtail.actions.move_page import MovePageAction

from core import indexnow
from pages.models import LandingPage
from pages.tests import SiteTestCase

ENABLED = {"INDEXNOW_ENABLED": True, "INDEXABLE_HOSTS": ["testserver"], "INDEXNOW_KEY": ""}


class KeyTests(SimpleTestCase):
    def test_derived_key_follows_the_indexnow_format_and_is_stable(self):
        key = indexnow.get_key()
        self.assertRegex(key, indexnow.KEY_PATTERN)
        self.assertEqual(key, indexnow.get_key())
        with override_settings(SECRET_KEY="another-secret"):
            self.assertNotEqual(indexnow.get_key(), key)

    @override_settings(INDEXNOW_KEY="my-own-key-123")
    def test_key_can_be_set(self):
        self.assertEqual(indexnow.get_key(), "my-own-key-123")
        self.assertEqual(indexnow.check_key(None), [])

    @override_settings(INDEXNOW_KEY="has_underscores=")
    def test_invalid_key_fails_the_system_checks(self):
        self.assertEqual([error.id for error in indexnow.check_key(None)], ["core.E001"])
        self.assertIn("core.E001", [error.id for error in checks.run_checks()])


class KeyFileTests(SiteTestCase):
    def test_key_file_is_served_at_the_root(self):
        key = indexnow.get_key()
        response = self.client.get(f"/{key}.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), key)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("public", response["Cache-Control"])

    def test_other_txt_files_are_not_found(self):
        self.assertEqual(self.client.get("/not-the-key.txt").status_code, 404)
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/llms.txt").status_code, 200)


class RunInline:
    """Stands in for threading.Timer so queued URLs are sent straight away in tests."""

    def __init__(self, interval, function):
        self.function = function

    def start(self):
        self.function()


@override_settings(**ENABLED)
@mock.patch("core.indexnow.threading.Timer", RunInline)
class SubmissionTests(SiteTestCase):
    def setUp(self):
        patcher = mock.patch("core.indexnow.submit")
        self.submit = patcher.start()
        self.addCleanup(patcher.stop)
        indexnow._outbox.clear()
        indexnow._last_submitted.clear()
        indexnow._timer["running"] = False
        # Each step stands for a separate change, more than RESUBMIT_SECONDS apart unless a test says otherwise
        self.now = 0.0
        clock = mock.patch("core.indexnow.time.monotonic", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def later(self, seconds=indexnow.RESUBMIT_SECONDS):
        self.now += seconds

    def submitted(self):
        return sorted(url for call in self.submit.call_args_list for url in call.args[1])

    def cms(self, *args):
        call_command("cms", *args, stdout=io.StringIO(), stderr=io.StringIO())

    def edit(self, *args):
        changes = '[{"op": "set_field", "field": "seo_title", "value": "New title"}]'
        self.cms("pages", "edit", "/comedy/", "--data", changes, *args)

    def test_publishing_submits_the_page(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.edit("--publish")
        self.submit.assert_called_once_with("testserver", ["http://testserver/comedy/"])

    def test_publishing_from_code_submits_the_page(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.save_revision().publish()
        self.assertEqual(self.submitted(), ["http://testserver/comedy/"])

    def test_drafts_and_dry_runs_submit_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.edit()  # dry run, rolled back
            self.edit("--draft")
        self.submit.assert_not_called()

    def test_pages_hidden_from_search_engines_are_not_submitted(self):
        self.comedy.noindex = True
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.save_revision().publish()
            self.cms("pages", "unpublish", "/comedy/", "--apply")
        self.submit.assert_not_called()

    def test_scheduled_publishing_waits_until_the_page_goes_live(self):
        self.comedy.go_live_at = timezone.now() + timedelta(days=1)
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.save_revision().publish()
        self.submit.assert_not_called()

    def test_unpublishing_submits_the_now_missing_url(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("pages", "unpublish", "/comedy/", "--apply")
        self.assertEqual(self.submitted(), ["http://testserver/comedy/"])

    def test_deleting_submits_the_url_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.delete()
        self.assertEqual(self.submitted(), ["http://testserver/comedy/"])

    def test_renaming_submits_the_old_and_new_urls(self):
        self.comedy.slug = "stand-up"
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.save_revision().publish()
        self.assertEqual(self.submitted(), ["http://testserver/comedy/", "http://testserver/stand-up/"])

    def test_moving_submits_old_and_new_urls_of_the_page_and_its_children(self):
        parent = self.home.add_child(instance=LandingPage(title="Services", slug="services"))
        self.comedy.add_child(instance=LandingPage(title="Fringe", slug="fringe"))
        self.submit.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            MovePageAction(self.comedy, parent, pos="last-child").execute(skip_permission_checks=True)
        self.assertEqual(
            self.submitted(),
            [
                "http://testserver/comedy/",
                "http://testserver/comedy/fringe/",
                "http://testserver/services/comedy/",
                "http://testserver/services/comedy/fringe/",
            ],
        )

    def test_the_same_url_is_not_resubmitted_within_a_few_minutes(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.edit("--publish")
        self.later(60)
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.refresh_from_db()
            self.comedy.save_revision().publish()
        self.assertEqual(self.submit.call_count, 1)
        self.later()
        with self.captureOnCommitCallbacks(execute=True):
            self.comedy.save_revision().publish()
        self.assertEqual(self.submit.call_count, 2)

    @override_settings(INDEXABLE_HOSTS=["designbycommitt.ee"])
    def test_hosts_search_engines_dont_index_are_not_submitted(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.edit("--publish")
        self.submit.assert_not_called()

    @override_settings(INDEXNOW_ENABLED=False)
    def test_nothing_is_submitted_when_turned_off(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.edit("--publish")
        self.submit.assert_not_called()


@override_settings(INDEXNOW_KEY="test-key-1234")
class SubmitRequestTests(SimpleTestCase):
    def test_submits_the_urls_to_indexnow(self):
        response = mock.MagicMock(status=202)
        response.__enter__.return_value = response
        with mock.patch("core.indexnow.urllib.request.urlopen", return_value=response) as urlopen:
            self.assertTrue(indexnow.submit("designbycommitt.ee", ["https://designbycommitt.ee/comedy/"]))
        request = urlopen.call_args.args[0]
        self.assertEqual((request.method, request.full_url), ("POST", "https://api.indexnow.org/indexnow"))
        self.assertEqual(request.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(
            json.loads(request.data),
            {"host": "designbycommitt.ee", "key": "test-key-1234", "urlList": ["https://designbycommitt.ee/comedy/"]},
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)

    def test_errors_are_logged_not_raised(self):
        error = urllib.error.HTTPError(indexnow.ENDPOINT, 403, "Forbidden", {}, io.BytesIO(b"key not valid"))
        for failure in (error, OSError("network down")):
            with mock.patch("core.indexnow.urllib.request.urlopen", side_effect=failure):
                with self.assertLogs("core.indexnow", "WARNING"):
                    self.assertFalse(indexnow.submit("designbycommitt.ee", ["https://designbycommitt.ee/"]))
