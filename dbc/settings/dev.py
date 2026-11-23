"""Local development settings. Values can be overridden in a gitignored .env file (see .env.example)."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing base, which reads DATABASE_URL, MEDIA_ROOT etc. from the environment.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from .base import *  # noqa: E402,F403

DEBUG = True

SECRET_KEY = "django-insecure-local-development-only"  # noqa: S105

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
