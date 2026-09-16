"""Deployment state machine. SQLite is the record; processes are the runtime."""
import hashlib
import json
import select
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

VERSIONS = {'v1': 'Baseline catalog', 'v2': 'Updated catalog pricing',
            'v3-broken': 'Failure drill: readiness returns HTTP 503'}

def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

class Conflict(Exception):
    pass

class Engine:
    def __init__(self, database, probe_timeout=4):
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.active = None
        self.busy = False
        self.closed = False
        self.worker = None
        self.probe_timeout = probe_timeout
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS deployments(
                id TEXT PRIMARY KEY, version TEXT NOT NULL, kind TEXT NOT NULL,
                status TEXT NOT NULL, created TEXT NOT NULL, finished TEXT,
                digest TEXT NOT NULL, reason TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY AUTOINCREMENT, deployment_id TEXT NOT NULL,
                time TEXT NOT NULL, stage TEXT NOT NULL, message TEXT NOT NULL);
        """)
        # Processes are owned by this controller's lifetime; never trust stale PIDs.
        self.db.execute("UPDATE deployments SET status='interrupted', finished=? WHERE status IN ('queued','starting','checking')", (now(),))
        self.db.commit()

    def event(self, ident, stage, message):
        with self.lock:
            self.db.execute('INSERT INTO events(deployment_id,time,stage,message) VALUES(?,?,?,?)',
                            (ident, now(), stage, message))
            self.db.commit()

    def status(self, ident, status, reason=''):
        with self.lock:
            finished = now() if status in ('succeeded', 'failed', 'interrupted') else None
            self.db.execute('UPDATE deployments SET status=?,reason=?,finished=? WHERE id=?',
                            (status, reason, finished, ident))
            self.db.commit()

    def deploy(self, version, kind='deploy'):
        with self.lock:
            if self.closed or self.busy:
                raise Conflict('A deployment is already running or the controller is stopping.')
            if version not in VERSIONS:
                raise ValueError('Choose a release from the catalog.')
            if self.active and self.active['version'] == version:
                raise Conflict('This release is already active.')
            ident = uuid.uuid4().hex[:12]
            digest = hashlib.sha256(Path(__file__).with_name('sample.py').read_bytes() + version.encode()).hexdigest()
            self.db.execute('INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)',
                            (ident, version, kind, 'queued', now(), None, digest, ''))
            self.db.commit()
            self.busy = True
            self.event(ident, 'queued', f'{kind.title()} requested for {version}.')
            self.worker = threading.Thread(target=self._run, args=(ident, version), daemon=True)
            self.worker.start()
            return ident

    def rollback(self):
        with self.lock:
            if not self.active:
                raise Conflict('Deploy a release before requesting rollback.')
            row = self.db.execute("SELECT version FROM deployments WHERE status='succeeded' AND version != ? ORDER BY rowid DESC LIMIT 1",
                                  (self.active['version'],)).fetchone()
            if not row:
                raise Conflict('No earlier successful release is available.')
            return self.deploy(row['version'], 'rollback')

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)
        if process.stdout:
            process.stdout.close()

    def _run(self, ident, version):
        candidate = None
        try:
            self.status(ident, 'starting')
            self.event(ident, 'starting', 'Starting an isolated Python workload on a loopback port.')
            candidate = subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('sample.py')), version],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            ready, _, _ = select.select([candidate.stdout], [], [], self.probe_timeout)
            if not ready:
                raise RuntimeError('Workload did not announce its port before the startup deadline.')
            port = int(candidate.stdout.readline().strip())
            self.status(ident, 'checking')
            self.event(ident, 'checking', f'Candidate is listening on port {port}; requiring three healthy responses.')
            deadline = time.monotonic() + self.probe_timeout
            successes = 0
            while time.monotonic() < deadline and successes < 3:
                if self.closed:
                    raise RuntimeError('Controller is stopping.')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/health', timeout=.5) as response:
                        payload = json.load(response)
                        if payload.get('version') != version or payload.get('healthy') is not True:
                            raise ValueError('Readiness identity mismatch')
                    successes += 1
                except Exception:
                    successes = 0
                time.sleep(.15)
            if successes < 3:
                raise RuntimeError('Readiness deadline exceeded. Candidate never passed three consecutive probes.')
            with self.lock:
                if self.closed:
                    raise RuntimeError('Controller is stopping.')
                previous = self.active
                self.active = {'id': ident, 'version': version, 'port': port, 'process': candidate}
                candidate = None
                self.status(ident, 'succeeded')
                self.event(ident, 'promoted', 'Readiness passed. The stable /demo route now serves this release.')
            if previous:
                self.stop(previous['process'])
                self.event(ident, 'retired', f"Stopped previous workload {previous['version']}.")
        except Exception as exc:
            self.status(ident, 'failed', str(exc))
            self.event(ident, 'failed', str(exc) + ' Existing traffic was not switched.')
        finally:
            if candidate:
                self.stop(candidate)
            with self.lock:
                self.busy = False

    def snapshot(self):
        with self.lock:
            deployments = [dict(r) for r in self.db.execute('SELECT * FROM deployments ORDER BY rowid DESC LIMIT 100')]
            events = [dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 250')]
            counts = dict(self.db.execute('SELECT status,COUNT(*) FROM deployments GROUP BY status').fetchall())
            active = {k: v for k, v in self.active.items() if k != 'process'} if self.active else None
            if active:
                active['running'] = self.active['process'].poll() is None
            return {'service': 'catalog-demo', 'runtime': 'local process', 'active': active,
                    'busy': self.busy, 'releases': VERSIONS, 'deployments': deployments, 'events': events,
                    'counts': counts}

    def proxy(self):
        # Hold the lock while reading, so promotion cannot retire an in-flight workload.
        with self.lock:
            if not self.active:
                raise Conflict('No release is active. Deploy v1 to begin.')
            with urlopen(f"http://127.0.0.1:{self.active['port']}/", timeout=2) as response:
                return json.load(response)

    def close(self):
        self.closed = True
        if self.worker:
            self.worker.join(timeout=self.probe_timeout + 8)
        with self.lock:
            if self.active:
                self.stop(self.active['process']); self.active = None
            self.db.close()
