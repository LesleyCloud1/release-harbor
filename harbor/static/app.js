const $ = id => document.getElementById(id);
let pending = false;
const cell = (text, tag = 'td') => { const el = document.createElement(tag); el.textContent = text; return el; };
async function refresh() {
  try {
    const response = await fetch('/api/state');
    if (!response.ok) throw Error('Controller unavailable');
    const state = await response.json();
    $('connection').textContent = state.busy ? 'Deployment in progress' : 'Controller online';
    $('active').textContent = state.active?.version || '—';
    $('active-detail').textContent = state.active ? (state.active.running ? 'Process running · /demo routes here' : 'Process stopped · service unavailable') : 'Awaiting first deployment';
    $('success').textContent = state.counts.succeeded || 0;
    $('failed').textContent = state.counts.failed || 0;
    $('deploy').disabled = pending || state.busy;
    $('rollback').disabled = pending || state.busy || !state.active || !state.deployments.some(d => d.status === 'succeeded' && d.version !== state.active.version);
    $('rows').replaceChildren();
    for (const d of state.deployments) {
      const row = document.createElement('tr');
      row.append(cell(d.version), cell(d.kind));
      const status = cell(''); const badge = cell(d.status, 'span'); badge.className = 'badge ' + d.status; status.append(badge); row.append(status);
      row.append(cell(new Date(d.created).toLocaleString()));
      const digest = cell(''); const code = cell(d.digest.slice(0, 12), 'code'); code.title = 'SHA-256 of workload source and release configuration: ' + d.digest; digest.append(code); row.append(digest);
      $('rows').append(row);
    }
    $('empty').hidden = state.deployments.length > 0;
    $('event-list').replaceChildren();
    for (const e of state.events.slice(0, 16)) {
      const item = document.createElement('div'); item.className = 'event';
      item.append(cell(new Date(e.time).toLocaleTimeString(), 'time'), cell(e.stage, 'b'), cell(e.message, 'span'));
      $('event-list').append(item);
    }
    if (!state.events.length) $('event-list').append(cell('Deployment events will appear here.', 'p'));
  } catch (err) { $('connection').textContent = 'Controller offline'; $('feedback').textContent = err.message; $('deploy').disabled = true; $('rollback').disabled = true; }
}
async function act(path, data) {
  if (!$('key').value) { $('feedback').textContent = 'Paste the operator key from your terminal first.'; $('key').focus(); return; }
  pending = true; $('deploy').disabled = true; $('rollback').disabled = true;
  try {
    const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + $('key').value}, body: JSON.stringify(data)});
    const result = await r.json();
    if (!r.ok) throw Error(result.error || 'Request failed');
    $('feedback').textContent = 'Request ' + result.id + ' accepted. Follow the activity log below.';
  } catch (err) { $('feedback').textContent = err.message; }
  finally { pending = false; await refresh(); }
}
$('deploy').addEventListener('click', () => act('/api/deploy', {version: $('release').value}));
$('rollback').addEventListener('click', () => act('/api/rollback', {}));
refresh(); setInterval(refresh, 1500);
