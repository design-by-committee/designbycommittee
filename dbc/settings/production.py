"""Production settings (Render). Every secret and host name comes from environment variables set in render.yaml."""

import os

from .base import *  # noqa: F403


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

# RENDER_EXTERNAL_HOSTNAME is set by Render to the service's *.onrender.com host name.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS") + env_list("RENDER_EXTERNAL_HOSTNAME")
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if not host.startswith(".")]

# Hashed, compressed static files served by WhiteNoise with far-future cache headers.
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# HTTPS: Render terminates TLS and forwards the original scheme in X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Start with a short HSTS max-age; raise it once the site has run on Render for a while.
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 60 * 60 * 24))
# HSTS deliberately covers only the website host: other subdomains (email, Resend's send.) aren't
# served by this app, and preload-list entries are hard to undo.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Full site URL for links in admin emails. Falls back to Render's own *.onrender.com URL (RENDER_EXTERNAL_URL).
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL") or os.environ.get(
    "RENDER_EXTERNAL_URL", WAGTAILADMIN_BASE_URL  # noqa: F405
)

# Form notification emails go out through Resend's SMTP relay; the password is the Resend API key.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.resend.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "resend")
EMAIL_HOST_PASSWORD = os.environ.get("RESEND_API_KEY", "")
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"), "propagate": False},
    },
}
