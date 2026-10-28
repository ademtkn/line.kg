#!/usr/bin/env python3
"""Build a GitHub Pages package; keep bilingual HTML readable without JavaScript."""
import json
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlsplit, urlunsplit
import build


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
    path = ('/ky/' if selected == 'ky' else '/') + page
    return urlunsplit((address.scheme, address.netloc, path, '', address.fragment))


def main():
    build.build()
    output = build.ROOT / 'dist'
    shutil.rmtree(output / '_localized')
    # Pages negotiates compression itself; do not publish unused sidecar files.
    for path in output.rglob('*.gz'):
        path.unlink()
    for language in build.LANGUAGES:
        for page in build.PAGES:
            document = build.Document(build.render_page(page, language))
            for node in build.elements(document.root):
                if node.tag == 'html':
                    node.attrs['data-static-pages'] = 'true'
                if node.tag == 'head':
                    node.children.insert(0, build.Node('script', {'src': '/assets/js/pages-language.js?v=20261028'}))
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
    for old, page in [('indexkg.html', 'index.html'), ('contactkg.html', 'contact.html')]:
        (output / old).write_text('<!doctype html><html lang="ky"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/ky/' + page + '"><link rel="canonical" href="https://line.kg/ky/' + page + '"></head><body><a href="/ky/' + page + '">Улантуу</a></body></html>')
    (output / '.nojekyll').touch()
    (output / 'CNAME').write_text('line.kg\n')
    (output / 'assets/js/pages-language.js').write_text('''(function () {
    'use strict';
    var address = new URL(window.location.href);
    var explicit = address.searchParams.get('lang');
    var kyrgyzPath = address.pathname.indexOf('/ky/') === 0;
    var selected = explicit;
    if (selected !== 'en' && selected !== 'ky') {
        selected = kyrgyzPath ? 'ky' : null;
        if (!selected) { try { selected = localStorage.getItem('linekg.language'); } catch (e) {} }
    }
    if (selected !== 'ky') { selected = 'en'; }
    var page = address.pathname.replace(/^\\/ky\\//, '/').replace(/^\\//, '') || 'index.html';
    if (['index.html', 'contact.html', 'privacy.html', '404.html'].indexOf(page) !== -1) {
        var path = (selected === 'ky' ? '/ky/' : '/') + page;
        if ((selected === 'ky') !== kyrgyzPath) {
            address.pathname = path;
            window.location.replace(address.pathname + address.search + address.hash);
            return;
        }
    }
    // Let the existing language initializer prioritize this route over stored preferences.
    address.searchParams.set('lang', selected);
    window.history.replaceState(window.history.state, '', address.pathname + address.search + address.hash);
})();
''')
    # Keep canonical metadata and language switch links consistent with static routes.
    script = output / 'assets/js/language.js'
    source = script.read_text().replace(
        "var canonical = base + '?lang=' + language;",
        "var canonical = 'https://line.kg/' + (language === 'ky' ? 'ky/' : '') + page;")
    source = source.replace(
        "link.href = base + '?lang=' + (supported.indexOf(alternate) !== -1 ? alternate : 'en');",
        "link.href = 'https://line.kg/' + (alternate === 'ky' ? 'ky/' : '') + page;")
    source = source.replace(
        "languageUrl.searchParams.set('lang', link.dataset.language);",
        "languageUrl.pathname = languageUrl.pathname.replace(/^\\/ky\\//, '/'); if (link.dataset.language === 'ky') { languageUrl.pathname = '/ky' + languageUrl.pathname; } languageUrl.searchParams.set('lang', link.dataset.language);")
    script.write_text(source)
    sitemap = (output / 'sitemap.xml').read_text()
    import re
    sitemap = re.sub(r'https://line\.kg/[^<"\s]+\?lang=(?:en|ky)', lambda match: page_url(match[0]), sitemap)
    (output / 'sitemap.xml').write_text(sitemap)
    print(json.dumps({'output': str(output), 'files': sum(p.is_file() for p in output.rglob('*'))}))


if __name__ == '__main__':
    main()
