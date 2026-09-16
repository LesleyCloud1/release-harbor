"""Loopback-only dashboard/API. Run: python -m harbor.server."""
import argparse
import hmac
import json
import os
import secrets
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from harbor.engine import Conflict, Engine

STATIC = Path(__file__).with_name('static')

def make_server(engine, token, port=8088, host='127.0.0.1'):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/healthz':
                return self.send(200, {'healthy': True})
            if path == '/api/state':
                return self.send(200, engine.snapshot())
            if path == '/demo':
                try:
                    return self.send(200, engine.proxy())
                except Conflict as exc:
                    return self.send(503, {'error': str(exc)})
                except Exception:
                    return self.send(502, {'error': 'Active workload is unavailable.'})
            if path == '/metrics':
                counts = engine.snapshot()['counts']
                metrics = '# HELP harbor_deployments_total Recorded deployments by final or current status.\n# TYPE harbor_deployments_total gauge\n'
                metrics += ''.join(f'harbor_deployments_total{{status="{k}"}} {v}\n' for k, v in sorted(counts.items()))
                return self.send(200, metrics.encode(), 'text/plain; version=0.0.4')
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path in assets:
                name, mime = assets[path]
                return self.send(200, (STATIC / name).read_bytes(), mime)
            self.send(404, {'error': 'Route not found.'})

        def do_POST(self):
            expected_host = f'127.0.0.1:{self.server.server_port}'
            hosts = {expected_host, f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in hosts:
                return self.send(403, {'error': 'Use the local dashboard address.'})
            origin = self.headers.get('Origin')
            if origin and origin not in {f'http://{host}' for host in hosts}:
                return self.send(403, {'error': 'Cross-origin requests are not allowed.'})
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + token).encode()):
                return self.send(401, {'error': 'Enter the operator key printed in your terminal.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 4096:
                    return self.send(413, {'error': 'Request is too large.'})
                data = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object.')
                if self.path == '/api/deploy':
                    version = data.get('version')
                    if not isinstance(version, str):
                        raise ValueError('A release version is required.')
                    ident = engine.deploy(version)
                elif self.path == '/api/rollback':
                    ident = engine.rollback()
                else:
                    return self.send(404, {'error': 'Route not found.'})
                self.send(202, {'id': ident})
            except Conflict as exc:
                self.send(409, {'error': str(exc)})
            except (ValueError, TypeError) as exc:
                self.send(400, {'error': str(exc)})

        def log_message(self, fmt, *args):
            pass
    return ThreadingHTTPServer((host, port), Handler)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=['127.0.0.1', '0.0.0.0'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--database', default='.harbor/state.db')
    args = parser.parse_args()
    Path(args.database).parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get('HARBOR_TOKEN') or secrets.token_urlsafe(24)
    if len(token) < 16:
        parser.error('HARBOR_TOKEN must contain at least 16 characters.')
    engine = Engine(args.database)
    server = make_server(engine, token, args.port, args.host)
    def shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f'Release Harbor: http://127.0.0.1:{server.server_port}\nOperator key: {token}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close(); engine.close()

if __name__ == '__main__':
    main()
