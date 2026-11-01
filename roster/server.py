"""Serve the game launcher and read-only roster API with the upstream COOP/COEP headers."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import urllib.parse
import socket

from .refresh import OUTPUT, ROOT, refresh

sys.path.insert(0, str(ROOT / "web"))
from serve import Handler as GameHandler  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

LAUNCH_LOCK = threading.Lock()
LOCAL = ROOT / 'local_runtime'


class LocalServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR permits competing listeners rather than just restart reuse.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(GameHandler):
    def do_POST(self):
        if self.path != '/api/launch':
            self.send_error(404)
            return
        # This server binds loopback. Refuse cross-origin requests that could trigger work.
        if self.headers.get('Origin') not in (None, f'http://{self.headers.get("Host")}'):
            self.send_error(403)
            return
        if not LAUNCH_LOCK.acquire(blocking=False):
            self.reply_json(409, {'error': 'A roster refresh is already in progress. Wait for it to finish, then reload.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 1024:
                raise ValueError('Invalid launch request')
            options = json.loads(self.rfile.read(size))
            format_name = options.get('format', 'ODI')
            if format_name not in ('Test', 'ODI', 'T20'):
                raise ValueError('Unknown format')
            warning = None
            try:
                snapshot = refresh()
            except Exception as error:
                if not OUTPUT.exists():
                    raise
                snapshot = json.loads(OUTPUT.read_text(encoding='utf-8'))
                warning = f'Live refresh failed; using snapshot {snapshot["asOf"]}. {error}'
            from .game_patch import prepare
            result = prepare(snapshot, format_name)
            result['warning'] = warning
            self.reply_json(200, result)
        except Exception as error:
            self.reply_json(500, {'error': str(error)})
        finally:
            LAUNCH_LOCK.release()

    def reply_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith('/assets/teams/') and path.endswith('.png'):
            slug = path[len('/assets/teams/'):-4]
            from .teams import TEAMS
            if slug not in {code for _,code in TEAMS.values()}:
                self.send_error(404)
                return
            from PIL import Image
            from .logos import transparent_background
            import io
            target = ROOT / 'web/assets/teams' / (slug + '.png')
            if not target.exists():
                self.send_error(404)
                return
            output = io.BytesIO()
            with Image.open(target) as source:
                transparent_background(source).save(output, format='PNG')
            body = output.getvalue()
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ('/play/', '/play/index.html', '/play/c07.js'):
            target = LOCAL / 'web' / ('c07.js' if path.endswith('c07.js') else 'index.html')
            if not target.exists():
                self.send_error(503, 'Run python tools/setup_local.py first')
                return
            source = target.read_text(encoding='utf-8')
            if path.endswith('c07.js'):
                source = source.replace("async function run(session) {", "async function run(session) {\n  if (window.revampLaunching) return;\n  window.revampLaunching = true;\n  if (session) throw new Error('Local roster testing supports solo play.');\n  $('play').disabled = true;\n  try { await window.revampBeforeLaunch(); } catch (error) { window.revampLaunching = false; $('play').disabled = false; throw error; }")
            else:
                controls = '<div style="position:fixed;top:12px;left:12px;z-index:30;background:#111c16;padding:10px;border-radius:8px"><label>Roster format <select id="revamp-format"><option>Test</option><option selected>ODI</option><option>T20</option></select></label> <a href="/rosters.html" style="color:#6de1b0">Player preview</a><p id="revamp-message" style="font-size:12px">Live roster refresh runs when you press Play Solo.</p></div>'
                source = source.replace('<body>', '<body>' + controls)
                source = source.replace('<span id="visits">2,693,467 visits</span>', '')
                import re
                source = re.sub(r'<script type="module" src="https://static.cloudflareinsights.com/[^>]+></script>', '', source)
                source = source.replace('<script src="c07.js"></script>', '<script src="/local-launch.js"></script><script src="c07.js"></script>')
            body = source.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
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
        p = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        if p.startswith('/play/game/'):
            target = LOCAL / 'game' / p[len('/play/game/'):]
        elif p.startswith('/local-game/'):
            target = LOCAL / 'prepared' / p[len('/local-game/'):]
        elif p.startswith('/play/'):
            target = LOCAL / 'web' / p[len('/play/'):]
        else:
            target = Path(super().translate_path(path))
        target = target.resolve()
        roots = (ROOT / "web", ROOT / "build_web" / "www", LOCAL / 'web', LOCAL / 'game', LOCAL / 'prepared')
        if not any(target.is_relative_to(root.resolve()) for root in roots):
            return str(ROOT / "web" / ".not-found")
        return str(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8007)
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()
    # Starting the server can use the saved preview. Play Solo always refreshes.
    needs_refresh = not OUTPUT.exists()
    if needs_refresh and not args.no_refresh:
        try:
            refresh()
        except Exception as error:
            print(f"Refresh failed; keeping previous snapshot if available: {error}", flush=True)
    server = LocalServer(("127.0.0.1", args.port), Handler)
    print(f"Roster preview: http://localhost:{args.port}/rosters.html", flush=True)
    print(f"Play locally: http://localhost:{args.port}/play/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
