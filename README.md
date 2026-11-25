# Design by Committee

The https://designbycommitt.ee website: [Wagtail CMS](https://wagtail.org/) 7.4 LTS on Django 5.2 LTS, Python 3.13,
hosted on [Render](https://render.com/) (Frankfurt). Every page is built from sections editors can change in the
Wagtail admin; how to do that is in [docs/editing.md](docs/editing.md). SEO status and open to-dos are in
[docs/seo.md](docs/seo.md).

## Local development

Requirements: Python 3.13 and [uv](https://docs.astral.sh/uv/). Locally the site uses SQLite (`db.sqlite3`), so
there's no database server to install. To use Postgres instead, set `DATABASE_URL` in `.env`.

```bash
uv sync
```

```bash
cp .env.example .env    # then set LOCAL_ADMIN_PASSWORD to a password of your choice
```

```bash
uv run manage.py migrate
```

```bash
set -a; . ./.env; set +a; DJANGO_SUPERUSER_PASSWORD="$LOCAL_ADMIN_PASSWORD" uv run manage.py createsuperuser --noinput --username "$LOCAL_ADMIN_USERNAME" --email admin@localhost
```

```bash
uv run manage.py import_current_site --hostname localhost --port 8000
```

```bash
uv run manage.py runserver
```

- Site: http://localhost:8000/ and admin: http://localhost:8000/admin/ (the local admin account from `.env`).
- Form emails print to the terminal instead of being sent.
- `.claude/launch.json` defines the same server (`wagtail`) for the Claude app's browser pane.
- `import_current_site` creates the home and `/comedy/` pages, testimonials, packages, images and settings from the
  seed copy in `pages/management/commands/import_current_site.py`. It isn't a copy of production: the other landing
  pages and later edits exist only in the live database. To see live content, use `cms … show` over SSH (below).

| Command | What it does |
|---|---|
| `uv run manage.py test` | Run the tests (about 2 minutes) |
| `uv run manage.py makemigrations` | Create migrations after changing models |
| `uv add <package>` | Add a dependency, then `uv export --no-dev --no-hashes -o requirements.txt` (Render installs from `requirements.txt`) |
| `DJANGO_SETTINGS_MODULE=dbc.settings.production SECRET_KEY=x uv run manage.py check --deploy` | Check production settings |

## Development to release

1. **Branch** from `main` (`claude/<topic>`), make the change, add or update tests, and check it in the browser
   pane (desktop and 375 px wide for anything visual).
2. **Pull request** to `main`. CI (`.github/workflows/tests.yml`) runs on every PR: the tests, a missing-migrations
   check, Django's deploy checks on production settings, and a check that `requirements.txt` matches `uv.lock`.
3. **Merge** once CI passes. Render auto-deploys every commit on `main`: `pip install` and `collectstatic`, then
   `migrate` before the switch, then the start command. Each deploy has a few seconds of downtime (the service has
   a disk, so Render stops the old instance first) and purges the edge cache. A commit message containing
   `[skip render]` doesn't deploy; for a docs-only PR, put it in the PR title (GitHub copies the title into the merge
   commit message).
4. **Verify** the change on https://designbycommitt.ee once the deploy is live.
5. **Tag** the release: `gh release create vX.Y.Z --target <merge commit> --title "vX.Y.Z: <summary>"` with a
   bullet list of changes and the PR link. Patch for fixes and small changes, minor for new features, sections or
   admin fields, major when existing content or admin structure changes (e.g. v2.0.0 moved packages into snippets).
   Content edits made in the admin, and docs-only changes, don't get a tag.

Migrations run before the new code starts, so a migration must work with the code that's still running until the
switch (add fields before using them; remove them a release later). Data migrations that move content run against
the live database: test them on a copy of real content first.

## Project layout

| Path | What's in it |
|---|---|
| `dbc/settings/` | `base.py` (shared), `dev.py` (local, loads `.env`), `production.py` (Render, config from env vars) |
| `dbc/urls.py` | `/admin/`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/media/`, then Wagtail pages; `/healthz/` is answered by `core/middleware.py` |
| `core/` | `SiteSettings` (company, lead email, pound rate, organisation for search engines and AI, footer), `Testimonial` snippet, caching (`cache.py`, `storage.py`, `middleware.py`), robots.txt, llms.txt, media serving, the `cms` and `hash_renditions` commands |
| `pages/` | `HomePage` (agency design, grid blocks) and `LandingPage` (full-width sections), the `Package`, `CaseStudy`, `Question` and `SharedSection` snippets, blocks (`blocks.py`), price placeholders (`prices.py`), JSON-LD (`structured_data.py`), `cms pages edit` operations (`content_ops.py`), the `import_current_site` command |
| `leads/` | The two lead forms, spam checks (`spam.py`), `FormSubmission` (admin: **Leads → Inbox / Spam**), notification emails |
| `templates/` | `base.html`, page templates, one template per block in `blocks/agency/` (home) and `blocks/sections/` (landing pages) |
| `static/` | CSS, JS, fonts and images (collected to `staticfiles/` and served by WhiteNoise) |
| `public/` | Files served at the site root (`/favicon.ico`) |
| `ops/` | `remote-manage.sh` (management commands on Render over SSH) and Render's pinned SSH host key |
| `render.yaml` | Render Blueprint: web service, Postgres, disk, env vars |

## How it works

### Forms

Both forms post back to their own page (`BasePage.serve` → `leads/views.py`). Each submission is saved under
**Leads** in the admin and emailed to the address in **Settings → Site settings** (through Resend in production,
after the visitor's response has been sent).

The forms have no CSRF token, so the pages they're on can be cached. Instead, a submission is only accepted if the
browser's `Origin` (or `Referer`) header is this site.

Spam is handled without anything visitors have to do. A hidden honeypot field drops bots outright; `leads/spam.py`
flags the rest: no `fill-time` from the page's script or under 3 seconds, HTML or more than two links in an answer,
anything the form rejects as impossible (`LeadForm.spam_reasons`), or more than 5 sends an hour from one IP address
(only a keyed hash of the address is stored). Flagged submissions get the normal thank-you response and are saved
under **Leads → Spam** without an email.

### Caching

| What | Cache-Control | How changes show up |
|---|---|---|
| Static files (`/static/`) | 1 year, immutable | WhiteNoise puts a content hash in each file name |
| Image renditions (`/media/images/`) | 1 year, immutable | `core/storage.py` puts a content hash in each file name |
| Other media (original images, documents) | 1 hour | |
| Pages, `sitemap.xml`, `robots.txt`, `llms.txt` | edge: `s-maxage` 5 min (1 day with purging); browsers: `max-age=0` | Browsers revalidate every visit (a 304 thanks to ETags) |
| Admin, previews, form responses, logged-in visitors, URLs with `?query` | `private, no-cache` | Never stored at the edge |

Render's edge cache (Cloudflare) follows these headers for what it stores, depending on **Settings → Edge Caching**
in the Render dashboard: **Common static files** caches only images, CSS and JS; **All files** caches pages too. A
response's `CF-Cache-Status` header shows what happened (`HIT`, `MISS`, or `DYNAMIC` for not cached).

With `RENDER_API_KEY` set, publishing or changing anything that appears on pages (pages, snippets, Site settings,
images, redirects) purges the whole edge cache through Render's API, so pages can be cached for a day. Drafts and
`cms` dry runs don't purge. Every deploy purges too, and the dashboard has a manual **Purge cache** button.

`hash_renditions` (run at startup) renames image renditions from before hashed names existed; it does nothing once
they're all hashed.

### Page speed

Pages load nothing from other hosts (`PageSpeedTests` in `pages/tests.py` checks this).

- **Fonts:** Khula is self-hosted in `static/fonts/` (SIL Open Font License); `small.css` has the `@font-face` rules
  and `base.html` preloads the latin files. To add a weight, download its woff2 files from Google Fonts.
- **No libraries:** the testimonial carousel is CSS scroll snap plus a few lines of `main.js`; the assessment form
  uses the browser's own date and time fields.
- **Images:** screenshots use `{% srcset_image ... format-webp sizes=... %}`. Write `sizes` media queries as
  `(min-width: 48em)`: Wagtail's tag parser can't handle the `=` in `(width >= 48em)`. Logos use
  `format-webp preserve-svg`. Keep static PNGs small (256 colours is usually enough for the illustrations).

### Price placeholders

`{solo.price}` and `{solo.pounds}` (any package code) in page copy, meta tags, structured data and `/llms.txt` are
filled in by `core.middleware.PackagePriceMiddleware` and `pages/prices.py`; the admin keeps the placeholder.

## Managing the live site from the command line

`python manage.py cms` does what an editor or administrator does in the Wagtail admin, through Wagtail's own APIs
and admin forms, so changes are validated the same way and appear in page **History** and **Reports → Site history**
as "Claude (command line)" (a `claude` user that can't sign in). Run it on Render over SSH:

```bash
ops/remote-manage.sh cms pages list
```

| Area | Actions |
|---|---|
| `pages` | `list`, `show`, `edit` (operations in `pages/content_ops.py`), `create`, `publish`, `unpublish`, `delete`, `move`, `copy`, `revisions`, `revert`, `lock`, `unlock`, `references` |
| `snippets` | `types`, then `list`/`show`/`create`/`update`/`delete <type>`, e.g. `package`, `testimonial` |
| `settings` | `list`, `show sitesettings`, `update sitesettings` |
| `images`, `documents` | `list`, `show`, `upload --file PATH` (or `--file - --filename x.jpg` from stdin), `update`, `delete` |
| `leads` | `list` (`--unhandled`, `--form`, `--since`, `--spam`), `show`, `update` (`{"handled": true}`), `delete`, `export` (CSV) |
| `redirects`, `sites` | `list`, `show`, `create`, `update` (and `delete` for redirects) |
| `users` | `list`, `show`, `create`, `update` (profile, active, superuser, groups), `delete`, `groups` |

- **Dry run by default:** changes run in a transaction that's rolled back, so every error a real run would hit shows
  up. Add `--apply` to save (pages: `--draft` or `--publish`).
- Data is JSON: `--data '{"role": "Founder"}'` or `--data-file changes.json` (`-` for stdin). Updates only change
  the fields given.
- Deleting anything used elsewhere needs `--force`. The home page can't be deleted, unpublished or moved; the last
  active superuser can't be demoted, deactivated or deleted; `pages edit --publish` won't publish someone else's
  unpublished draft.
- Passwords are never set or shown: new users set one with "Forgot password?".

`cms <area> --help` has the details; locally use `uv run manage.py cms …`. `ops/remote-manage.sh` needs an SSH key
on your Render account (Account Settings → SSH Public Keys).

## Hosting and configuration

| Piece | Where |
|---|---|
| Web service | Render `designbycommittee`, Frankfurt, `0.5c-512mb`, deploys `main` (`render.yaml`) |
| Database | Render Postgres 17 `designbycommittee-db`, `0.1c-256mb` |
| Uploads | 1 GB Render disk at `/opt/render/project/src/storage` (`MEDIA_ROOT`), served by the app |
| Email | Resend SMTP relay, sending from `forms@designbycommitt.ee` |
| DNS | Netlify DNS: apex `A 216.24.57.1`, `www CNAME designbycommittee.onrender.com` (www redirects to the apex). Mail records are separate and untouched |

| Variable | Set by | Purpose |
|---|---|---|
| `DATABASE_URL` | Render (from the database) | Postgres connection. Defaults to local SQLite |
| `SECRET_KEY` | Render (generated) | Django secret key, required in production |
| `ALLOWED_HOSTS` | `render.yaml` | Host names; the service's `*.onrender.com` host is added automatically |
| `MEDIA_ROOT` | `render.yaml` | Upload folder on the disk |
| `DEFAULT_FROM_EMAIL` | `render.yaml` | Sender address for form emails |
| `RESEND_API_KEY` | Render dashboard | Sends form notification emails through Resend |
| `RENDER_API_KEY` | Render dashboard (optional) | Lets the site purge the edge cache when content changes |
| `RENDER_SERVICE_ID`, `RENDER_EXTERNAL_HOSTNAME`, `RENDER_EXTERNAL_URL` | Render (automatic) | Service to purge; extra allowed host; fallback admin URL |
| `WAGTAILADMIN_BASE_URL` | `render.yaml` | Site URL for links in admin emails (falls back to `RENDER_EXTERNAL_URL`) |
| `INDEXABLE_HOSTS` | optional | Hosts search engines may index (default `designbycommitt.ee,www.designbycommitt.ee`); others get `noindex` |
| `EDGE_HTML_MAX_AGE` | optional | Seconds the edge keeps pages (default 300, or 86400 with `RENDER_API_KEY`) |
| `SECURE_HSTS_SECONDS` | optional | HSTS max-age (default 1 day) |

## Open items

- **Netlify leftovers** (the static site before 23 Nov 2026): after two problem-free weeks (from 7 Dec 2026), remove
  the custom domain from the Netlify site and delete the site (keep the DNS zone), then delete `netlify.toml`, whose
  only job is stopping Netlify from building `main`. Until then, the rollback is to delete the two DNS records above
  and re-add the domain on the Netlify site.
- **Edge caching:** on 25 Nov 2026 static files were edge-cached (`HIT`) but pages weren't
  (`CF-Cache-Status: DYNAMIC`), and `RENDER_API_KEY` wasn't set (`s-maxage=300`). To cache pages, check Edge Caching
  is **All files** and add a Render API key so edits purge the cache.
- **Backups:** confirm what Render keeps for Postgres and the disk, and write down the restore steps here.
- Raise `SECURE_HSTS_SECONDS` once the site has run on Render for a while; enable Dependabot for Python packages.
- Upgrade to the next Wagtail LTS before 7.4's support ends in November 2027.
