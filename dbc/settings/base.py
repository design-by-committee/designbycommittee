"""Settings shared by every environment. Environment-specific values live in dev.py and production.py."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


INSTALLED_APPS = [
    "core",
    "pages",
    "leads",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.sitemaps",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "core.middleware.HealthCheckMiddleware",
    # Outermost after the health check, so it sees every response (core/cache.py)
    "core.middleware.PrivateByDefaultMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serves the collected, hashed static files in production (and with runserver_nostatic)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # ETags, so browsers revalidating a cached page get a short 304 instead of the whole page
    "django.middleware.http.ConditionalGetMiddleware",
    # Fills {solo.price}-style placeholders in served pages; after ConditionalGet so ETags see the prices
    "core.middleware.PackagePriceMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "dbc.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "core.context_processors.indexing",
            ],
        },
    },
]

WSGI_APPLICATION = "dbc.wsgi.application"


# Database: DATABASE_URL (Postgres on Render), falling back to a local SQLite file.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Internationalisation
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Amsterdam"
USE_I18N = True
USE_TZ = True


# Static files: source assets live in static/, collectstatic writes to staticfiles/.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"

# Files served at the site root, such as /favicon.ico
WHITENOISE_ROOT = BASE_DIR / "public"

# Host names search engines may index (robots.txt and <meta name="robots">). Everything else is noindex.
INDEXABLE_HOSTS = [
    host.strip()
    for host in os.environ.get("INDEXABLE_HOSTS", "designbycommitt.ee,www.designbycommitt.ee").split(",")
    if host.strip()
]

# IndexNow (core/indexnow.py): tell search engines when pages change. On in production only. INDEXNOW_KEY is
# optional: without it the key is derived from SECRET_KEY (changing SECRET_KEY changes the key, which is fine).
INDEXNOW_ENABLED = False
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")

# Uploaded images and documents. On Render this points at the persistent disk.
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
MEDIA_URL = "/media/"

STORAGES = {
    # Image renditions get a content hash in their file names, so they can be cached for a year (core/storage.py)
    "default": {"BACKEND": "core.storage.HashedRenditionStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Complex StreamField pages can exceed Django's default of 1000 fields per form in the page editor.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000


# Wagtail
WAGTAIL_SITE_NAME = "Design by Committee"

WAGTAILSEARCH_BACKENDS = {
    "default": {"BACKEND": "wagtail.search.backends.database"},
}

# Full base URL of the site, used for links in admin notification emails. No trailing slash.
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "http://localhost:8000")

WAGTAILDOCS_EXTENSIONS = ["csv", "docx", "key", "odt", "pdf", "pptx", "rtf", "txt", "xlsx", "zip"]
# SVG is allowed for logos (testimonials). SVGs can contain scripts, so only give trusted editors image upload rights.
WAGTAILIMAGES_EXTENSIONS = ["avif", "gif", "jpg", "jpeg", "png", "webp", "svg"]

WAGTAILDOCS_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


# Email: console output unless overridden by an environment's settings.
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Design by Committee <forms@designbycommitt.ee>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# Lead notification emails are sent after the visitor gets their reply (leads/views.py send_in_background)
LEAD_EMAILS_IN_BACKGROUND = True


# Edge caching (core/cache.py). With RENDER_API_KEY set, the site purges Render's edge cache when content changes.
# RENDER_SERVICE_ID is set by Render. EDGE_HTML_MAX_AGE overrides how long the edge keeps pages, in seconds.
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID", "")
EDGE_HTML_MAX_AGE = int(os.environ["EDGE_HTML_MAX_AGE"]) if os.environ.get("EDGE_HTML_MAX_AGE") else None
