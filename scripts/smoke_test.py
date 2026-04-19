import socket
import subprocess
import sys
import time
from http.client import HTTPConnection
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ASS1_DIR = ROOT_DIR / "Ass1"


def wait_port(host: str, port: int, timeout: float = 8.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        sock = socket.socket()
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            time.sleep(0.2)
        finally:
            sock.close()
    return False


def request(name: str, method: str, path: str, port: int, headers=None, body=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    payload = response.read().decode("utf-8", errors="replace")
    conn.close()

    status_ok = response.status == 200
    print(f"[{name}] status={response.status} ok={status_ok}")
    if not status_ok:
        print(f"[{name}] body={payload[:300]}")
    return status_ok


def start_server(args):
    return subprocess.Popen(
        args,
        cwd=str(ASS1_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    processes = []
    try:
        processes.append(
            start_server(
                ["python", "start_backend.py", "--server-ip", "127.0.0.1", "--server-port", "9000"]
            )
        )
        if not wait_port("127.0.0.1", 9000):
            print("Backend did not start on 9000")
            return 1

        processes.append(
            start_server(
                ["python", "start_sampleapp.py", "--server-ip", "127.0.0.1", "--server-port", "2026"]
            )
        )
        if not wait_port("127.0.0.1", 2026):
            print("Sample app did not start on 2026")
            return 1

        processes.append(
            start_server(
                ["python", "start_proxy.py", "--server-ip", "127.0.0.1", "--server-port", "8080"]
            )
        )
        if not wait_port("127.0.0.1", 8080):
            print("Proxy did not start on 8080")
            return 1

        checks = [
            request("BACKEND_ROOT", "GET", "/", 9000),
            request("BACKEND_LOGIN_HTML", "GET", "/login.html", 9000),
            request("APP_LOGIN", "POST", "/login", 2026),
            request(
                "APP_ECHO",
                "POST",
                "/echo",
                2026,
                headers={"Content-Type": "application/json"},
                body='{"msg":"hello"}',
            ),
            request("APP_HELLO", "PUT", "/hello", 2026),
            request(
                "PROXY_ROOT",
                "GET",
                "/",
                8080,
                headers={"Host": "127.0.0.1:8080"},
            ),
            request(
                "PROXY_APP_LOGIN",
                "POST",
                "/login",
                8080,
                headers={"Host": "sampleapp.local"},
            ),
        ]

        if all(checks):
            print("Smoke test PASSED")
            return 0
        print("Smoke test FAILED")
        return 1
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        time.sleep(0.5)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
