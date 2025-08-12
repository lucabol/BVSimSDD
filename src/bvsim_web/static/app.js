let spinnerTimer = null;
let skillsChart = null;
let lastSkillsData = null;

function toggleOutput() {
  const outEl = document.getElementById('output');
  const tog = document.getElementById('outputToggle');
  const isHidden = outEl.style.display === 'none';
  if (isHidden) {
    outEl.style.display = 'block';
    tog.textContent = 'Hide';
  } else {
    outEl.style.display = 'none';
    tog.textContent = 'Show';
  }
}
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
  // Ensure output stays collapsed unless user opens it; do not auto-open
  el.textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
}

function renderSkillsChart(results) {
  try {
    const ctx = document.getElementById('skillsChart');
    if (!ctx || !results) return;
    const baseline = results.baseline_win_rate; // percent value
    const improvements = results.parameter_improvements || {};
    const rows = Object.entries(improvements).map(([name, info]) => ({
      name,
      win_rate: info.win_rate, // already absolute win rate percent
      improvement: info.improvement // delta in percent points
    }));
    // Sort by absolute improvement desc
    rows.sort((a,b) => Math.abs(b.improvement) - Math.abs(a.improvement));
    const top = rows.slice(0, 25);
    const labels = top.map(r => r.name.split('.').slice(-2).join('.'));
    const dataWin = top.map(r => r.win_rate);
    const dataImprovement = top.map(r => r.improvement);
    const baseLineData = new Array(top.length).fill(baseline);
    if (skillsChart) {
      skillsChart.destroy();
    }
    skillsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            type: 'line',
            label: 'Baseline',
            data: baseLineData,
            borderColor: '#888',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            tension: 0
          },
            {
            label: 'New Win Rate',
            data: dataWin,
            backgroundColor: dataImprovement.map(v => v >= 0 ? 'rgba(25,118,210,0.55)' : 'rgba(198,40,40,0.55)'),
            borderColor: dataImprovement.map(v => v >= 0 ? 'rgba(25,118,210,1)' : 'rgba(198,40,40,1)'),
            borderWidth: 1
          },
          {
            label: 'Improvement (Δ)',
            data: dataImprovement,
            type: 'line',
            yAxisID: 'y1',
            borderColor: '#43a047',
            backgroundColor: 'rgba(67,160,71,0.3)',
            fill: true,
            tension: 0.25
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => {
                if (ctx.dataset.label === 'New Win Rate') {
                  const imp = dataImprovement[ctx.dataIndex];
                  return `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}% (Δ ${imp >= 0 ? '+' : ''}${imp.toFixed(3)} pts)`;
                }
                if (ctx.dataset.label === 'Baseline') {
                  return `Baseline: ${baseline.toFixed(2)}%`;
                }
                if (ctx.dataset.label.startsWith('Improvement')) {
                  return `Δ: ${ctx.parsed.y.toFixed(3)} pts`;
                }
                return `${ctx.dataset.label}: ${ctx.parsed.y}`;
              }
            }
          },
          legend: { display: true }
        },
        scales: {
          y: {
            title: { display: true, text: 'Win Rate %' },
            beginAtZero: false,
            suggestedMin: Math.max(0, baseline - 5),
            suggestedMax: Math.min(100, baseline + 5)
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Improvement Δ pts' }
          },
          x: { ticks: { autoSkip: true, maxRotation: 45, minRotation: 0 } }
        }
      }
    });
  } catch (e) {
    console.warn('Chart render failed', e);
  }
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
    out(res); // keep textual JSON in collapsible output
    lastSkillsData = res.results;
    if (res && res.results) {
      renderSkillsChart(res.results);
    }
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
