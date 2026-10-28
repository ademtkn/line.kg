"""Validate the four bilingual source pages without network or browser dependencies.

Run with: python3 -m unittest discover -s tests -p 'test_site.py'
Generated HTTP/SSR output is covered separately by test_publish.py.
"""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unittest
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = {"index.html": "home", "contact.html": "contact", "privacy.html": "privacy", "404.html": "notfound"}
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class Element:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = []

    def hidden(self):
        node = self
        while node:
            if "hidden" in node.attrs or "d-none" in node.attrs.get("class", "").split():
                return True
            node = node.parent
        return False


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.stack = []
        self.feed(source)
        self.close()
        if self.stack:
            raise ValueError("Unclosed elements: " + ", ".join(n.tag for n in self.stack))

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1] if self.stack else None)
        self.elements.append(node)
        if self.stack:
            self.stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.stack.pop()

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1].tag != tag:
            raise ValueError("Unexpected closing tag: " + tag)
        self.stack.pop()

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].text.append(data)


def normalized(value):
    return re.sub(r"\s+", " ", value).strip()


class SiteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {name: Page((ROOT / name).read_text()) for name in PAGES}
        cls.dictionaries = {
            language: json.loads((ROOT / "assets/i18n" / (language + ".json")).read_text())
            for language in ("en", "ky")
        }

    def test_four_source_pages_and_no_duplicate_language_templates(self):
        self.assertEqual({p.name for p in ROOT.glob("*.html")}, set(PAGES))

    def test_translation_keys_and_english_defaults_are_complete(self):
        english, kyrgyz = self.dictionaries["en"], self.dictionaries["ky"]
        self.assertEqual(set(english), set(kyrgyz), "Both languages must define the same keys")
        for prefix in ("home", "contact", "privacy", "notfound"):
            self.assertIn(prefix + ".page_title", english)
            self.assertIn(prefix + ".description", english)
        for language, dictionary in self.dictionaries.items():
            for key, value in dictionary.items():
                with self.subTest(language=language, key=key):
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip(), "A translation cannot be blank")
        for name, page in self.pages.items():
            text_bindings = 0
            for node in page.elements:
                text_key = node.attrs.get("data-i18n")
                if text_key:
                    with self.subTest(page=name, text_key=text_key):
                        self.assertIn(text_key, english)
                        self.assertFalse(node.children, "Text translations must preserve nested icons/markup")
                        self.assertEqual(normalized("".join(node.text)), normalized(english[text_key]))
                    text_bindings += 1
                attribute_keys = json.loads(node.attrs.get("data-i18n-attrs", "{}"))
                self.assertIsInstance(attribute_keys, dict)
                for attribute, key in attribute_keys.items():
                    with self.subTest(page=name, attribute=attribute, key=key):
                        self.assertIn(key, english)
                        self.assertIn(attribute, node.attrs)
                        self.assertEqual(normalized(node.attrs[attribute]), normalized(english[key]))
            self.assertGreater(text_bindings, 0, name + " must contain translatable content")
            titles = [n for n in page.elements if n.tag == "title"]
            descriptions = [n for n in page.elements if n.tag == "meta" and n.attrs.get("name") == "description"]
            self.assertEqual(len(titles), 1)
            self.assertIn("data-i18n", titles[0].attrs)
            self.assertEqual(len(descriptions), 1)
            self.assertIn("content", json.loads(descriptions[0].attrs.get("data-i18n-attrs", "{}")))

    def test_ids_local_files_srcsets_and_fragment_targets_exist(self):
        ids_by_page = {}
        for name, page in self.pages.items():
            ids = [n.attrs["id"] for n in page.elements if "id" in n.attrs]
            duplicates = [value for value, count in Counter(ids).items() if count > 1]
            self.assertFalse(duplicates, name + " has duplicate IDs: " + ", ".join(duplicates))
            ids_by_page[name] = set(ids)
        for name, page in self.pages.items():
            for node in page.elements:
                references = [node.attrs.get(attribute) for attribute in ("src", "href")]
                if "srcset" in node.attrs:
                    references.extend(candidate.strip().split()[0] for candidate in node.attrs["srcset"].split(","))
                for value in filter(None, references):
                    address = urlsplit(value)
                    if address.scheme or address.netloc:
                        continue
                    target = ROOT / unquote(address.path.lstrip("/")) if address.path else ROOT / name
                    with self.subTest(page=name, reference=value):
                        self.assertTrue(target.exists(), "Missing local file: " + str(target))
                        if address.fragment and target.suffix == ".html":
                            self.assertIn(target.name, ids_by_page)
                            self.assertIn(unquote(address.fragment), ids_by_page[target.name], "Missing fragment target")

    def test_language_links_keep_page_context(self):
        for name, page in self.pages.items():
            html = [n for n in page.elements if n.tag == "html"]
            bodies = [n for n in page.elements if n.tag == "body"]
            self.assertEqual(len(html), 1)
            self.assertEqual(html[0].attrs.get("lang"), "en", "Default content must declare its language")
            self.assertEqual(len(bodies), 1)
            self.assertEqual(bodies[0].attrs.get("data-page"), PAGES[name])
            selectors = [n for n in page.elements if "data-language" in n.attrs]
            self.assertEqual({n.attrs["data-language"] for n in selectors}, {"en", "ky"})
            self.assertEqual(len(selectors), 2)
            for node in selectors:
                language = node.attrs["data-language"]
                address = urlsplit(node.attrs["href"])
                with self.subTest(page=name, language=language):
                    self.assertEqual(node.tag, "a")
                    self.assertEqual(address.path, name)
                    self.assertEqual(parse_qs(address.query).get("lang"), [language])
                    self.assertEqual(node.attrs.get("lang"), language)
                    self.assertEqual(node.attrs.get("hreflang"), language)
            for node in page.elements:
                if "data-localized-link" in node.attrs:
                    address = urlsplit(node.attrs["href"])
                    self.assertIn(address.path, PAGES)
                    self.assertEqual(parse_qs(address.query).get("lang"), ["en"])

    def test_keyboard_bypass_and_accessible_page_landmarks(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                mains = [n for n in page.elements if n.tag == "main"]
                self.assertEqual(len(mains), 1)
                self.assertEqual(mains[0].attrs.get("id"), "main-content")
                self.assertEqual(mains[0].attrs.get("tabindex"), "-1")
                links = [n for n in page.elements if n.tag == "a" and not n.hidden()]
                self.assertTrue(links)
                self.assertEqual(links[0].attrs.get("href"), "#main-content")
                self.assertEqual(links[0].attrs.get("data-i18n"), "common.skip_to_content")
                headings = [n for n in page.elements if n.tag == "h1" and not n.hidden()]
                self.assertEqual(len(headings), 1, "Each page needs one clear primary heading")
                for nav in [n for n in page.elements if n.tag == "nav" and not n.hidden()]:
                    self.assertTrue(nav.attrs.get("aria-label") or nav.attrs.get("aria-labelledby"))
                for node in page.elements:
                    if node.tag == "svg" and not node.hidden():
                        self.assertEqual(node.attrs.get("aria-hidden"), "true", "Decorative SVGs must not repeat accessible text")

    def test_external_language_bootstrap_and_page_specific_plugins(self):
        for name, page in self.pages.items():
            scripts = [n for n in page.elements if n.tag == "script"]
            paths = [urlsplit(n.attrs.get("src", "")).path for n in scripts]
            with self.subTest(page=name):
                self.assertEqual(paths.count("assets/js/language-init.js"), 1)
                self.assertEqual(paths.count("assets/js/language.js"), 1)
                self.assertLess(paths.index("assets/js/language-init.js"), paths.index("assets/js/language.js"))
                loader = scripts[paths.index("assets/js/language.js")]
                self.assertIn("defer", loader.attrs)
                for script in scripts:
                    if script.attrs.get("type") not in ("application/ld+json", "application/json"):
                        self.assertTrue(script.attrs.get("src"), "Executable inline script is incompatible with the publishing CSP")
                for path in paths:
                    self.assertNotRegex(path, r"gsap|magnific|popper")
                if name != "index.html":
                    self.assertFalse(any("plugins/" in path for path in paths), "Static utility pages must not load carousel/animation dependencies")
                for path in ("common/js/common_script.js", "assets/js/theme.js"):
                    if path in paths:
                        self.assertGreater(paths.index(path), paths.index("assets/js/language.js"))

    def test_fonts_and_styles_are_local_without_icon_font_dependencies(self):
        for name, page in self.pages.items():
            resources = [n for n in page.elements if n.tag in ("link", "script") and (
                n.tag == "script" or n.attrs.get("rel") in ("stylesheet", "preload"))]
            with self.subTest(page=name):
                self.assertIn("assets/css/fonts.css", [urlsplit(n.attrs.get("href", "")).path for n in resources])
                for node in resources:
                    reference = node.attrs.get("src") or node.attrs.get("href", "")
                    self.assertFalse(urlsplit(reference).scheme or urlsplit(reference).netloc, "Site assets must load locally")
                    self.assertNotRegex(reference, r"fontawesome|flaticon|magnific|gsap")
        fonts_css = (ROOT / "assets/css/fonts.css").read_text()
        for reference in re.findall(r"url\(['\"]?([^)'\"]+)", fonts_css):
            self.assertFalse(urlsplit(reference).scheme)
            font = ROOT / "assets/css" / reference
            self.assertTrue(font.is_file(), "Missing self-hosted font: " + str(font))
            self.assertEqual(font.read_bytes()[:4], b"wOF2")
        for license_name in ("Manrope-OFL.txt", "PlusJakartaSans-OFL.txt", "NotoSans-OFL.txt"):
            self.assertIn("SIL OPEN FONT LICENSE", (ROOT / "assets/fonts" / license_name).read_text())

    def test_privacy_link_is_available_and_error_page_cannot_be_indexed(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                privacy = [n for n in page.elements if n.tag == "a" and not n.hidden() and urlsplit(n.attrs.get("href", "")).path == "privacy.html"]
                self.assertTrue(privacy, "Every page must expose the privacy policy")
                if name == "404.html":
                    robots = [n for n in page.elements if n.tag == "meta" and n.attrs.get("name") == "robots"]
                    self.assertEqual(len(robots), 1)
                    self.assertIn("noindex", robots[0].attrs.get("content", "").lower())
                    self.assertFalse([n for n in page.elements if n.tag == "link" and n.attrs.get("rel") in ("canonical", "alternate")])
                    self.assertFalse([n for n in page.elements if n.tag == "meta" and n.attrs.get("property") == "og:url"])


if __name__ == "__main__":
    unittest.main()
