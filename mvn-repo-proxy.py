#!/usr/bin/env python3
"""Local Maven repo proxy: tries backends in order (Central -> Shibboleth -> JBoss)
and returns the first 200 response. Point a settings.xml <mirror>/<repository> at
this server. See README.md for why this exists and how to wire it up.
"""
import http.server
import os
import sys
import urllib.error
import urllib.request

PORT = int(os.environ.get("PROXY_PORT", "8477"))
TIMEOUT = float(os.environ.get("PROXY_BACKEND_TIMEOUT", "5"))

BACKENDS = [
    "https://repo.maven.apache.org/maven2",
    "https://build.shibboleth.net/nexus/content/repositories/releases",
    "https://repository.jboss.org/nexus/content/groups/public",
]


class Handler(http.server.BaseHTTPRequestHandler):
    def _proxy(self, method):
        for backend in BACKENDS:
            url = backend + self.path
            try:
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    body = resp.read() if method == "GET" else b""
                    self.send_response(200)
                    ctype = resp.headers.get("Content-Type", "application/octet-stream")
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    if method == "GET":
                        self.wfile.write(body)
                    print(f"[OK]   {method} {self.path} -> {backend}", file=sys.stderr)
                    return
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    print(f"[WARN] {method} {self.path} -> {backend} ({e.code})", file=sys.stderr)
                continue
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"[WARN] {method} {self.path} -> {backend} unreachable ({e})", file=sys.stderr)
                continue

        print(f"[404]  {method} {self.path} (tried {len(BACKENDS)} backends)", file=sys.stderr)
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        self._proxy("GET")

    def do_HEAD(self):
        self._proxy("HEAD")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Maven fallback proxy listening on http://127.0.0.1:{PORT}", file=sys.stderr)
    for b in BACKENDS:
        print(f"  backend: {b}", file=sys.stderr)
    server.serve_forever()
