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
with native language links usable without JavaScript. Public addresses carry no
file extension or language query: `/`, `/contact` and `/privacy` for English and
`/ky/`, `/ky/contact` and `/ky/privacy` for Kyrgyz. Old `?lang=ky`, `index.html`
and `contact.html` links are routed to these addresses in the browser. Old `indexkg.html` and `contactkg.html`
links redirect to the Kyrgyz pages. Missing URLs return the custom 404 page.
Nginx-specific response headers and server redirects do not apply on Pages.

The main working directory may contain unpublished edits. Only the committed
production sources were used for the migration; unrelated local edits were kept.

## Securing the repository and domain

Pages sends no custom response headers, so the build adds a Content-Security-Policy
and referrer policy as meta tags, a frame-breaking check and
`/.well-known/security.txt`. The settings below live in GitHub, Cloudflare and the
registrar and cannot be set from this repository:

1. **GitHub account:** turn on two-factor authentication (a passkey or authenticator
   app), keep recovery codes offline, and review *Settings > Applications* and
   *Settings > SSH and GPG keys* for anything unfamiliar.
2. **Collaborators:** *Settings > Collaborators* should list only people who must
   publish. Give everyone else *Read* access or none.
3. **Rulesets** (*Settings > Rules > Rulesets*): the active ruleset "Protect main and
   gh-pages" restricts updates, deletions and force pushes on both branches. Only the
   repository admin role is on the bypass list, so the owner can still push and run
   `python3 tools/publish-pages.py`. Other collaborators cannot push to those branches.
4. **Actions** (*Settings > Actions > General*): allow only actions from this
   repository or GitHub, set workflow permissions to read-only and require approval
   for all outside contributors.
5. **Pages** (*Settings > Pages*): custom domain `line.kg` with *Enforce HTTPS* on. Verify the
   domain under the account's *Settings > Pages* so nobody else can claim it.
6. **Code security:** enable Dependabot alerts, secret scanning with push protection
   and private vulnerability reporting.
7. **Domain:** protect the Cloudflare and cctld.kg accounts with two-factor
   authentication, and add a CAA record `0 issue "letsencrypt.org"`.
