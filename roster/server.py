"""Serve the game launcher and read-only roster API with the upstream COOP/COEP headers."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .refresh import OUTPUT, ROOT, refresh

sys.path.insert(0, str(ROOT / "web"))
from serve import Handler as GameHandler  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402


class Handler(GameHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/api/rosters":
            if not OUTPUT.exists():
                self.send_error(503, "No roster snapshot. Run python -m roster.refresh first.")
                return
            body = OUTPUT.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def translate_path(self, path):
        # Keep static requests inside the selected public root.
        target = Path(super().translate_path(path)).resolve()
        roots = (ROOT / "web", ROOT / "build_web" / "www")
        if not any(target.is_relative_to(root.resolve()) for root in roots):
            return str(ROOT / "web" / ".not-found")
        return str(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8007)
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()
    # Fetch at most daily at launch. A failure retains the previous dated snapshot.
    needs_refresh = True
    try:
        saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
        needs_refresh = saved["asOf"] != datetime.now(timezone.utc).date().isoformat()
    except (OSError, ValueError, KeyError):
        pass
    if needs_refresh and not args.no_refresh:
        try:
            refresh()
        except Exception as error:
            print(f"Refresh failed; keeping previous snapshot if available: {error}", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Roster preview: http://localhost:{args.port}/rosters.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
