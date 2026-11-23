# Relaunch designbycommitt.ee on Wagtail

Status: **approved 2026-11-23** · Phases 0–7 done (staging: https://designbycommittee.onrender.com), Phase 8 next

This plan moves the site from static HTML on Netlify to Wagtail CMS on Render. It keeps the current
design, URLs and form behaviour, and makes every section editable in the Wagtail admin. Claude does the
work in this repo. Your part is limited to the steps marked **You**, collected in
[Your checklist](#your-checklist) at the end.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| CMS | **Wagtail 7.4 LTS** on **Django 5.2 LTS**, Python 3.13 | 7.4 has security support until Nov 2027. Wagtail 8.0 isn't an LTS release. |
| Hosting | **Render**, Frankfurt region: web service `0.5c-512mb`, Postgres `0.1c-256mb`, 1 GB disk for uploads | Fixed monthly price, the whole setup lives in a `render.yaml` file in the repo, and pushes deploy automatically like Netlify does now. EU region for an EU audience. |
| Editing | **Rearrangeable sections.** Pages are built from StreamField blocks that match the current design. | You can edit, reorder, add or remove sections and build new landing pages from the same blocks. |
| Forms | **Saved in the Wagtail admin and emailed to you** through **Resend** (free tier: 3,000 emails/month) | Leads show up in your inbox and stay listed in the admin, with CSV export. |
| DNS | **Stays on Netlify DNS.** Only the website records change. | No nameserver move, and your email (MX/SPF) records aren't touched. |
| Repo | Same repo and branch flow. Build on this branch; `main` keeps the static site until cutover. | Netlify keeps serving the current site until the DNS switch, so it's the rollback path. |
| Local dev | `uv` with SQLite locally, Postgres on Render | No database server to install. A staging check against Postgres runs before launch. |

Estimated running cost: about **$13–14 per month** (web $7, Postgres about $6, disk about $0.25). Resend's free tier
covers the forms. Claude checks current prices at signup and tells you before anything is billed.

## Target architecture

```
designbycommittee/
├── manage.py
├── pyproject.toml, uv.lock, requirements.txt   # requirements.txt is exported from uv.lock for Render
├── render.yaml                                 # Render Blueprint: web service, Postgres, disk, env vars
├── netlify.toml                                # build ignore, so Netlify stops building (see Phase 0)
├── dbc/                                        # Django project
│   ├── settings/{base,dev,production}.py       # env-based config: DATABASE_URL, SECRET_KEY, email
│   └── urls.py                                 # Wagtail, sitemap.xml, robots.txt, favicon, media
├── core/          # base templates, header/footer, SiteSettings, Testimonial snippet, template tags
├── pages/         # LandingPage model + StreamField blocks + block templates
├── leads/         # Django forms for the 2 forms, FormSubmission model, admin viewset, email notify
├── static/        # current css/, js/, img/ moved here unchanged (paths via {% static %})
├── templates/     # base.html, includes, block templates
└── docs/          # this plan, editor guide
```

### Page model

Two page types share a base with the SEO and social-sharing fields:

- **`HomePage`** (`/`, one only): the original agency design. Its blocks render as columns of the home page's
  12-column grid, which can't be mixed with full-width sections.
- **`LandingPage`** (`/comedy/` and future landing pages, under the home page): full-width section blocks
  (`comedy.css`), plus optional header links and a header button.
- Promote tab: SEO title, meta description, social title/description/image (`og:*`); canonical URL generated per page

(Changed during Phase 2 from one page type with a theme switch: the two designs' blocks don't work inside each
other's layouts, so separate page types stop editors from combining them.)

Site-wide **SiteSettings** hold the footer company name, the lead notification email and default social image.
The copyright year updates by itself (today it's hard-coded "© 2026").

### Section blocks (from the two existing pages)

Each block gets an optional **anchor id** (so `#packages`, `#quote` and `#fringe` keep working) and, where the
design has it, a **background** choice (light / paper / dark). Block templates reuse the current markup and
class names, so the existing CSS works unchanged.

| Block | Used for |
|---|---|
| Agency hero | Home: headline, animated moped illustration, lead, CTA |
| Screenshot hero | Comedy: headline, lead, two buttons, proof line, browser-framed screenshot + optional editor mockup |
| Illustrated feature rows | Home: "Gain Visitor Insights" / "Devise Winning Strategies" / "Maximize Return on Ad Spend" (illustration left/right) |
| Colour cards | Comedy: "Who we build for", "Recent work" (pink/teal/blue) |
| Columns | Comedy: "Why work with Committee" |
| Timeline + checklist panel | Comedy: Fringe section |
| Numbered steps | Comedy: "How it works" |
| Pricing packages | Comedy: Solo / Show / Venue, featured flag, badge, "from" prefix, CTA that preselects the package |
| Testimonial carousel / quote card | Home carousel, comedy quote. Both use **Testimonial snippets**, so a quote is written once and reused. |
| FAQ | Comedy: `<details>` list |
| Lead form | Either form, with editable heading, intro, button label and thank-you text |
| Rich text | General use for new pages |

## Phases

Each phase ends with a commit on this branch and a check Claude runs before moving on. Claude reports at the end
of each phase. Only Phases 6 and 8 need you.

### Phase 0: Protect the live site *(Claude)*

1. Add `netlify.toml` with `[build] ignore = "exit 0"` on this branch. Netlify then skips Deploy Previews for it,
   so Python source files are never published as a static preview. After the merge in Phase 8, Netlify also stops
   rebuilding `main` and keeps serving the last static deploy until DNS moves.
2. Push the branch and open a **draft PR** so progress is visible.

**Check:** the PR's Netlify check shows "skipped", not a deploy.

### Phase 1: Local development environment *(Claude)*

1. `brew install uv`. Create the project with Wagtail 7.4 / Django 5.2 pinned (`uv add "wagtail>=7.4,<7.5" "django>=5.2,<5.3"`),
   plus `dj-database-url`, `whitenoise`, `gunicorn`, `psycopg[binary]`.
2. Split settings (`dev` / `production`). In dev: SQLite, `DEBUG=True`, console email backend, media in `./media`.
   Secrets come from a gitignored `.env`, and `.gitignore` gains Python, `media/`, `.env` and `db.sqlite3` entries.
3. Create a **local test admin** with generated credentials stored only in `.env` (not committed, not shown in chat).
4. Add `.claude/launch.json` so the dev server can be previewed in the app's browser pane.
5. Rewrite `README.md`: setup (`uv sync`, `uv run manage.py migrate`, `uv run manage.py runserver`), project layout, deploy flow.

**Check:** `runserver` serves the Wagtail welcome page, `/admin/` logs in, `manage.py check --deploy` passes on production settings.

### Phase 2: Models, blocks and snippets *(Claude)*

1. `LandingPage`, `SiteSettings` and the `Testimonial` snippet, with migrations.
2. All blocks from the table above, with admin labels, help text and icons. Limit the root page to `LandingPage` children.
3. Enable SVG uploads in Wagtail images (the testimonial logos are SVGs).
4. Turn on `wagtail.contrib.redirects`, `wagtail.contrib.sitemaps` and `wagtail.contrib.settings`. Leave Django's own admin off.

**Check:** every block can be added, edited and reordered in the admin without errors. The model tests pass.

### Phase 3: Templates *(Claude)*

1. `base.html`: `<head>` with title, meta description, canonical, OG tags, fonts, theme CSS (`small.css`,
   `medium.css` with its media query, `comedy.css`), and the tiny-slider/flatpickr CDN tags with their SRI hashes as they are today.
2. Header (logo SVG as an include, optional nav + CTA), skip link, footer.
3. One template per block, ported from the current HTML. The bespoke pieces (moped animation, duplicated
   responsive illustrations, editor mockup) stay in the block templates, so editors only see content fields.
4. Move `css/`, `js/`, `img/` into `static/`. Serve them through WhiteNoise with hashed, compressed, long-cached
   filenames. Decorative illustrations stay static files. Content images (screenshot, testimonial logos) become Wagtail images.
5. `/sitemap.xml` (Wagtail sitemap, with HTTPS URLs; the current file still lists the home page as `http://`),
   `/robots.txt` (now pointing to the sitemap), `/favicon.ico`, plus a redirect from `/index.html` to `/`.

### Phase 4: Forms *(Claude)*

1. Django forms that match today's fields exactly:
   - **Landing page assessment**: URL, 8 factor checkboxes, details; name, email, date, time, timezone
   - **Comedy enquiry**: name, email, client type (radio), package, deadline, link, details
2. A `POST /leads/<form>/` endpoint with CSRF protection, the existing honeypot field, and server-side validation that
   mirrors the JS rules. It returns JSON for the current `fetch` flow and redirects with a thank-you message when JS is off.
3. Small JS changes: post to the new endpoint, send the CSRF token. Keep the multi-step flow, flatpickr, package preselect,
   focus handling and error messages as they are.
4. A `FormSubmission` model (form, page, data, timestamp) listed in the Wagtail admin under **Leads**, with
   filters and CSV/XLSX export.
5. An email to the address in SiteSettings for each submission (sent through Resend in production), with reply-to set
   to the person who submitted. If the email fails, the submission is still saved.

**Check:** tests cover valid and invalid submissions, the honeypot, saving, and email (Django's test mail outbox).
Manual run in the browser pane: both forms submit and the thank-you states appear.

### Phase 5: Content import and visual parity *(Claude)*

1. An idempotent `manage.py import_current_site` command creates the site, both pages, the testimonials, settings
   and images with today's exact copy. Local, staging and production all start from the same content.
2. **Parity check:** serve the current static site from `main` (`python3 -m http.server`) next to the Wagtail
   dev server. Screenshot both pages at 375, 768 and 1280 px and compare them. Diff the visible text and the `<head>` tags.
   Fix any difference that isn't deliberate (sitemap scheme, dynamic year).
3. Accessibility and performance spot check: skip links, focus order, form errors announced, reduced motion. Lighthouse
   scores should be the same as or better than the current site.

**Check:** no visible differences. Claude sends you side-by-side screenshots.

### Phase 6: Staging on Render *(You: about 15 minutes; Claude: everything else)*

Claude first:
1. Writes `render.yaml`:
   - **Web service:** Python 3.13 (from `.python-version`), region Frankfurt, plan `0.5c-512mb`, branch = this branch
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Pre-deploy: `python manage.py migrate --noinput`
   - Start: `import_current_site --initial` (a no-op once the site has content; the disk isn't available earlier), then `gunicorn`; health check at `/healthz/`
   - 1 GB disk at `/opt/render/project/src/storage` for uploaded images and documents (served by the app with cache headers; can
     move to object storage later if traffic grows)
   - Env vars: `DATABASE_URL` from the database, `SECRET_KEY` generated, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`,
     and `RESEND_API_KEY` left for you to fill in
   - **Postgres:** `0.1c-256mb`, version 17, Frankfurt
2. Validates the Blueprint and gives you the exact clicks for the steps below.

**You:**
1. Sign up at render.com, connect GitHub (grant access to this repo only), and add a payment method.
2. **New → Blueprint** and select this repo and branch. Review the monthly cost Render shows, then approve.
3. Sign up at resend.com, add the domain `designbycommitt.ee`, create an API key and paste it into the `RESEND_API_KEY`
   env var on Render. (Claude may not handle API keys or passwords.)
4. Add Resend's DNS records (DKIM/SPF on a `send.` subdomain; your existing email records stay as they are)
   in Netlify DNS. Or, if you prefer, approve Claude making these record changes through Netlify for you.
5. Run `render login` in the terminal when Claude asks, so Claude can read logs and trigger deploys.
6. Create your own admin account: in Render's **Shell** tab run `python manage.py createsuperuser` and choose your password.

Then Claude:
- Confirms the start command imported the content on staging, and repeats the parity, form and email checks on the `*.onrender.com` URL,
  this time against Postgres.
- Confirms what backups Render takes of the database and the disk, and writes the restore steps in the README.
- Adds `noindex` on the staging hostname so search engines don't index it.

### Phase 7: Review and editor guide *(You review; Claude writes)*

1. Claude writes `docs/editing.md`: how to edit a section, add a page from blocks, manage testimonials, find leads,
   and change the notification email.
2. **You** spend about 30 minutes on staging: edit something, add a test section, submit both forms, and send Claude a list of changes.
3. Claude fixes the list. The comedy page's prices (€495, €795, from €1,950) and the "reply within one working day"
   promise were confirmed on 23 Nov.

### Phase 8: Cutover *(Claude, with your go-ahead at each outward step)*

1. **Before the switch:** Claude lists every record in the zone so nothing else changes. (The past Netlify form
   submissions aren't needed, so they aren't exported; you decided this on 23 Nov.) The apex and `www` records
   already have a 2-minute TTL (checked 23 Nov), so no TTL change is needed.
2. **Merge** the PR to `main` (your go-ahead). Netlify skips the build because of `netlify.toml`, so the old site stays up.
   Claude switches the Render service to the `main` branch and confirms it deployed.
3. Add `designbycommitt.ee` and `www.designbycommitt.ee` as custom domains on Render. www redirects to the apex,
   matching today's canonical URLs.
4. **DNS switch** (your go-ahead): in Netlify DNS, remove the Netlify-type records for the apex and `www`, add the apex
   `A` record and the `www` `CNAME` that Render gives. MX, SPF and other records stay as they are.
5. Verify: HTTPS certificate issued, both pages render, `/sitemap.xml` and `/robots.txt` load, both forms submit and email
   you, admin login works, Render logs are clean.
6. **Rollback** if needed: put the two DNS records back and the static Netlify site is live again within minutes.
   The Netlify site stays in place for two weeks for this reason.

### Phase 9: After launch *(Claude, with your OK where noted)*

1. Watch Render logs and form email delivery for 48 hours.
2. **You** (only if you use Google Search Console): resubmit `/sitemap.xml`.
3. After two weeks without problems, remove the custom domain from the Netlify site and, with your confirmation, delete
   the Netlify **site**. The **DNS zone stays**. Deleting the site also deletes its stored form submissions (not needed).
4. Raise the DNS TTL back to normal. Update the README to describe the Render-only deploy flow.
5. ~~Add a CI workflow~~ (done before launch: `.github/workflows/tests.yml` runs the tests, a migrations check, Django's
   deploy checks and a `requirements.txt`/`uv.lock` sync check). Enable Dependabot for Python packages.
   Before Wagtail 7.4's support ends in Nov 2027, upgrade to the next LTS.

## Your checklist

| When | What | Time |
|---|---|---|
| Now | Approve this plan | – |
| Phase 5 | Look over the side-by-side screenshots | 5 min |
| Phase 6 | Sign up for Render, connect GitHub, add a payment method, create the Blueprint | 10 min |
| Phase 6 | Sign up for Resend, add the domain, paste the API key into Render, add its DNS records (or let Claude) | 10 min |
| Phase 6 | `render login`; create your admin account in Render's shell | 3 min |
| Phase 7 | Review staging, send a list of changes, confirm comedy prices (done) | 30 min |
| Phase 8 | Go-ahead to merge, and go-ahead to change the 2 website DNS records | 2 min |
| Phase 9 | Confirm deleting the Netlify site after two weeks | 1 min |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| The design changes during the port | The templates keep the existing markup and CSS. Phase 5 compares screenshots at three widths before staging. |
| Leads lost during the switch | New submissions are saved even if the email fails. Forms are tested on staging and again after the DNS switch. |
| Email for the domain breaks | Only the apex/www website records and Resend's `send.` subdomain records change. Claude lists the zone before and after to confirm. |
| Downtime at cutover | A low TTL set the day before, the Render domains added before the DNS change, and the old site kept running as a rollback. |
| Python source exposed through a Netlify preview | `netlify.toml` build ignore is added in Phase 0, before any Python code is pushed. |
| Uploaded media lost | Render disk, with backup coverage confirmed in Phase 6 and a documented restore. The images that ship with the site can be recreated by `import_current_site`. |
