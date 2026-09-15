from __future__ import annotations

import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE = Path(__file__).resolve().parent / "fixtures"


class BenchmarkHandler(BaseHTTPRequestHandler):
    def _send_file(self, path: Path, status: int = 200) -> None:
        body = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/static":
            self._send_file(BASE / "static" / "valid.html")
            return

        if self.path == "/structured":
            self._send_file(BASE / "structured" / "jsonld.html")
            return

        if self.path == "/thin":
            self._send_file(BASE / "thin" / "empty.html")
            return

        if self.path == "/js-shell":
            self._send_file(BASE / "thin" / "js_shell.html")
            return

        if self.path == "/browser-interaction":
            self._send_file(BASE / "thin" / "browser_interaction.html")
            return

        if self.path == "/static/app.js":
            body = (BASE / "thin" / "app.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/error":
            self._send_file(BASE / "error" / "error.html", status=500)
            return

        if self.path == "/slow":
            time.sleep(0.25)
            self._send_file(BASE / "slow" / "slow.html")
            return

        if self.path.startswith("/multi/"):
            self._send_file(BASE / "static" / "valid.html")
            return

        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BenchmarkHandler)
    print(f"Benchmark server listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
