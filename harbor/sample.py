"""A real HTTP workload, launched as a separate process for each candidate."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

version = sys.argv[1]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        healthy = version != 'v3-broken'
        payload = {'service': 'catalog-demo', 'version': version, 'healthy': healthy,
                   'products': [{'name': 'Canvas backpack', 'price': 48},
                                {'name': 'Desk lamp', 'price': 32 if version == 'v1' else 29}]}
        body = json.dumps(payload).encode()
        self.send_response(200 if healthy else 503)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer((os.environ.get('SAMPLE_HOST', '127.0.0.1'), int(os.environ.get('SAMPLE_PORT', '0'))), Handler)
print(server.server_port, flush=True)
server.serve_forever()
