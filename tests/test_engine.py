import json
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from harbor.engine import Conflict, Engine
from harbor.server import make_server

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(self.tmp.name + '/test.db', probe_timeout=.8)
    def tearDown(self):
        self.engine.close(); self.tmp.cleanup()
    def wait(self):
        self.engine.worker.join(timeout=5)
        self.assertFalse(self.engine.busy, 'worker did not finish')
    def test_healthy_release_serves_real_workload(self):
        self.engine.deploy('v1'); self.wait()
        self.assertEqual(self.engine.proxy()['version'], 'v1')
        self.assertEqual(self.engine.snapshot()['deployments'][0]['status'], 'succeeded')
    def test_failed_candidate_preserves_active_process(self):
        self.engine.deploy('v1'); self.wait()
        previous = self.engine.active['process']
        self.engine.deploy('v3-broken'); self.wait()
        self.assertIs(self.engine.active['process'], previous)
        self.assertEqual(self.engine.proxy()['version'], 'v1')
        self.assertEqual(self.engine.snapshot()['deployments'][0]['status'], 'failed')
    def test_rollback_rechecks_previous_release_and_retires_old_process(self):
        self.engine.deploy('v1'); self.wait()
        old = self.engine.active['process']
        self.engine.deploy('v2'); self.wait()
        self.assertIsNotNone(old.poll())
        self.engine.rollback(); self.wait()
        self.assertEqual(self.engine.proxy()['version'], 'v1')
        self.assertEqual(self.engine.snapshot()['deployments'][0]['kind'], 'rollback')
    def test_concurrent_request_is_rejected(self):
        self.engine.deploy('v1')
        with self.assertRaises(Conflict): self.engine.deploy('v2')
        self.wait()
    def test_unknown_release_and_missing_rollback_are_rejected(self):
        with self.assertRaises(ValueError): self.engine.deploy('; touch /tmp/nope')
        with self.assertRaises(Conflict): self.engine.rollback()
        self.assertEqual(len(self.engine.snapshot()['deployments']), 0)
    def test_restart_keeps_history_but_not_stale_runtime(self):
        self.engine.deploy('v1'); self.wait()
        self.engine.close()
        self.engine = Engine(self.tmp.name + '/test.db')
        state = self.engine.snapshot()
        self.assertEqual(state['counts']['succeeded'], 1)
        self.assertIsNone(state['active'])
    def test_crash_recovery_marks_incomplete_deployment(self):
        self.engine.db.execute("INSERT INTO deployments VALUES('old','v1','deploy','checking','yesterday',NULL,'digest','')")
        self.engine.db.commit(); self.engine.close()
        self.engine = Engine(self.tmp.name + '/test.db')
        self.assertEqual(self.engine.snapshot()['deployments'][0]['status'], 'interrupted')

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(':memory:', probe_timeout=.8)
        self.token = 'test-operator-token-123456'
        self.server = make_server(self.engine, self.token, 0)
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.engine.close()
    def post(self, path, data, auth=True, origin=None):
        headers = {'Content-Type': 'application/json'}
        if auth: headers['Authorization'] = 'Bearer ' + self.token
        if origin: headers['Origin'] = origin
        try:
            r = urlopen(Request(self.base + path, json.dumps(data).encode(), headers), timeout=3)
        except HTTPError as exc: r = exc
        with r: return r.status, json.load(r)
    def test_writes_require_operator_token(self):
        code, _ = self.post('/api/deploy', {'version': 'v1'}, auth=False)
        self.assertEqual(code, 401)
        self.assertFalse(self.engine.busy)
    def test_cross_origin_write_rejected_even_with_token(self):
        code, _ = self.post('/api/deploy', {'version': 'v1'}, origin='https://other.example')
        self.assertEqual(code, 403)
    def test_invalid_payload_does_not_crash_handler(self):
        for data in ([], {'version': []}, {'version': 'unknown'}):
            code, _ = self.post('/api/deploy', data)
            self.assertEqual(code, 400)
    def test_api_deployment_and_live_route(self):
        code, result = self.post('/api/deploy', {'version': 'v2'})
        self.assertEqual(code, 202); self.assertIn('id', result)
        self.engine.worker.join(5)
        with urlopen(self.base + '/demo') as r:
            self.assertEqual(json.load(r)['version'], 'v2')
        with urlopen(self.base + '/metrics') as r:
            self.assertIn(b'status="succeeded"} 1', r.read())
    def test_static_path_is_not_arbitrary_file_access(self):
        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.base + '/../../harbor/server.py')
        self.assertEqual(ctx.exception.code, 404)
    def test_key_is_not_exposed_in_state_or_html(self):
        for path in ('/', '/api/state'):
            with urlopen(self.base + path) as r:
                self.assertNotIn(self.token.encode(), r.read())

if __name__ == '__main__': unittest.main()
