# GitHub Pages publishing

Production domain: https://line.kg/ (www redirects to the apex).
GitHub Pages source: `gh-pages` branch, `/` directory.

After editing the sources on `main`, publish with:

```sh
python3 tools/publish-pages.py
```

The command builds only public files and pushes them to `gh-pages`, preserving
that branch's history. GitHub's built-in Pages pipeline then publishes the site.
No DigitalOcean server or access token in the repository is needed.

The account's billing lock currently prevents custom GitHub Actions jobs from
starting. The built-in Pages pipeline works. The old custom workflow is manual
only and is not the production publishing mechanism. Do not switch Pages to
GitHub Actions until billing is resolved and a successful deployment is verified.

GitHub Pages cannot select HTML by query string or apply Nginx configuration.
The Pages package therefore includes pre-rendered Kyrgyz pages under `/ky/`,
with native language links usable without JavaScript. Existing `?lang=ky` links
are routed to those pages in the browser. Old `indexkg.html` and `contactkg.html`
links redirect to the Kyrgyz pages. Missing URLs return the custom 404 page.
Nginx-specific response headers and server redirects do not apply on Pages.

The main working directory may contain unpublished edits. Only the committed
production sources were used for the migration; unrelated local edits were kept.
