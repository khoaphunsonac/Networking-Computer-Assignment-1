#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist
request settings (cookies, auth, proxies).
"""

from .dictionary import CaseInsensitiveDict


class Request:
    """A mutable HTTP request object parsed from a raw HTTP message."""

    __attrs__ = [
        "method",
        "url",
        "path",
        "version",
        "headers",
        "body",
        "_raw_headers",
        "_raw_body",
        "cookies",
        "routes",
        "hook",
        "auth",
    ]

    def __init__(self):
        self.method = None
        self.url = None
        self.path = None
        self.version = "HTTP/1.1"
        self.headers = CaseInsensitiveDict()
        self.cookies = CaseInsensitiveDict()
        self.body = ""
        self._raw_headers = ""
        self._raw_body = ""
        self.routes = {}
        self.hook = None
        self.auth = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()
            if path == "/":
                path = "/index.html"
            return method.upper(), path, version
        except Exception:
            return None, None, None

    def fetch_headers_body(self, request):
        parts = request.split("\r\n\r\n", 1)
        headers = parts[0] if parts else ""
        body = parts[1] if len(parts) > 1 else ""
        return headers, body

    def prepare_headers(self, raw_headers):
        headers = CaseInsensitiveDict()
        lines = raw_headers.split("\r\n")
        for line in lines[1:]:
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()
        return headers

    def _parse_cookies(self, cookie_header):
        cookies = CaseInsensitiveDict()
        if not cookie_header:
            return cookies

        for pair in cookie_header.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key.strip()] = value.strip()
            else:
                cookies[pair] = ""
        return cookies

    def prepare(self, request, routes=None):
        """Parse a raw HTTP request string and bind optional route hook."""
        # TODO(student): ensure cookie parsing is complete and supports common header formats.

        self.method, self.path, self.version = self.extract_request_line(request)
        self.url = self.path

        self._raw_headers, self._raw_body = self.fetch_headers_body(request)
        self.headers = self.prepare_headers(self._raw_headers)
        self.body = self._raw_body

        cookie_header = self.headers.get("Cookie", "")
        self.cookies = self._parse_cookies(cookie_header)

        routes = routes or {}
        self.routes = routes
        self.hook = None
        if self.method and self.path and routes:
            self.hook = routes.get((self.method, self.path))

        return self

    def prepare_body(self, body, files=None, json=None):
        if body is None:
            body = ""
        if isinstance(body, bytes):
            self.body = body.decode("utf-8", errors="replace")
        else:
            self.body = str(body)
        self.prepare_content_length(self.body)
        return self

    def prepare_content_length(self, body):
        if body is None:
            length = 0
        elif isinstance(body, bytes):
            length = len(body)
        else:
            length = len(str(body).encode("utf-8"))

        self.headers["Content-Length"] = str(length)
        return self

    def prepare_auth(self, auth, url=""):
        self.auth = auth
        return self

    def prepare_cookies(self, cookies):
        if not cookies:
            return self

        if isinstance(cookies, dict):
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        else:
            cookie_header = str(cookies)

        self.headers["Cookie"] = cookie_header
        self.cookies = self._parse_cookies(cookie_header)
        return self
