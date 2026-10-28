# Line Education

Line Education is the informational website of **"Line" LLC / ОсОО «Лайн»**.
Contact: **linekginfo@gmail.com** and **+996 502 001 903**.

The project has four editable HTML sources: `index.html`, `contact.html`,
`privacy.html` and `404.html`. English and Kyrgyz copy is shared through
`assets/i18n/en.json` and `assets/i18n/ky.json`; there are no separately maintained
Kyrgyz HTML sources.

## Languages and publishing output

Use `?lang=en` or `?lang=ky` on the home, contact and privacy pages. The URL takes
priority over a saved preference. With JavaScript enabled, `linekg.language` in
browser local storage remembers the selected language; without a language choice,
English is the default. EN/KY links preserve the current page and language in
navigation, reloads and shared URLs.

The publishing build and local preview render the selected language into HTML
before serving it, including descriptions, accessible labels and social sharing
metadata. Both languages therefore remain readable without JavaScript, and
sharing crawlers receive the corresponding metadata. JavaScript supports saved
preferences, the interactive FAQ and the homepage carousel; it is not required to
read the page or follow its contact links. If a translation request fails, the
already rendered page remains usable.

```sh
python3 tools/build.py
```

The generated `dist/` directory contains public assets and pre-rendered EN/KY
variants under `_localized/`. These are build outputs, not editable source copies.
Hidden demo teams, testimonials and placeholder links remain in the source
project, but are removed from the published HTML and translation JSON. Unused
assets, source tooling, tests, design originals and Git data are excluded.

**Publish only the contents of `dist/`, never the repository root.** Edit translation
values without changing their keys. When changing English copy, keep the source
HTML fallback synchronized. After changing shared CSS, JavaScript or dictionaries,
refresh the asset `?v=` fingerprints and `linekg-i18n-version` in all four source
pages, then rebuild `dist/` so cached assets and rendered text stay current.

## Local preview and verification

Use the public-only preview server rather than a generic directory server:

```sh
python3 tools/preview.py --port 8785
```

The current review preview uses
`http://127.0.0.1:8785/index.html?lang=ky`. The tool's default port is `8765`, which
can also be selected with `--port 8765` for a separate local session. It binds only
to localhost, renders both languages, redirects former `indexkg.html` and
`contactkg.html` addresses, and returns the custom page with HTTP 404 for missing
paths. It also applies the local security headers and blocks source files,
directory listings and unsupported write methods. HSTS is reserved for HTTPS
production hosting.

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_language.js
```

The checks cover source and rendered HTML, translation keys, local links, build
contents, preview responses, language precedence and metadata. Browser checks
should include both languages at phone, landscape, tablet and desktop widths,
keyboard navigation, visible focus, FAQ controls and real missing-page recovery.
Passing these checks does not certify complete WCAG conformance or the security
of a future hosting server.

## Site features and deployment

The privacy policy identifies the actual operator and describes language storage,
possible hosting request data, voluntary contact information and external
providers. The site uses self-hosted OFL fonts and original SVG UI icons. FAQ images
have responsive variants; social sharing cards have localized metadata. The
published package includes `sitemap.xml`, `robots.txt` and the bilingual 404 page.
No on-site accounts, payments, contact forms or visitor analytics are installed.

`deployment/` contains prepared Nginx, security-header and old-language redirect
configurations. They are templates, not an active deployment. Configure the
production site root and HTTPS certificates on the target server, run **`nginx -t`
on that server** before reloading, and verify HTTPS redirects, headers, EN/KY
sharing metadata and a real HTTP 404 afterward. See
[`deployment/README.md`](deployment/README.md) for publishing instructions.
