#!/usr/bin/env python3
"""Preview only public site files on localhost, with publishing-equivalent headers.

Run: python3 tools/preview.py --port 8765
This is a development server; production uses the supplied Nginx configuration.
"""

import argparse
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from build import LANGUAGES, PAGES, ROOT, public_dictionary, render_page, resource_set


CSP = "; ".join((
    "default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:", "font-src 'self'", "connect-src 'self'",
    "object-src 'none'", "frame-src 'none'", "frame-ancestors 'none'",
    "base-uri 'none'", "form-action 'none'",
))
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
LEGACY = {"/indexkg.html": "/index.html?lang=ky", "/contactkg.html": "/contact.html?lang=ky"}


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = "LinePreview"
    sys_version = ""

    def security_headers(self):
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)

    def respond(self, status, body, content_type, head=False, cache="no-cache"):
        if "gzip" in self.headers.get("Accept-Encoding", "") and len(body) > 1024 and (
                content_type.startswith("text/") or content_type.split(";")[0] in (
                    "application/javascript", "application/json", "application/xml", "image/svg+xml")):
            body = gzip.compress(body, compresslevel=6, mtime=0)
            encoding = "gzip"
        else:
            encoding = None
        self.send_response(status)
        self.security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("ETag", '"' + hashlib.sha256(body).hexdigest()[:20] + '"')
        if encoding:
            self.send_header("Content-Encoding", encoding)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def missing(self, language, head=False):
        self.respond(404, render_page("404.html", language).encode("utf-8"),
                     "text/html; charset=utf-8", head)

    def handle_public_request(self, head=False):
        address = urlsplit(self.path)
        path = unquote(address.path)
        language = parse_qs(address.query).get("lang", ["en"])[0]
        if language not in LANGUAGES:
            language = "en"
        if path in LEGACY:
            self.send_response(301)
            self.security_headers()
            self.send_header("Location", LEGACY[path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/":
            path = "/index.html"
        if "\x00" in path or "\\" in path or any(part in (".", "..") for part in path.split("/")):
            self.missing(language, head)
            return
        page = path.lstrip("/")
        if path == "/" + page and page in PAGES:
            self.respond(404 if page == "404.html" else 200,
                         render_page(page, language).encode("utf-8"), "text/html; charset=utf-8", head)
            return
        relative = Path(path.lstrip("/"))
        if relative not in self.server.public_assets and relative.as_posix() not in ("robots.txt", "sitemap.xml"):
            self.missing(language, head)
            return
        resource = (ROOT / relative).resolve()
        if not resource.is_relative_to(ROOT.resolve()) or not resource.is_file():
            self.missing(language, head)
            return
        if relative.parent == Path("assets/i18n"):
            body = public_dictionary(relative.stem)
        else:
            body = resource.read_bytes()
        content_type = mimetypes.guess_type(resource.name)[0] or "application/octet-stream"
        if resource.suffix == ".js":
            content_type = "application/javascript"
        if content_type.startswith("text/") or resource.suffix in (".js", ".json", ".xml", ".svg"):
            content_type += "; charset=utf-8"
        self.respond(200, body, content_type, head)

    def do_GET(self):
        self.handle_public_request()

    def do_HEAD(self):
        self.handle_public_request(head=True)

    def unsupported_method(self):
        self.send_response(405)
        self.security_headers()
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = unsupported_method
    do_PUT = unsupported_method
    do_DELETE = unsupported_method
    do_PATCH = unsupported_method
    do_TRACE = unsupported_method
    do_OPTIONS = unsupported_method


def create_server(port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)
    server.public_assets = resource_set()
    server.daemon_threads = True
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with create_server(args.port) as preview:
        print("Line Education preview: http://127.0.0.1:" + str(preview.server_port), flush=True)
        try:
            preview.serve_forever()
        except KeyboardInterrupt:
            pass
