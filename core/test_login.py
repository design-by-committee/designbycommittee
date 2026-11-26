"""Brute-force protection for the Wagtail admin sign-in (django-axes, AXES_* in dbc/settings/base.py)."""

import io
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

LOGIN_URL = "/admin/login/"
PASSWORD = "correct-horse-battery-staple"
VISITOR = "203.0.113.7"


# A fast hasher: these tests check dozens of passwords
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AdminLoginLockoutTests(TestCase):
    def setUp(self):
        axes_log = logging.getLogger("axes")
        axes_log.disabled = True  # a warning per failed attempt
        self.addCleanup(setattr, axes_log, "disabled", False)
        self.editor = get_user_model().objects.create_superuser("editor", "editor@example.com", PASSWORD)

    def sign_in(self, password, ip=VISITOR, username="editor"):
        # Render's edge reports the visitor's address in CF-Connecting-IP (leads/spam.py client_ip)
        return self.client.post(LOGIN_URL, {"username": username, "password": password}, HTTP_CF_CONNECTING_IP=ip)

    def fail(self, times, **kwargs):
        for _ in range(times):
            response = self.sign_in("wrong", **kwargs)
            self.assertEqual(response.status_code, 200)  # the login form again, with an error

    def lock_out(self):
        """Fail until locked out: the attempt that reaches the limit is already refused."""
        self.fail(settings.AXES_FAILURE_LIMIT - 1)
        self.assertLockedOut(self.sign_in("wrong"))

    def assertSignedIn(self, response):
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.client.logout()

    def assertLockedOut(self, response):
        self.assertContains(response, "too many login attempts", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_correct_password_signs_in(self):
        self.assertSignedIn(self.sign_in(PASSWORD))

    def test_locked_out_after_the_failure_limit_even_with_the_right_password(self):
        self.lock_out()
        self.assertLockedOut(self.sign_in(PASSWORD))

    def test_a_successful_sign_in_resets_the_failure_count(self):
        self.fail(settings.AXES_FAILURE_LIMIT - 1)
        self.assertSignedIn(self.sign_in(PASSWORD))
        self.fail(settings.AXES_FAILURE_LIMIT - 1)
        self.assertSignedIn(self.sign_in(PASSWORD))

    def test_lockout_is_per_username_and_address(self):
        self.lock_out()
        self.assertSignedIn(self.sign_in(PASSWORD, ip="198.51.100.20"))

    def test_address_comes_from_the_edge_not_the_proxy(self):
        # Without CF-Connecting-IP every request would share Render's proxy address and one attacker could lock
        # out everyone; with it, each visitor is counted separately.
        self.lock_out()
        response = self.client.post(
            LOGIN_URL,
            {"username": "editor", "password": PASSWORD},
            HTTP_CF_CONNECTING_IP="198.51.100.20",
            REMOTE_ADDR=VISITOR,
        )
        self.assertSignedIn(response)

    def test_axes_reset_unlocks(self):
        self.lock_out()
        call_command("axes_reset", stdout=io.StringIO())
        self.assertSignedIn(self.sign_in(PASSWORD))

    def test_health_check_answers_while_locked_out(self):
        self.lock_out()
        response = self.client.get("/healthz/", HTTP_CF_CONNECTING_IP=VISITOR)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_signed_in_editors_are_not_affected_by_a_lockout(self):
        self.lock_out()
        self.client.force_login(self.editor)
        response = self.client.get("/admin/", HTTP_CF_CONNECTING_IP=VISITOR)
        self.assertEqual(response.status_code, 200)
