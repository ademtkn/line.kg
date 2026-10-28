#!/usr/bin/env python3
"""Create a public-only static package from the single bilingual page sources.

Only Python's standard library is required. The same renderer is used by preview.py.
"""

import argparse
from collections import deque
from dataclasses import dataclass, field
import gzip
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "contact.html", "privacy.html", "404.html")
LANGUAGES = ("en", "ky")
DOMAIN = "https://line.kg"
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
ATTRIBUTES = frozenset(("alt", "title", "content", "aria-label", "aria-valuetext", "placeholder"))
RESOURCE_ATTRIBUTES = frozenset(("src", "href", "poster"))
SAFE_ASSET_SUFFIXES = frozenset((
    ".css", ".js", ".json", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif",
    ".svg", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp4", ".webm",
))
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+(['\"])(.*?)\1", re.I)


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.feed(source)
        self.close()
        if len(self.stack) != 1:
            raise ValueError("Unclosed HTML elements: " + ", ".join(n.tag for n in self.stack[1:]))

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError("Unexpected HTML closing tag: " + tag)
        self.stack.pop()

    def handle_data(self, value):
        self.stack[-1].children.append(value)

    def handle_decl(self, value):
        self.stack[-1].children.append(Node("!doctype", {"value": value}))

    # Template comments, including commented-out demo markup, are not public output.


def public_children(node):
    for child in node.children:
        if isinstance(child, Node) and "data-content-status" in child.attrs:
            continue
        yield child


def elements(node):
    yield node
    for child in public_children(node):
        if isinstance(child, Node):
            yield from elements(child)


def dictionaries(root=ROOT):
    return {language: json.loads((root / "assets/i18n" / (language + ".json")).read_text())
            for language in LANGUAGES}


def absolute_local_url(value):
    address = urlsplit(value)
    if address.scheme or address.netloc or not address.path or address.path.startswith("/"):
        return value
    return urlunsplit(("", "", "/" + address.path, address.query, address.fragment))


def localized_url(value, language):
    address = urlsplit(value)
    if address.scheme or address.netloc:
        return value
    query = dict(parse_qsl(address.query, keep_blank_values=True))
    query["lang"] = language
    return urlunsplit(("", "", address.path, urlencode(query), address.fragment))


def serialize(node, raw=False):
    if isinstance(node, str):
        return node if raw else escape(node, quote=False)
    if node.tag == "#document":
        return "".join(serialize(child) for child in public_children(node))
    if node.tag == "!doctype":
        return "<!DOCTYPE html>"
    attrs = "".join(" " + name + ("" if value is None else '="' + escape(str(value), quote=True) + '"')
                    for name, value in node.attrs.items())
    start = "<" + node.tag + attrs + ">"
    if node.tag in VOID:
        return start
    return start + "".join(serialize(child, node.tag in ("script", "style"))
                           for child in public_children(node)) + "</" + node.tag + ">"


def render_page(page, language="en", root=ROOT):
    """Translate before serving, including metadata, without adding source HTML copies."""
    if page not in PAGES or language not in LANGUAGES:
        raise ValueError("Unsupported page or language")
    document = Document((root / page).read_text())
    dictionary = dictionaries(root)[language]
    canonical = DOMAIN + "/" + page + "?lang=" + language
    for node in elements(document.root):
        key = node.attrs.get("data-i18n")
        if key:
            node.children = [dictionary[key]]
        for attribute, key in json.loads(node.attrs.get("data-i18n-attrs", "{}")).items():
            if attribute not in ATTRIBUTES:
                raise ValueError("Unsupported translation attribute: " + attribute)
            node.attrs[attribute] = dictionary[key]
        if node.tag == "html":
            node.attrs.update({"lang": language, "data-rendered-language": language})
        if "data-localized-link" in node.attrs:
            node.attrs["href"] = localized_url(node.attrs["href"], language)
        if "data-language" in node.attrs:
            link_language = node.attrs["data-language"]
            node.attrs["href"] = localized_url("/" + page, link_language)
            if language == link_language:
                node.attrs["aria-current"] = "page"
            else:
                node.attrs.pop("aria-current", None)
        if node.tag == "link" and node.attrs.get("rel") == "canonical":
            node.attrs["href"] = canonical
        if node.tag == "meta" and node.attrs.get("property") == "og:url":
            node.attrs["content"] = canonical
        if node.tag == "meta" and node.attrs.get("property") == "og:locale":
            node.attrs["content"] = "ky_KG" if language == "ky" else "en_US"
        if node.tag == "meta" and (node.attrs.get("property") in ("og:image", "og:image:secure_url") or
                                   node.attrs.get("name") == "twitter:image"):
            if re.search(r"/social/line-education-(?:en|ky)\.png$", node.attrs.get("content", "")):
                node.attrs["content"] = DOMAIN + "/assets/images/social/line-education-" + language + ".png"
        for attribute in RESOURCE_ATTRIBUTES:
            if attribute in node.attrs:
                node.attrs[attribute] = absolute_local_url(node.attrs[attribute])
        if "srcset" in node.attrs:
            node.attrs["srcset"] = ", ".join(absolute_local_url(part.strip().split()[0]) +
                                                   (" " + " ".join(part.strip().split()[1:])
                                                    if len(part.strip().split()) > 1 else "")
                                                   for part in node.attrs["srcset"].split(","))
        if "style" in node.attrs:
            node.attrs["style"] = CSS_URL.sub(lambda m: "url(" + absolute_local_url(m[2]) + ")",
                                               node.attrs["style"])
    return serialize(document.root)


def used_translation_keys(root=ROOT):
    keys = set()
    for page in PAGES:
        if not (root / page).exists():
            continue
        for node in elements(Document((root / page).read_text()).root):
            if "data-i18n" in node.attrs:
                keys.add(node.attrs["data-i18n"])
            keys.update(json.loads(node.attrs.get("data-i18n-attrs", "{}")).values())
    return keys


def public_dictionary(language, root=ROOT):
    dictionary = dictionaries(root)[language]
    return json.dumps({key: dictionary[key] for key in sorted(used_translation_keys(root))},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def referenced_resources(source):
    for node in elements(Document(source).root):
        for attribute in RESOURCE_ATTRIBUTES:
            value = node.attrs.get(attribute)
            if value and (node.tag != "a" or attribute != "href"):
                yield value
        for part in node.attrs.get("srcset", "").split(","):
            if part.strip():
                yield part.strip().split()[0]
        if node.tag == "meta" and (node.attrs.get("property") in ("og:image", "og:image:secure_url") or
                                   node.attrs.get("name") == "twitter:image"):
            yield node.attrs.get("content", "")
        yield from (match[2] for match in CSS_URL.finditer(node.attrs.get("style", "")))


def asset_path(value, base=Path(".")):
    address = urlsplit(value)
    if (address.scheme or address.netloc) and address.netloc not in ("line.kg", "www.line.kg"):
        return None
    if not address.path:
        return None
    address_path = unquote(address.path)
    path = Path(address_path.lstrip("/")) if address_path.startswith("/") else base / address_path
    path = Path(__import__("posixpath").normpath(path.as_posix()))
    if ".." in path.parts or any(part.startswith(".") for part in path.parts):
        raise ValueError("Unsafe asset path: " + value)
    font_license = path.parent == Path("assets/fonts") and path.name.endswith("OFL.txt")
    if path.parts[0] not in ("assets", "common") or (path.suffix.lower() not in SAFE_ASSET_SUFFIXES and not font_license):
        return None
    return path


def resource_set(root=ROOT):
    queue = deque()
    for page in PAGES:
        if (root / page).exists():
            for language in LANGUAGES:
                queue.extend((value, Path(".")) for value in referenced_resources(render_page(page, language, root)))
    queue.extend(("assets/i18n/" + language + ".json", Path(".")) for language in LANGUAGES)
    found = set()
    while queue:
        value, base = queue.popleft()
        path = asset_path(value, base)
        if path is None or path in found:
            continue
        source = (root / path).resolve()
        if not source.is_relative_to(root.resolve()) or not source.is_file() or source.is_symlink():
            raise ValueError("Missing or unsafe asset: " + str(path))
        found.add(path)
        if path.suffix in (".woff", ".woff2", ".ttf", ".otf") and path.parent == Path("assets/fonts"):
            queue.extend(("/" + license_path.relative_to(root).as_posix(), Path("."))
                         for license_path in (root / path.parent).glob("*OFL.txt"))
        if path.suffix == ".css":
            css = source.read_text()
            queue.extend((match[2], path.parent) for match in CSS_URL.finditer(css))
            queue.extend((match[2], path.parent) for match in CSS_IMPORT.finditer(css))
    return found


def build(root=ROOT, destination=None):
    destination = Path(destination or root / "dist").resolve()
    # A mistake in --output must never delete the repository or arbitrary user files.
    if destination != (root / "dist").resolve():
        raise ValueError("The output directory must be the project's dist directory")
    missing = [page for page in PAGES if not (root / page).is_file()]
    if missing:
        raise ValueError("Missing public pages: " + ", ".join(missing))
    staging = Path(tempfile.mkdtemp(prefix=".linekg-build-", dir=root))
    try:
        for page in PAGES:
            for language in LANGUAGES:
                output = staging / "_localized" / language / page
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_page(page, language, root))
            (staging / page).write_text(render_page(page, "en", root))
        for path in resource_set(root):
            output = staging / path
            output.parent.mkdir(parents=True, exist_ok=True)
            if path.parent == Path("assets/i18n"):
                output.write_bytes(public_dictionary(path.stem, root))
            else:
                shutil.copyfile(root / path, output)
        for name in ("robots.txt", "sitemap.xml"):
            shutil.copyfile(root / name, staging / name)
        for path in list(staging.rglob("*")):
            if path.is_file() and path.suffix in (".html", ".css", ".js", ".json", ".xml", ".txt", ".svg"):
                path.with_name(path.name + ".gz").write_bytes(gzip.compress(path.read_bytes(), compresslevel=9, mtime=0))
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    files = [path for path in destination.rglob("*") if path.is_file()]
    return {"output": str(destination), "files": len(files), "bytes": sum(path.stat().st_size for path in files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build(), indent=2))
