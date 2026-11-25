# Design by Committee

The designbycommitt.ee website, being relaunched on [Wagtail CMS](https://wagtail.org/) (Wagtail 7.4 LTS on
Django 5.2 LTS, Python 3.13). The plan, decisions and progress are in
[docs/wagtail-relaunch-plan.md](docs/wagtail-relaunch-plan.md).

> **Transition period:** `main` still holds the static site, which Netlify serves at https://designbycommitt.ee.
> The Wagtail project lives on the relaunch branch until cutover (plan, Phase 8). The original HTML is now in
> `templates/` (markup) and `pages/management/commands/import_current_site.py` (copy).

## Local development

Requirements: Python 3.13 and [uv](https://docs.astral.sh/uv/). There's no database server to install: locally the site
uses SQLite (`db.sqlite3`). To use Postgres instead, set `DATABASE_URL` in `.env`.

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

- Site: http://localhost:8000/
- Admin: http://localhost:8000/admin/ (sign in with the local admin account from `.env`)
- Form emails print to the terminal instead of being sent.

`.claude/launch.json` defines the same server for the Claude app's browser pane (`wagtail`).

### Useful commands

| Command | What it does |
|---|---|
| `uv run manage.py makemigrations` | Create migrations after changing models |
| `uv run manage.py test` | Run the tests |
| `uv add <package>` | Add a dependency (then `uv export --no-dev --no-hashes -o requirements.txt` for Render) |
| `DJANGO_SETTINGS_MODULE=dbc.settings.production SECRET_KEY=x uv run manage.py check --deploy` | Check production settings |

## Project layout

| Path | What's in it |
|---|---|
| `dbc/settings/` | `base.py` (shared), `dev.py` (local, loads `.env`), `production.py` (Render, all config from env vars) |
| `dbc/urls.py` | Admin at `/admin/`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/healthz/` health check, then Wagtail pages |
| `core/` | Site settings (company name, lead email, default social image, the organisation for search engines and AI, footer), Testimonial snippets, rich text styles, robots.txt, llms.txt, media serving |
| `pages/` | `HomePage` (agency design, grid blocks) and `LandingPage` (section blocks, e.g. /comedy/), `Package` snippets, blocks in `blocks.py`, schema.org JSON-LD in `structured_data.py`, the `import_current_site` command |
| `leads/` | The two lead forms, `FormSubmission` (admin: **Leads**, with CSV/XLSX export), notification emails |
| `templates/` | `base.html`, page templates, one template per block in `blocks/agency/` and `blocks/sections/` |
| `static/` | CSS, JS and images (collected to `staticfiles/` and served by WhiteNoise in production) |
| `public/` | Files served at the site root (`/favicon.ico`) |

## Forms

Both forms post back to their own page (`BasePage.serve` → `leads/views.py`). Each submission is saved under
**Leads** in the admin and emailed to the address in **Settings → Site settings** (through Resend in production;
printed to the terminal locally).

Spam is handled without anything visitors have to do:

- A hidden honeypot field: anything that fills it in is dropped.
- `leads/spam.py` flags the rest: no `fill-time` from the page's script (seconds since the page opened) or under 3
  seconds; HTML or more than two links in an answer; anything the form itself rejects as impossible
  (`LeadForm.spam_reasons`, e.g. an assessment call outside weekdays 09:00–18:00 in the next two weeks, or the same
  first and last name); more than 5 sends an hour from one IP address. Flagged submissions get the normal success
  response but are saved with `is_spam` under **Leads → Spam**, with no email. Only a keyed hash of the IP address is
  stored, for the rate limit. `cms leads list --spam` lists them.

The forms have no CSRF token, so the pages they're on can be cached (see Caching). Instead, a submission is only
accepted if the browser's `Origin` (or `Referer`) header is this site, which another site can't fake.

## Caching

Everything visitors load can be cached by browsers and by Render's edge cache (Cloudflare, in front of the service):

| What | Cache-Control | How changes show up |
|---|---|---|
| Static files (`/static/`) | 1 year, immutable | WhiteNoise puts a content hash in each file name; a deploy changes the names |
| Image renditions (`/media/images/`) | 1 year, immutable | `core/storage.py` puts a content hash in each file name; a changed image gets new URLs |
| Other media (original images, documents) | 1 hour | |
| Pages, `sitemap.xml`, `robots.txt` | edge: `s-maxage` (5 min, or 1 day with purging); browsers: `max-age=0` | Browsers revalidate on every visit (a quick 304 thanks to ETags), so they see whatever the edge has |
| Everything else (admin, previews, form responses, logged-in visitors, URLs with `?query`) | `private, no-cache` | Never stored at the edge |

**Purging.** With `RENDER_API_KEY` set, the site asks Render to purge the whole edge cache whenever something that
appears on pages changes: publishing, unpublishing, moving or deleting a page, and saving testimonials, Site
settings, images, redirects or sites. That's why pages can stay cached for a day. Drafts and `cms` dry runs don't
purge. Without the key, pages are cached for 5 minutes, so an edit is live within 5 minutes. Every deploy also
purges the edge cache, and there's a manual **Purge cache** button under the service's Settings in Render.

**Render settings.** Edge caching is a dashboard setting (Settings → Edge Caching): **All files** caches pages as well
as images, CSS and JS; **Common static files** caches only images, CSS and JS. Check a response's `CF-Cache-Status`
header: `HIT` came from the edge, `MISS`/`EXPIRED` from the service, `BYPASS`/`DYNAMIC` isn't cached.

`python manage.py hash_renditions` (run at startup by `render.yaml`) replaces renditions from before hashed names
existed; it does nothing once they're all hashed.

## Page speed

Pages load nothing from other sites: a new connection to another host holds up the first paint on phones.
`pages/tests.py` (`PageSpeedTests`) checks this.

- **Fonts.** Khula is in `static/fonts/` (SIL Open Font License, `OFL.txt`). `small.css` has the `@font-face` rules
  and `base.html` preloads the latin files. To add a weight, download its woff2 files from Google Fonts and add
  matching rules.
- **No libraries.** The testimonial carousel is CSS scroll snap plus a few lines in `main.js` for the dots. The
  assessment form uses the browser's own date and time fields (dates are sent as `YYYY-MM-DD`).
- **Images.** Screenshots use `{% srcset_image ... format-webp sizes=... %}` so phones get smaller WebP files. Write
  `sizes` media queries as `(min-width: 48em)`: Wagtail's tag parser can't handle the `=` in `(width >= 48em)`. Logos
  use `format-webp preserve-svg`, which converts raster logos and leaves SVGs alone. Keep static PNGs small (256
  colours is usually enough for the illustrations).

## Managing the site from the command line

`python manage.py cms` does what an editor or administrator does in the Wagtail admin, through Wagtail's own APIs
and admin forms, so changes are validated the same way and appear in page **History** and **Reports → Site history**
under "Claude (command line)" (a `claude` user that can't sign in). Claude uses it over SSH; you can too.

```bash
ops/remote-manage.sh cms pages list
```

| Area | Actions |
|---|---|
| `pages` | `list`, `show`, `edit` (content operations, see `pages/content_ops.py`), `create`, `publish`, `unpublish`, `delete`, `move`, `copy`, `revisions`, `revert`, `lock`, `unlock`, `references` |
| `snippets` | `types`, then `list`/`show`/`create`/`update`/`delete <type>`, e.g. `testimonial` |
| `settings` | `list`, `show sitesettings`, `update sitesettings` |
| `images`, `documents` | `list`, `show`, `upload --file PATH` (or `--file - --filename x.jpg` from stdin), `update`, `delete` |
| `leads` | `list` (`--unhandled`, `--form`, `--since`), `show`, `update` (`{"handled": true}`), `delete`, `export` (CSV) |
| `redirects`, `sites` | `list`, `show`, `create`, `update` (and `delete` for redirects) |
| `users` | `list`, `show`, `create`, `update` (profile, active, superuser, groups), `delete`, `groups` |

Safety rules built in:

- **Dry run by default.** Changes run inside a transaction that's rolled back, so every error a real run would hit
  shows up, and nothing is saved until you add `--apply` (pages: `--draft` or `--publish`).
- Data is JSON: `--data '{"role": "Founder"}'` or `--data-file changes.json` (`-` for stdin). Updates only change the
  fields you give.
- Deleting anything that's used elsewhere (a testimonial on a page, an image, a linked page) needs `--force`.
- The home page can't be deleted, unpublished or moved. The last active superuser can't be demoted, deactivated or
  deleted. `pages edit --publish` won't publish someone else's unpublished draft.
- **Passwords are never set or shown.** New users get no password and set one with "Forgot password?".

Run `python manage.py cms <area> --help` for details. Locally use `uv run manage.py cms …`.
`ops/remote-manage.sh` needs an SSH key on your Render account; the Render host key is pinned in
`ops/render_known_hosts`.

## Comparing with the original static site

To check that a template change still matches the original design, extract the original site and serve it next to
the Wagtail server (the `.original-site/` folder is gitignored):

```bash
mkdir -p .original-site && git archive d6ab64d | tar -x -C .original-site
```

Then start `original-static-site` (port 8001) from `.claude/launch.json` alongside `wagtail` (port 8000).

## Configuration (environment variables)

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | Render (from the database) | Postgres connection. Defaults to local SQLite. |
| `SECRET_KEY` | Render (generated) | Django secret key, required in production |
| `ALLOWED_HOSTS` | Render | Comma-separated host names, e.g. `designbycommitt.ee,www.designbycommitt.ee` |
| `MEDIA_ROOT` | Render | Upload folder on the persistent disk |
| `WAGTAILADMIN_BASE_URL` | Render | Full site URL for links in admin emails |
| `RESEND_API_KEY` | Render (entered by the site owner) | Sends form notification emails through Resend |
| `INDEXABLE_HOSTS` | optional | Hosts search engines may index. Default `designbycommitt.ee,www.designbycommitt.ee`; everything else gets `noindex` |
| `DEFAULT_FROM_EMAIL` | optional | Sender address for form emails |
| `RENDER_API_KEY` | Render (entered by the site owner, optional) | Lets the site purge Render's edge cache when content changes (see Caching) |
| `RENDER_SERVICE_ID` | Render (automatic) | The service whose edge cache is purged |
| `EDGE_HTML_MAX_AGE` | optional | Seconds the edge keeps pages. Default 300, or 86400 with `RENDER_API_KEY` |

## Deploys

Until cutover, Netlify deploys `main` (the static site). This branch carries a `netlify.toml` whose build `ignore`
command stops Netlify building it, so the Python source is never published as a static site. After the merge it also
stops rebuilding `main`, and Netlify keeps serving the last static deploy until DNS points at Render.

Render deployment (`render.yaml`) is added in Phase 6 of the plan.
