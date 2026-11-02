"""Test-only network hold after a real authorized Java GET; never a production hook."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx


class ReadProxy:
    def __init__(self, port: int, origin: str):
        self.received = threading.Event()
        self.release = threading.Event()
        self.hold = False
        self.import_reads = 0
        self.origin = origin
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def forward(self):
                size = int(self.headers.get("Content-Length", "0"))
                if size > 65536:
                    self.send_error(413)
                    return
                data = self.rfile.read(size)
                headers = {
                    k: v
                    for k, v in self.headers.items()
                    if k.lower() not in {"host", "content-length", "connection"}
                }
                response = httpx.request(
                    self.command,
                    proxy.origin + self.path,
                    content=data,
                    headers=headers,
                    timeout=10,
                    trust_env=False,
                )
                if self.command == "GET" and self.path == "/api/ops/imports":
                    proxy.import_reads += 1
                    if proxy.hold:
                        proxy.received.set()
                        proxy.release.wait(40)
                try:
                    self.send_response(response.status_code)
                    for k, v in response.headers.multi_items():
                        if k.lower() not in {
                            "content-length",
                            "transfer-encoding",
                            "connection",
                            "content-encoding",
                        }:
                            self.send_header(k, v)
                    self.send_header("Content-Length", str(len(response.content)))
                    self.end_headers()
                    self.wfile.write(response.content)
                except ConnectionError:
                    pass

            do_GET = forward
            do_POST = forward
            # Explicit operator fixture setup may activate/deactivate a profile.
            # This test-only relay does not change the AI tool transport allowlist.
            do_PATCH = forward

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
