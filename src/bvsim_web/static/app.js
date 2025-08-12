let spinnerTimer = null;
function startWorking(msg = 'Working') {
  const el = document.getElementById('output');
  let dots = 0;
  clearWorking();
  el.textContent = msg;
  spinnerTimer = setInterval(() => {
    dots = (dots + 1) % 4;
    el.textContent = msg + '.'.repeat(dots);
  }, 400);
}
function clearWorking() {
  if (spinnerTimer) {
    clearInterval(spinnerTimer);
    spinnerTimer = null;
  }
}
function out(obj) {
  clearWorking();
  const el = document.getElementById('output');
  el.textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
}
async function api(path, options={}) {
  startWorking();
  const res = await fetch(path, Object.assign({headers: { 'Content-Type': 'application/json' }}, options));
  if (!res.ok) {
    let txt = await res.text();
    clearWorking();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  const data = await res.json();
  clearWorking();
  return data;
}

async function refreshTeams() {
  try {
    const data = await api('/api/teams');
    const list = document.getElementById('teamList');
    list.innerHTML = '';
    data.teams.forEach(t => {
      const li = document.createElement('li');
      li.innerHTML = `<span>${t.name || '(unnamed)'} <small>${t.file || ''}</small></span>`;
      list.appendChild(li);
    });
  } catch (e) { out(e.message); }
}

async function createTeam() {
  startWorking('Creating team');
  const name = document.getElementById('newTeamName').value.trim();
  const template = document.getElementById('newTeamTemplate').value;
  if (!name) return out('Enter a team name');
  try {
    const res = await api('/api/teams', { method: 'POST', body: JSON.stringify({ name, template }) });
    out(res);
    refreshTeams();
  } catch (e) { out(e.message); }
}

async function uploadTeam() {
  startWorking('Uploading team');
  const input = document.getElementById('uploadTeamFile');
  if (!input.files.length) return out('Choose a file');
  const form = new FormData();
  form.append('file', input.files[0]);
  try {
    const res = await fetch('/api/teams/upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    out(await res.json());
    refreshTeams();
  } catch (e) { out(e.message); }
}

async function simulateCommon(opts) {
  startWorking('Simulating');
  try {
    const team_a = document.getElementById('simTeamA').value.trim();
    const team_b = document.getElementById('simTeamB').value.trim();
    const points = document.getElementById('simPoints').value;
    const payload = Object.assign({ team_a, team_b }, opts);
    if (points) payload.points = parseInt(points, 10);
    const res = await api('/api/simulate', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  } catch (e) { out(e.message); }
}
function simulate() { simulateCommon({}); }
function simulateQuick() { simulateCommon({ quick: true }); }
function simulateAccurate() { simulateCommon({ accurate: true }); }

async function skillsCommon(opts) {
  startWorking('Analyzing skills');
  try {
    const team = document.getElementById('skillsTeam').value.trim();
    const opponent = document.getElementById('skillsOpponent').value.trim();
    const improve = document.getElementById('skillsImprove').value.trim();
    const payload = Object.assign({}, opts);
    if (team) payload.team = team;
    if (opponent) payload.opponent = opponent;
    if (improve) payload.improve = improve;
    const res = await api('/api/skills', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  } catch (e) { out(e.message); }
}
function skillsAnalysis() { skillsCommon({}); }
function skillsQuick() { skillsCommon({ quick: true }); }
function skillsAccurate() { skillsCommon({ accurate: true }); }

async function compareCommon(opts) {
  startWorking('Comparing teams');
  try {
    const teams = document.getElementById('compareTeams').value.split(',').map(s => s.trim()).filter(Boolean);
    const payload = Object.assign({ teams }, opts);
    const res = await api('/api/compare', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  } catch (e) { out(e.message); }
}
function compareTeamsRun() { compareCommon({}); }
function compareQuick() { compareCommon({ quick: true }); }
function compareAccurate() { compareCommon({ accurate: true }); }

// Renamed from examples() to runExamples() to avoid collision with element id or reserved globals
async function runExamples() {
  startWorking('Generating rallies');
  try {
    const team_a = document.getElementById('exTeamA').value.trim();
    const team_b = document.getElementById('exTeamB').value.trim();
    const count = document.getElementById('exCount').value || 5;
    const payload = { team_a, team_b, count: parseInt(count,10) };
    const res = await api('/api/examples', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  } catch (e) { out(e.message); }
}

refreshTeams();
