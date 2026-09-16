"""Live integration smoke test; defaults match the ephemeral CI container."""
import json
import os
import time
from urllib.request import Request, urlopen
BASE = os.environ.get('HARBOR_URL', 'http://127.0.0.1:8088')
TOKEN = os.environ.get('HARBOR_TOKEN', 'ci-only-ephemeral-operator-key')
def get(path):
    with urlopen(BASE + path, timeout=2) as r: return json.load(r)
def post(path, data):
    req = Request(BASE + path, json.dumps(data).encode(),
                  {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    with urlopen(req, timeout=2) as r: return json.load(r)
for attempt in range(40):
    try: get('/healthz'); break
    except Exception: time.sleep(.25)
else: raise RuntimeError('Controller failed to start')
def deploy(version, expected):
    ident = post('/api/deploy', {'version': version})['id']
    for _ in range(80):
        state = get('/api/state')
        row = next(d for d in state['deployments'] if d['id'] == ident)
        if row['status'] in ('succeeded', 'failed') and not state['busy']:
            assert row['status'] == expected, row
            return
        time.sleep(.15)
    raise RuntimeError('Deployment did not finish')
deploy('v1', 'succeeded')
deploy('v3-broken', 'failed')
assert get('/demo')['version'] == 'v1'
print('Live smoke passed: real workload promoted; broken candidate rejected; v1 still serves.')
