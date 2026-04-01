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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

HTTP adapter for handling client connections and dispatching routes.
"""

from .request import Request
from .response import Response

import asyncio
import base64
import inspect


class HttpAdapter:
    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        self.ip = ip
        self.port = port
        self.conn = conn
        self.connaddr = connaddr
        self.routes = routes or {}
        self.request = Request()
        self.response = Response()

    def _read_http_request(self, conn):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > 10 * 1024 * 1024:
                break

        if not data:
            return ""

        header_part, _, body_part = data.partition(b"\r\n\r\n")
        headers_text = header_part.decode("utf-8", errors="replace")

        content_length = 0
        for line in headers_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = 0
                break

        while len(body_part) < content_length:
            chunk = conn.recv(4096)
            if not chunk:
                break
            body_part += chunk

        return (header_part + b"\r\n\r\n" + body_part).decode("utf-8", errors="replace")

    def _call_hook_sync(self, hook, req, resp):
        if inspect.iscoroutinefunction(hook):
            try:
                return asyncio.run(hook(req.headers, req.body))
            except TypeError:
                return asyncio.run(hook(req, resp))

        try:
            return hook(req.headers, req.body)
        except TypeError:
            return hook(req, resp)

    async def _call_hook_async(self, hook, req, resp):
        # Async hook
        if inspect.iscoroutinefunction(hook):
            try:
                return await hook(req.headers, req.body)
            except TypeError:
                return await hook(req, resp)

        # Sync hook in coroutine context
        return self._call_hook_sync(hook, req, resp)

    def handle_client(self, conn, addr, routes):
        self.conn = conn
        self.connaddr = addr
        self.routes = routes or {}

        req = self.request
        resp = self.response

        raw_msg = self._read_http_request(conn)
        if not raw_msg:
            conn.close()
            return

        req.prepare(raw_msg, self.routes)

        envelop_content = None
        if req.hook:
            envelop_content = self._call_hook_sync(req.hook, req, resp)
            if envelop_content is not None and resp.headers.get("Content-Type") is None:
                resp.headers["Content-Type"] = "application/json; charset=utf-8"

        response = resp.build_response(req, envelop_content=envelop_content)
        if isinstance(response, str):
            response = response.encode("utf-8")

        conn.sendall(response)
        conn.close()

    async def handle_client_coroutine(self, reader, writer):
        req = self.request
        resp = self.response

        raw_data = await reader.read(4096)
        if not raw_data:
            writer.close()
            await writer.wait_closed()
            return

        req.prepare(raw_data.decode("utf-8", errors="replace"), self.routes)

        envelop_content = None
        if req.hook:
            envelop_content = await self._call_hook_async(req.hook, req, resp)
            if envelop_content is not None and resp.headers.get("Content-Type") is None:
                resp.headers["Content-Type"] = "application/json; charset=utf-8"

        response = resp.build_response(req, envelop_content=envelop_content)
        writer.write(response)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    def add_headers(self, request):
        pass

    def build_proxy_headers(self, proxy):
        """Build proxy headers with basic authentication credentials."""
        headers = {}

        username = "user1"
        password = "password"
        if username and password:
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            headers["Proxy-Authorization"] = f"Basic {encoded}"

        return headers
