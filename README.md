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
| `dbc/urls.py` | Admin at `/admin/`, `/sitemap.xml`, `/healthz/` health check, then Wagtail pages |
| `core/` | Site settings (company name, lead email, default social image), Testimonial snippets, rich text styles, robots.txt, media serving |
| `pages/` | `HomePage` (agency design, grid blocks) and `LandingPage` (section blocks, e.g. /comedy/), blocks in `blocks.py`, the `import_current_site` command |
| `leads/` | The two lead forms, `FormSubmission` (admin: **Leads**, with CSV/XLSX export), notification emails |
| `templates/` | `base.html`, page templates, one template per block in `blocks/agency/` and `blocks/sections/` |
| `static/` | CSS, JS and images (collected to `staticfiles/` and served by WhiteNoise in production) |
| `public/` | Files served at the site root (`/favicon.ico`) |

## Forms

Both forms post back to their own page (`BasePage.serve` → `leads/views.py`). Each submission is saved under
**Leads** in the admin and emailed to the address in **Settings → Site settings** (through Resend in production;
printed to the terminal locally). A hidden honeypot field catches simple spam bots.

## Editing content from the command line

Page content can be read and changed without the admin, through Wagtail's own APIs, so every change is validated
like the page editor does it and saved as a normal revision (shown in the page's **History**, revertible there).
Claude uses this over SSH; you can too.

```bash
ops/remote-manage.sh show_page
```

```bash
ops/remote-manage.sh show_page /comedy/
```

```bash
ops/remote-manage.sh edit_page /comedy/ - < changes.json
```

- `show_page` lists the pages, or prints one page's fields and blocks (with block ids) as JSON.
- `edit_page` takes a JSON list of operations (`set_field`, `set`, `insert`, `remove`, `move`; the format is
  described at the top of `pages/content_ops.py`). On its own it's a **dry run**: it validates the changes and prints
  a diff. Add `--draft` to save a draft for review in the admin, or `--publish` to publish.
- Revisions are recorded under a `claude` user that can't sign in. `--publish` refuses when someone else has an
  unpublished draft on the page, because it would publish that too.
- Locally, run the same commands with `uv run manage.py …`.
- `ops/remote-manage.sh` needs an SSH key on your Render account. The Render host key is pinned in
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

## Deploys

Until cutover, Netlify deploys `main` (the static site). This branch carries a `netlify.toml` whose build `ignore`
command stops Netlify building it, so the Python source is never published as a static site. After the merge it also
stops rebuilding `main`, and Netlify keeps serving the last static deploy until DNS points at Render.

Render deployment (`render.yaml`) is added in Phase 6 of the plan.
