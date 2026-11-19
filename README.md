# Design by Committee

Static HTML site. No build step, no dependencies.

## Structure

- `index.html` — the site (single page; includes the Netlify form)
- `css/`, `js/`, `img/` — assets
- `robots.txt`, `sitemap.xml`, `favicon.ico`

## Local preview

Open `index.html` directly, or serve the folder so paths behave like production:

```bash
python3 -m http.server 8000
```

Netlify Forms only work on the deployed site, not locally.

## Deploys

Netlify project `design-by-committee` deploys from
`git@github.com:design-by-committee/designbycommittee.git`:

- Push to `main` → production deploy to https://designbycommitt.ee
- Pull requests against `main` → Deploy Preview
- Other branches are not deployed (branch deploys are off)
- Base and publish directory are the repo root (`/`); there is no build command
- Netlify Forms is enabled (used by the form in `index.html`)

## Workflow

1. Branch off `main`
2. Make changes and preview locally
3. Open a PR against `main` and check its Netlify Deploy Preview
4. Merge to `main` to ship

When more pages are added, add them to `sitemap.xml`. If a build step or
generator is introduced later, add a `netlify.toml` with the build command and
publish directory and update this README.
