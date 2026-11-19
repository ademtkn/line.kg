# Publishing Line Education

The website keeps one source HTML file per page and two translation dictionaries.
`python3 tools/build.py` generates a public-only `dist/` package. It renders English
and Kyrgyz HTML and social metadata before a browser or crawler receives the page.
The `_localized/` outputs are generated files, not duplicate editable sources.

Only assets referenced by the published pages or their CSS are copied. Hidden demo
markup and its unused images stay in the source project; they are removed from the
package and its translation JSON. Git data, tests, tooling, SCSS, maps, design
originals and documentation are not uploaded. Publish **dist contents only**.

## Local checks

Run `python3 tools/preview.py --port 8765`, then open
`http://127.0.0.1:8765/index.html?lang=ky`. The server binds only to localhost,
renders translated HTML, implements old Kyrgyz redirects and returns the bilingual
custom error page with an actual HTTP 404 status. It sends the same CSP and basic
security headers as the production template. Unknown files and directory listings
are blocked; write methods are not implemented. HSTS is deliberately omitted on
this HTTP development server.

## Active deployment

The site was published on **15 October 2026** to the existing DigitalOcean server
at `167.172.181.221`. The active release is `20261015-36e49a879d`, with its public
root at `/var/www/line.kg-releases/20261015-36e49a879d/dist`. The active Nginx site
file is `/etc/nginx/sites-available/line.kg`, enabled through
`/etc/nginx/sites-enabled/line.kg`. The previous `/var/www/line.kg` directory was
left intact. See [the release record](RELEASE-2026-10-15.md) for validation results,
backup locations and the rollback procedure.

## Nginx and HTTPS templates

The files in this directory are reusable templates; the active server has its own
release root and ACME webroot settings. When preparing another server, install
current Nginx, arrange HTTPS certificates, choose the site root and copy the built
package. Copy `security-headers.conf` to
`/etc/nginx/snippets/linekg-security-headers.conf` and
`nginx-language-redirects.conf` to
`/etc/nginx/snippets/linekg-language-redirects.conf`. Adapt the paths in `line.kg.conf`,
place it in the server's HTTP-context configuration directory, and run `nginx -t`
before reloading. Do not publish the repository root or this deployment directory.

The query-language map serves translated HTML at the existing URLs, so sharing
`index.html?lang=ky` includes Kyrgyz metadata even for crawlers without JavaScript.
`_localized/` is internal-only. Missing files return 404 instead of a home-page 200.
Gzip precompressed output, resource caching and MIME types are configured.

CSP allows local JavaScript and prohibits inline scripts, eval, iframes, objects
and external resource connections. Inline styles remain allowed for existing
backgrounds and animation transforms. Headers also prevent framing, MIME sniffing,
and access to camera, microphone, location, USB and payments. HSTS is sent only by
the HTTPS server; enable it after certificates and HTTPS have been verified.

Before considering production ready, check HTTPS redirects, certificates, all
security headers, a real unknown-path 404, and EN/KY crawler metadata on the actual
DigitalOcean endpoint. These checks passed for the release above. Repeat them
after future server or site changes; local validation cannot establish a future
server's state.

## Certificate renewal and Nginx reload

The current Let's Encrypt certificate covers `line.kg` and `www.line.kg` and was
verified as valid through **13 January 2027**. Certbot's renewal configuration uses
the webroot `/var/www/line.kg-acme`, which must remain available through the HTTP
ACME challenge location even when normal HTTP requests redirect to HTTPS.
`certbot.timer` is enabled on the current server.

Renewing certificate files does not by itself reload Nginx. Install the supplied
deploy hook whenever preparing or rebuilding this server. From an administrative
checkout containing this script, run:

```sh
sudo install -m 0755 deployment/renew-linekg-certificate.sh /etc/letsencrypt/renewal-hooks/deploy/linekg-reload-nginx
sudo env RENEWED_LINEAGE=/etc/letsencrypt/live/line.kg /etc/letsencrypt/renewal-hooks/deploy/linekg-reload-nginx
sudo systemctl is-enabled certbot.timer
```

The hook acts only on `/etc/letsencrypt/live/line.kg`; it runs `nginx -t` before
reloading Nginx. It was installed and executed successfully for this release.
An actual scheduled future renewal has not yet occurred; monitor its logs and
certificate expiry. `certbot renew --dry-run` can be used for a future renewal
exercise, but was not part of the recorded validation. The website package
contains neither this administrative script nor certificates/private keys.
