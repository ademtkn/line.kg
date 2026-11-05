"""Check the GitHub Pages package: clean addresses, no ?lang= in links, policy and security.txt.

Run with: python3 -m unittest discover -s tests -p 'test_pages.py'
"""

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
import pages

ROUTES = {"index.html": "", "contact.html": "contact", "privacy.html": "privacy"}


class PagesPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pages.main()
        cls.dist = ROOT / "dist"

    def documents(self):
        for language, prefix in (("en", ""), ("ky", "ky/")):
            for page in build.PAGES:
                path = self.dist / prefix / page
                yield language, page, path, list(build.elements(build.Document(path.read_text()).root))

    def test_page_urls_drop_extension_and_language_query(self):
        self.assertEqual(pages.page_url("index.html?lang=en"), "/")
        self.assertEqual(pages.page_url("index.html?lang=ky"), "/ky/")
        self.assertEqual(pages.page_url("contact.html?lang=ky"), "/ky/contact")
        self.assertEqual(pages.page_url("privacy.html?lang=en#top"), "/privacy#top")
        self.assertEqual(pages.page_url("https://line.kg/contact.html?lang=ky"), "https://line.kg/ky/contact")
        self.assertEqual(pages.page_url("https://example.com/contact.html?lang=ky"), "https://example.com/contact.html?lang=ky")

    def test_internal_links_and_metadata_use_clean_routes(self):
        for language, page, path, nodes in self.documents():
            prefix = "/ky/" if language == "ky" else "/"
            for node in nodes:
                href = node.attrs.get("href", "")
                if node.tag == "a" and not href.startswith(("http", "#", "mailto:", "tel:")):
                    with self.subTest(page=page, language=language, href=href):
                        self.assertNotRegex(href, r"\.html|\?lang=")
                if node.tag == "link" and node.attrs.get("rel") in ("canonical", "alternate"):
                    self.assertNotRegex(href, r"\.html|\?lang=")
                if node.tag == "link" and node.attrs.get("rel") == "canonical":
                    self.assertEqual(href, "https://line.kg" + prefix + ROUTES[page])
            if page in ROUTES:
                switches = {n.attrs["data-language"]: n.attrs["href"] for n in nodes if "data-language" in n.attrs}
                self.assertEqual(switches, {"en": "/" + ROUTES[page], "ky": "/ky/" + ROUTES[page]})

    def test_sitemap_lists_only_clean_urls(self):
        sitemap = (self.dist / "sitemap.xml").read_text()
        locations = re.findall(r"<loc>([^<]+)</loc>", sitemap)
        self.assertEqual(sorted(locations), sorted(
            "https://line.kg/" + prefix + route for prefix in ("", "ky/") for route in ROUTES.values()))
        self.assertNotRegex(sitemap, r"\.html|\?lang=")

    def test_policy_and_referrer_meta_precede_scripts_and_follow_charset(self):
        for language, page, path, nodes in self.documents():
            head = next(n for n in nodes if n.tag == "head")
            children = [c for c in head.children if isinstance(c, build.Node)]
            tags = [(c.tag, c.attrs.get("http-equiv") or c.attrs.get("name") or ("charset" if "charset" in c.attrs else "")) for c in children]
            with self.subTest(page=page, language=language):
                self.assertEqual(tags[0], ("meta", "charset"))
                self.assertEqual(tags[1], ("meta", "Content-Security-Policy"))
                self.assertLess(tags.index(("meta", "Content-Security-Policy")), min(i for i, t in enumerate(tags) if t[0] == "script"))
                policy = children[1].attrs["content"]
                self.assertIn("script-src 'self'", policy)
                self.assertIn("object-src 'none'", policy)
                self.assertNotIn("unsafe-eval", policy)
                self.assertNotIn("frame-ancestors", policy, "Ignored in meta tags")
        self.assertLess((self.dist / "index.html").read_text().index('name="referrer"'), 1500)

    def test_security_txt_cname_and_no_internal_files_are_published(self):
        security = (self.dist / ".well-known/security.txt").read_text()
        self.assertIn("Contact: mailto:linekginfo@gmail.com", security)
        self.assertRegex(security, r"Expires: \d{4}-\d{2}-\d{2}T")
        self.assertEqual((self.dist / "CNAME").read_text().strip(), "line.kg")
        self.assertFalse((self.dist / "_localized").exists())
        self.assertEqual(list(self.dist.rglob("*.gz")), [])
        for legacy, target in (("indexkg.html", "/ky/"), ("contactkg.html", "/ky/contact")):
            self.assertIn('url=' + target + '"', (self.dist / legacy).read_text())

    @unittest.skipUnless(shutil.which("node"), "Node is needed to run the browser script")
    def test_route_script_redirects_to_clean_language_paths(self):
        script = (self.dist / "assets/js/pages-language.js").read_text()
        harness = r"""
const vm = require('vm');
function run(url, stored) {
  const history = []; let redirected = null;
  const location = { href: url, replace(target) { redirected = target; } };
  const window = { location, history: { state: null, replaceState(s, t, u) { history.push(u); } } };
  window.top = window; window.self = window;
  Object.defineProperty(location, 'search', { get() { return new URL(url).search; } });
  Object.defineProperty(location, 'pathname', { get() { return new URL(url).pathname; } });
  Object.defineProperty(location, 'hash', { get() { return new URL(url).hash; } });
  const document = { addEventListener() {} };
  const localStorage = { getItem() { return stored || null; }, setItem() {} };
  vm.runInNewContext(process.argv[1], { window, document, localStorage, URL, location, history: window.history });
  return { redirected, replaced: history[0] || null };
}
const cases = {
  'https://line.kg/': run('https://line.kg/'),
  'https://line.kg/?lang=ky': run('https://line.kg/?lang=ky'),
  'https://line.kg/index.html?lang=en': run('https://line.kg/index.html?lang=en'),
  'https://line.kg/contact.html#form': run('https://line.kg/contact.html#form'),
  'https://line.kg/ky/contact': run('https://line.kg/ky/contact', 'en'),
  'https://line.kg/privacy?utm=x': run('https://line.kg/privacy?utm=x'),
  'stored ky': run('https://line.kg/contact', 'ky'),
  'https://line.kg/missing': run('https://line.kg/missing'),
};
console.log(JSON.stringify(cases));
"""
        result = subprocess.run(["node", "-e", harness, "--", script], capture_output=True, text=True, check=True)
        cases = json.loads(result.stdout)
        self.assertEqual(cases["https://line.kg/"], {"redirected": None, "replaced": "/?lang=en"})
        self.assertEqual(cases["https://line.kg/?lang=ky"]["redirected"], "/ky/")
        self.assertEqual(cases["https://line.kg/index.html?lang=en"]["redirected"], "/")
        self.assertEqual(cases["https://line.kg/contact.html#form"]["redirected"], "/contact#form")
        self.assertEqual(cases["https://line.kg/ky/contact"]["redirected"], None, "The path decides, not the saved language")
        self.assertEqual(cases["https://line.kg/privacy?utm=x"]["replaced"], "/privacy?utm=x&lang=en")
        self.assertEqual(cases["stored ky"]["redirected"], "/ky/contact")
        self.assertIsNone(cases["https://line.kg/missing"]["redirected"])


if __name__ == "__main__":
    unittest.main()
