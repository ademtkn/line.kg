#!/usr/bin/env python3
"""Build a GitHub Pages package; keep bilingual HTML readable without JavaScript."""
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import parse_qs, urlsplit, urlunsplit
import build

# GitHub Pages cannot send response headers, so the policy travels in a meta tag.
# frame-ancestors is ignored in meta tags; pages-language.js breaks out of frames.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; "
       "upgrade-insecure-requests")


def clean_page(page):
    """Public route for a source page: '' for the home page, 'contact', 'privacy'..."""
    return '' if page == 'index.html' else page.removesuffix('.html')


def page_url(value, language=None):
    address = urlsplit(value)
    if not address.path:
        return value
    if address.netloc and address.netloc not in ('line.kg', 'www.line.kg'):
        return value
    page = address.path.removeprefix('/ky/').lstrip('/') or 'index.html'
    if page not in build.PAGES:
        return value
    selected = language or parse_qs(address.query).get('lang', ['en'])[0]
    path = ('/ky/' if selected == 'ky' else '/') + clean_page(page)
    return urlunsplit((address.scheme, address.netloc, path, '', address.fragment))


PAGES_LANGUAGE_JS = '''(function () {
    'use strict';
    // The Pages host cannot send frame-ancestors, so leave any frame we are shown in.
    try { if (window.top !== window.self) { window.top.location.replace(window.self.location.href); } } catch (e) { /* Blocked by the browser. */ }

    // The language switch stores its choice before navigating, so a saved preference never undoes it.
    document.addEventListener('click', function (event) {
        var link = event.target.closest && event.target.closest('[data-language]');
        if (link) { try { localStorage.setItem('linekg.language', link.getAttribute('data-language')); } catch (e) {} }
    });

    var address = new URL(window.location.href);
    var kyrgyzPath = /^\\/ky(\\/|$)/.test(address.pathname);
    var route = address.pathname.replace(/^\\/ky(?=\\/|$)/, '').replace(/^\\/+/, '').replace(/\\.html$/, '').replace(/\\/+$/, '');
    if (route === 'index') { route = ''; }
    var selected = address.searchParams.get('lang');
    if (selected !== 'en' && selected !== 'ky') {
        selected = kyrgyzPath ? 'ky' : null;
        if (!selected) { try { selected = localStorage.getItem('linekg.language'); } catch (e) {} }
    }
    if (selected !== 'ky') { selected = 'en'; }
    // Public addresses are /, /contact and /privacy, with /ky/ in front for Kyrgyz.
    if (['', 'contact', 'privacy'].indexOf(route) !== -1) {
        var path = (selected === 'ky' ? '/ky/' : '/') + route;
        if (address.pathname !== path) {
            address.searchParams.delete('lang');
            window.location.replace(path + address.search + address.hash);
            return;
        }
    }
    // Hand the route's language to the initializer; language.js removes the parameter again.
    address.searchParams.set('lang', selected);
    window.history.replaceState(window.history.state, '', address.pathname + address.search + address.hash);
})();
'''


def replace_once(source, old, new):
    # Fail the build loudly if language.js changes and a Pages patch no longer applies.
    if source.count(old) != 1:
        raise ValueError('Pages patch does not apply to language.js: ' + old[:60])
    return source.replace(old, new)


def pages_language_script(source):
    """language.js for static routes: clean paths, no ?lang= in the address bar."""
    source = replace_once(source,
        "var page = { home: 'index.html', contact: 'contact.html', privacy: 'privacy.html' }[document.body.dataset.page] || 'index.html';",
        "var page = { home: '', contact: 'contact', privacy: 'privacy' }[document.body.dataset.page] || '';")
    source = replace_once(source,
        "var canonical = base + '?lang=' + language;",
        "var canonical = 'https://line.kg/' + (language === 'ky' ? 'ky/' : '') + page;")
    source = replace_once(source,
        "link.href = base + '?lang=' + (supported.indexOf(alternate) !== -1 ? alternate : 'en');",
        "link.href = 'https://line.kg/' + (alternate === 'ky' ? 'ky/' : '') + page;")
    source = replace_once(source,
        "languageUrl.searchParams.set('lang', link.dataset.language);",
        "languageUrl.pathname = languageUrl.pathname.replace(/^\\/ky(?=\\/|$)/, '') || '/'; "
        "if (link.dataset.language === 'ky') { languageUrl.pathname = '/ky' + languageUrl.pathname; } "
        "languageUrl.searchParams.delete('lang');")
    source = replace_once(source,
        "            if (url.origin === window.location.origin) {\n                url.searchParams.set('lang', language);",
        "            if (url.origin === window.location.origin) {\n                url.searchParams.delete('lang');")
    source = replace_once(source,
        "        address.searchParams.set('lang', language);\n        try {",
        "        address.searchParams.delete('lang');\n        try {")
    return source


def main():
    build.build()
    output = build.ROOT / 'dist'
    shutil.rmtree(output / '_localized')
    # Pages negotiates compression itself; do not publish unused sidecar files.
    for path in output.rglob('*.gz'):
        path.unlink()
    language_js = pages_language_script((output / 'assets/js/language.js').read_text())
    (output / 'assets/js/language.js').write_text(language_js)
    (output / 'assets/js/pages-language.js').write_text(PAGES_LANGUAGE_JS)
    language_version = hashlib.sha256(language_js.encode()).hexdigest()[:12]
    adapter_version = hashlib.sha256(PAGES_LANGUAGE_JS.encode()).hexdigest()[:12]
    for language in build.LANGUAGES:
        for page in build.PAGES:
            document = build.Document(build.render_page(page, language))
            for node in build.elements(document.root):
                if node.tag == 'html':
                    node.attrs['data-static-pages'] = 'true'
                if node.tag == 'head':
                    # Keep the charset declaration first so it stays within the first 1024 bytes.
                    charset = next((i for i, child in enumerate(node.children)
                                    if isinstance(child, build.Node) and 'charset' in child.attrs), -1)
                    node.children[charset + 1:charset + 1] = [
                        build.Node('meta', {'http-equiv': 'Content-Security-Policy', 'content': CSP}),
                        build.Node('meta', {'name': 'referrer', 'content': 'strict-origin-when-cross-origin'}),
                        build.Node('script', {'src': '/assets/js/pages-language.js?v=' + adapter_version}),
                    ]
                if node.tag == 'script' and node.attrs.get('src', '').split('?')[0] == '/assets/js/language.js':
                    # Refresh the URL so browsers cannot reuse a previous copy.
                    node.attrs['src'] = '/assets/js/language.js?v=' + language_version
                if node.tag == 'a' and 'href' in node.attrs:
                    node.attrs['href'] = page_url(node.attrs['href'])
                if node.tag == 'link' and node.attrs.get('rel') == 'canonical':
                    node.attrs['href'] = page_url(node.attrs['href'], language)
                if node.tag == 'link' and node.attrs.get('rel') == 'alternate':
                    node.attrs['href'] = page_url(node.attrs['href'])
                if node.tag == 'meta' and node.attrs.get('property') == 'og:url':
                    node.attrs['content'] = page_url(node.attrs['content'], language)
            path = output / ('ky' if language == 'ky' else '') / page
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(build.serialize(document.root))
    # Old shared URLs still resolve, with a refresh for clients without JavaScript.
    for old, target in [('indexkg.html', '/ky/'), ('contactkg.html', '/ky/contact')]:
        (output / old).write_text('<!doctype html><html lang="ky"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=' + target + '"><link rel="canonical" href="https://line.kg' + target + '"></head><body><a href="' + target + '">Улантуу</a></body></html>')
    (output / '.nojekyll').touch()
    (output / 'CNAME').write_text('line.kg\n')
    well_known = output / '.well-known'
    well_known.mkdir(exist_ok=True)
    (well_known / 'security.txt').write_text(
        'Contact: mailto:linekginfo@gmail.com\n'
        'Expires: ' + (date.today() + timedelta(days=365)).isoformat() + 'T00:00:00.000Z\n'
        'Preferred-Languages: en, ky\n'
        'Canonical: https://line.kg/.well-known/security.txt\n')
    sitemap = (output / 'sitemap.xml').read_text()
    sitemap = re.sub(r'https://line\.kg/[^<"\s]+\?lang=(?:en|ky)', lambda match: page_url(match[0]), sitemap)
    (output / 'sitemap.xml').write_text(sitemap)
    print(json.dumps({'output': str(output), 'files': sum(p.is_file() for p in output.rglob('*'))}))


if __name__ == '__main__':
    main()
