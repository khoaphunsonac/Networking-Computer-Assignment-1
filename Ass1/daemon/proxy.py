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
daemon.proxy
~~~~~~~~~~~~~~~~~

Simple reverse proxy server using socket + threading.
"""

import socket
import threading

PROXY_PASS = {
    "127.0.0.1:8080": ("127.0.0.1", 9000),
    "app1.local": ("127.0.0.1", 9001),
    "app2.local": ("127.0.0.1", 9002),
    "sampleapp.local": ("127.0.0.1", 2026),
}

_rr_state = {}
_rr_lock = threading.Lock()


def _build_notfound_response():
    return (
        "HTTP/1.1 404 Not Found\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 13\r\n"
        "Connection: close\r\n"
        "\r\n"
        "404 Not Found"
    ).encode("utf-8")


def forward_request(host, port, request_bytes):
    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backend.settimeout(5)

    try:
        backend.connect((host, port))
        backend.sendall(request_bytes)

        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
        return response
    except socket.error as e:
        print("[Proxy] Socket error: {}".format(e))
        return _build_notfound_response()
    finally:
        backend.close()


def resolve_routing_policy(hostname, routes):
    proxy_map, policy = routes.get(hostname, ("127.0.0.1:9000", "round-robin"))

    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            return "127.0.0.1", 9000

        if len(proxy_map) == 1:
            selected = proxy_map[0]
        else:
            # Default policy: round-robin for multi backend alternatives.
            if policy != "round-robin":
                selected = proxy_map[0]
            else:
                with _rr_lock:
                    idx = _rr_state.get(hostname, 0)
                    selected = proxy_map[idx % len(proxy_map)]
                    _rr_state[hostname] = (idx + 1) % len(proxy_map)

        host, port = selected.split(":", 1)
        return host, int(port)

    host, port = proxy_map.split(":", 1)
    return host, int(port)


def _recv_http_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > 10 * 1024 * 1024:
            break

    if not data:
        return b"", ""

    header_part, _, body = data.partition(b"\r\n\r\n")
    headers_text = header_part.decode("utf-8", errors="replace")

    host = ""
    content_length = 0
    for line in headers_text.split("\r\n"):
        lower_line = line.lower()
        if lower_line.startswith("host:"):
            host = line.split(":", 1)[1].strip()
        elif lower_line.startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                content_length = 0

    while len(body) < content_length:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk

    return header_part + b"\r\n\r\n" + body, host


def handle_client(ip, port, conn, addr, routes):
    request_bytes, hostname = _recv_http_request(conn)
    if not request_bytes:
        conn.close()
        return

    print("[Proxy] {} at Host: {}".format(addr, hostname))

    try:
        resolved_host, resolved_port = resolve_routing_policy(hostname, routes)
    except Exception as e:
        print("[Proxy] route resolve error: {}".format(e))
        resolved_host, resolved_port = "127.0.0.1", 9000

    if resolved_host:
        print(
            "[Proxy] Host name {} is forwarded to {}:{}".format(
                hostname, resolved_host, resolved_port
            )
        )
        response = forward_request(resolved_host, resolved_port, request_bytes)
    else:
        response = _build_notfound_response()

    conn.sendall(response)
    conn.close()


def run_proxy(ip, port, routes):
    # TODO(student): keep one worker thread per accepted client for concurrent proxy forwarding.
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)
        print("[Proxy] Listening on IP {} port {}".format(ip, port))
        while True:
            conn, addr = proxy.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(ip, port, conn, addr, routes),
                daemon=True,
            )
            client_thread.start()
    except socket.error as e:
        print("Socket error: {}".format(e))
    finally:
        proxy.close()


def create_proxy(ip, port, routes):
    run_proxy(ip, port, routes)
