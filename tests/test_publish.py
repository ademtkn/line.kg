"""Exercise the real HTTP preview and the generated public-only package."""

import gzip
import http.client
import json
from pathlib import Path
import sys
from threading import Thread
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
import preview


def metadata(source):
    return {(node.attrs.get("property") or node.attrs.get("name")): node.attrs.get("content")
            for node in build.elements(build.Document(source).root) if node.tag == "meta"}


class PublicHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = preview.create_server(port=0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_languages_are_rendered_without_javascript(self):
        for page in build.PAGES:
            for language in build.LANGUAGES:
                with self.subTest(page=page, language=language):
                    status, headers, body = self.request("/" + page + "?lang=" + language)
                    self.assertEqual(status, 404 if page == "404.html" else 200)
                    html = body.decode("utf-8")
                    document = list(build.elements(build.Document(html).root))
                    root = next(node for node in document if node.tag == "html")
                    self.assertEqual(root.attrs.get("lang"), language)
                    self.assertEqual(root.attrs.get("data-rendered-language"), language)
                    dictionary = build.dictionaries()[language]
                    for node in document:
                        key = node.attrs.get("data-i18n")
                        if key:
                            self.assertEqual("".join(node.children), dictionary[key])
                    values = metadata(html)
                    self.assertEqual(values["og:locale"], "ky_KG" if language == "ky" else "en_US")
                    if "og:image" in values:
                        self.assertTrue(values["og:image"].endswith("line-education-" + language + ".png"))
                    if page != "404.html":
                        canonical = next(node for node in document if node.tag == "link" and node.attrs.get("rel") == "canonical")
                        self.assertEqual(canonical.attrs["href"], "https://line.kg/" + page + "?lang=" + language)

    def test_headers_apply_to_success_error_assets_and_redirects(self):
        for path in ("/", "/contact.html?lang=ky", "/missing?lang=ky", "/assets/js/language.js", "/indexkg.html"):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                for name, value in preview.SECURITY_HEADERS.items():
                    self.assertEqual(headers.get(name), value)
                self.assertNotIn("Strict-Transport-Security", headers, "HSTS must not be sent on an HTTP localhost preview")
                csp = headers["Content-Security-Policy"]
                script_policy = next(part.strip() for part in csp.split(";") if part.strip().startswith("script-src "))
                self.assertEqual(script_policy, "script-src 'self'")
                self.assertIn("frame-ancestors 'none'", csp)
                self.assertNotIn("unsafe-eval", csp)

    def test_missing_private_and_traversal_paths_are_real_404(self):
        private_paths = (
            "/unknown.html", "/.git/config", "/.env", "/.DS_Store", "/README.md",
            "/tools/build.py", "/tests/test_site.py", "/deployment/line.kg.conf",
            "/assets/fonts/SOURCES.md", "/common/fonts/flaticon/backup.txt", "/assets/",
            "/_localized/ky/index.html", "/../README.md", "/assets/%2e%2e/%2e%2e/README.md",
            "/common/js/plugins/jquery.magnific-popup.min.js",
        )
        for path in private_paths:
            with self.subTest(path=path):
                status, headers, body = self.request(path + "?lang=ky")
                self.assertEqual(status, 404)
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertIn(b'data-rendered-language="ky"', body)
                self.assertIn(b'content="noindex, follow"', body)

    def test_legacy_addresses_redirect_to_the_selected_language(self):
        for original, target in preview.LEGACY.items():
            with self.subTest(path=original):
                status, headers, body = self.request(original)
                self.assertEqual(status, 301)
                self.assertEqual(headers["Location"], target)
                self.assertEqual(body, b"")

    def test_gzip_and_head_keep_content_length_and_status(self):
        status, headers, compressed = self.request("/index.html?lang=ky", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Encoding"), "gzip")
        self.assertEqual(int(headers["Content-Length"]), len(compressed))
        self.assertIn(b'data-rendered-language="ky"', gzip.decompress(compressed))
        self.assertLess(len(compressed), len(gzip.decompress(compressed)))
        head_status, head_headers, head_body = self.request("/index.html?lang=ky", method="HEAD", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(head_status, 200)
        self.assertEqual(head_headers["Content-Length"], headers["Content-Length"])
        self.assertEqual(head_body, b"")
        status, headers, body = self.request("/missing", method="HEAD")
        self.assertEqual(status, 404)
        self.assertEqual(body, b"")

    def test_write_methods_have_no_handler(self):
        for method in ("POST", "PUT", "DELETE", "PATCH", "TRACE"):
            with self.subTest(method=method):
                status, headers, body = self.request("/contact.html", method=method)
                self.assertEqual(status, 405)
                self.assertEqual(headers["Allow"], "GET, HEAD")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_untrusted_language_value_is_not_reflected(self):
        status, headers, body = self.request("/index.html?lang=%3Cscript%3Ealert(1)%3C/script%3E")
        self.assertEqual(status, 200)
        self.assertIn(b'data-rendered-language="en"', body)
        self.assertNotIn(b"alert(1)", body)


class PublishPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build.build()
        cls.destination = ROOT / "dist"

    def test_package_contains_only_public_allowlisted_resources(self):
        resources = build.resource_set()
        expected = set(resources) | {Path(page) for page in build.PAGES} | {Path("robots.txt"), Path("sitemap.xml")}
        expected |= {Path("_localized") / language / page for language in build.LANGUAGES for page in build.PAGES}
        actual = {path.relative_to(self.destination) for path in self.destination.rglob("*")
                  if path.is_file() and path.suffix != ".gz"}
        self.assertEqual(actual, expected)
        for private in (".git", "tools", "tests", "deployment", "README.md", ".DS_Store", "assets/images/instructor"):
            self.assertFalse((self.destination / private).exists(), private + " is private source material")
        self.assertTrue((self.destination / "assets/images/social/line-education-en.png").exists())
        self.assertTrue((self.destination / "assets/images/social/line-education-ky.png").exists())

    def test_hidden_demo_markup_and_translations_stay_out_of_package(self):
        for page in self.destination.rglob("*.html"):
            source = page.read_text()
            self.assertNotIn("data-content-status", source)
            self.assertNotIn("instructor-sel", source)
            self.assertNotIn("testimonial-sel", source)
            self.assertNotRegex(source, r"\bDemo\b")
            for node in build.elements(build.Document(source).root):
                if node.tag == "script":
                    self.assertTrue(node.attrs.get("src"), "Inline script would violate publishing CSP")
        keys = build.used_translation_keys()
        for language in build.LANGUAGES:
            dictionary = json.loads((self.destination / "assets/i18n" / (language + ".json")).read_text())
            self.assertEqual(set(dictionary), keys)
            self.assertNotRegex(json.dumps(dictionary), r"\bDemo\b")

    def test_rendered_paths_and_precompressed_output_are_correct(self):
        for language in build.LANGUAGES:
            for page in build.PAGES:
                path = self.destination / "_localized" / language / page
                html = path.read_text()
                self.assertIn('data-rendered-language="' + language + '"', html)
                for node in build.elements(build.Document(html).root):
                    for attr in ("src", "href"):
                        address = node.attrs.get(attr, "")
                        self.assertFalse(address.startswith(("assets/", "common/")), "Internal outputs need root-relative assets")
                self.assertEqual(gzip.decompress(path.with_name(page + ".gz").read_bytes()), path.read_bytes())
        self.assertEqual((self.destination / "index.html").read_bytes(),
                         (self.destination / "_localized/en/index.html").read_bytes())

    def test_renderer_escapes_dictionary_text_and_attributes(self):
        malicious = '<img src=x onerror="alert(1)">'
        dictionaries = build.dictionaries()
        dictionaries["en"]["home.page_title"] = malicious
        dictionaries["en"]["common.whatsapp_label"] = malicious
        with patch.object(build, "dictionaries", return_value=dictionaries):
            source = build.render_page("index.html", "en")
        self.assertNotIn("<img src=x", source)
        self.assertIn("&lt;img", source)
        self.assertIn("&quot;", source)
        nodes = list(build.elements(build.Document(source).root))
        title = next(node for node in nodes if node.tag == "title")
        self.assertEqual(title.children, [malicious])
        self.assertFalse(any(node.attrs.get("onerror") for node in nodes))


if __name__ == "__main__":
    unittest.main()
