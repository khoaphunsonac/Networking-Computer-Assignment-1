#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a Response object to manage and persist response settings
and to construct HTTP responses based on incoming requests.
"""

import datetime
import json
import mimetypes
import os
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""


class Response:
    """Container used to construct HTTP responses."""

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
    ]

    def __init__(self, request=None):
        self._content = b""
        self._header = b""
        self._content_consumed = False
        self._next = None

        self.status_code = 200
        self.method = None
        self.headers = CaseInsensitiveDict()
        self.url = None
        self.encoding = "utf-8"
        self.history = []
        self.reason = "OK"
        self.cookies = CaseInsensitiveDict()
        self.elapsed = datetime.timedelta(0)
        self.request = request

    def get_mime_type(self, path):
        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return "application/octet-stream"
        return mime_type or "application/octet-stream"

    def prepare_content_type(self, mime_type="text/html"):
        main_type, sub_type = mime_type.split("/", 1)

        base_dir = ""
        if main_type == "text":
            if sub_type == "html":
                base_dir = BASE_DIR + "www/"
            else:
                base_dir = BASE_DIR + "static/"
            self.headers["Content-Type"] = f"text/{sub_type}"
        elif main_type in ["image", "video", "audio", "font"]:
            base_dir = BASE_DIR + "static/"
            self.headers["Content-Type"] = f"{main_type}/{sub_type}"
        elif main_type == "application":
            # JSON response from route handlers does not need file fetch.
            if sub_type == "json":
                base_dir = ""
            else:
                base_dir = BASE_DIR + "static/"
            self.headers["Content-Type"] = f"application/{sub_type}"
        else:
            self.headers["Content-Type"] = "application/octet-stream"
            base_dir = BASE_DIR + "static/"

        return base_dir

    def build_content(self, path, base_dir):
        filepath = os.path.join(base_dir, path.lstrip("/"))
        try:
            with open(filepath, "rb") as f:
                content = f.read()
        except Exception:
            return -1, b""
        return len(content), content

    def build_response_header(self, request):
        reqhdr = request.headers if request and request.headers else CaseInsensitiveDict()

        # Normalize content to bytes before calculating content-length.
        if isinstance(self._content, str):
            body = self._content.encode("utf-8")
        else:
            body = self._content or b""
        self._content = body

        status_line = f"HTTP/1.1 {self.status_code} {self.reason}\r\n"
        headers = {
            "Content-Type": self.headers.get("Content-Type", "text/plain; charset=utf-8"),
            "Content-Length": str(len(body)),
            "Connection": "close",
            "Date": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Server": "AsynapRous/1.0",
            "Cache-Control": "no-cache",
            "User-Agent": reqhdr.get("User-Agent", "AsynapRous-Client"),
        }

        for key, value in self.headers.items():
            if key not in headers:
                headers[key] = value

        auth = reqhdr.get("Authorization")
        if auth:
            headers["Authorization"] = auth

        lines = [status_line]
        for key, value in headers.items():
            lines.append(f"{key}: {value}\r\n")
        lines.append("\r\n")

        return "".join(lines).encode("utf-8")

    def build_notfound(self):
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode("utf-8")

    def build_response(self, request, envelop_content=None):
        path = request.path if request else "/"
        mime_type = self.get_mime_type(path)

        # Hook response from RESTful app.
        if envelop_content is not None:
            if isinstance(envelop_content, dict):
                envelop_content = json.dumps(envelop_content)
            if isinstance(envelop_content, str):
                self._content = envelop_content.encode("utf-8")
            else:
                self._content = envelop_content

            if self.headers.get("Content-Type") is None:
                self.prepare_content_type("application/json")

            self.status_code = 200
            self.reason = "OK"
            self._header = self.build_response_header(request)
            return self._header + self._content

        if path.endswith(".html") or mime_type == "text/html":
            base_dir = self.prepare_content_type("text/html")
        elif mime_type == "text/css":
            base_dir = self.prepare_content_type("text/css")
        elif mime_type.startswith("text/"):
            base_dir = self.prepare_content_type(mime_type)
        elif mime_type.startswith("image/"):
            base_dir = self.prepare_content_type(mime_type)
        elif mime_type.startswith("video/"):
            base_dir = self.prepare_content_type(mime_type)
        elif mime_type.startswith("application/"):
            base_dir = self.prepare_content_type(mime_type)
        else:
            base_dir = self.prepare_content_type("application/octet-stream")

        content_length, content = self.build_content(path, base_dir)
        if content_length < 0:
            return self.build_notfound()

        self._content = content
        self.status_code = 200
        self.reason = "OK"
        self._header = self.build_response_header(request)

        return self._header + self._content
