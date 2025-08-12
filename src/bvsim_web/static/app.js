let spinnerTimer = null;
let matchImpactChart = null;
let simulateChart = null; // bar chart for last simulation
let compareChart = null;  // bar chart for last comparison average win rates
let lastSkillsData = null; // reserved for future use (e.g., re-sorting)
// Removed legacy skillsChart variable

// --- Status / progress helpers ---
function setMatchImpactStatus(msg, spinning=true) {
  const el = document.getElementById('matchImpactStatus');
  if (!el) return;
  if (!msg) { el.textContent=''; return; }
  el.innerHTML = (spinning?'<span class="spinner"></span>':'') + msg;
}
function clearMatchImpactDisplay() {
  const canvas = document.getElementById('matchImpactChart');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    // Clear drawing surface
    ctx.clearRect(0,0,canvas.width || canvas.clientWidth, canvas.height || canvas.clientHeight);
  }
  const legend = document.getElementById('matchImpactLegend');
  if (legend) legend.innerHTML='';
  const table = document.getElementById('matchImpactTableContainer');
  if (table) table.innerHTML='';
  if (matchImpactChart) { try { matchImpactChart.destroy(); } catch(_){} matchImpactChart=null; }
  if (simulateChart) { try { simulateChart.destroy(); } catch(_){} simulateChart=null; }
  if (compareChart) { try { compareChart.destroy(); } catch(_){} compareChart=null; }
}
function setSkillsStatus(msg, spinning=true){
  const el = document.getElementById('skillsStatus');
  if (!el) return;
  if (!msg) { el.textContent=''; return; }
  el.innerHTML = (spinning?'<span class="spinner"></span>':'') + msg;
}

// toggleOutput removed (output always visible now)
function startWorking(msg = 'Working') {
  const el = document.getElementById('output');
  let dots = 0;
  clearWorking();
  el.textContent = msg;
  // Show global activity also in chart area
  clearMatchImpactDisplay();
  setMatchImpactStatus('Processing request...', true);
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

// Statistical match impact chart (horizontal CI lines)
function renderMatchImpactChart(stat) {
  try {
    if (!stat || !stat.statistical_analysis) return;
    const canvas = document.getElementById('matchImpactChart');
    if (!canvas) return;
  const titleEl = document.getElementById('chartPaneTitle');
  if (titleEl) titleEl.textContent = 'Skills Impact (Match Win Rate Δ)';

  // Sort & select top skills by descending mean impact (most positive first)
  const skills = (stat.skills || []).slice().sort((a,b)=> b.match.mean - a.match.mean);
    const topSkills = skills; // now show all parameters
    const labels = topSkills.map(s=> s.parameter);
    const means = topSkills.map(s=> s.match.mean);
    const lowers = topSkills.map(s=> s.match.lower);
    const uppers = topSkills.map(s=> s.match.upper);
    const significant = topSkills.map(s=> !!s.significant);

  // Dynamic height per skill
  // Increased base row height & minimum height to create more vertical space between lines.
  // (Was BASE_ROW_HEIGHT=36, MIN_HEIGHT=320)
  const BASE_ROW_HEIGHT = 35; const MIN_HEIGHT = 280; // balanced height for readability
  const desiredHeight = Math.max(MIN_HEIGHT, BASE_ROW_HEIGHT * topSkills.length + 80);
    canvas.style.height = desiredHeight + 'px';

    // Destroy prior chart
    if (matchImpactChart) { try { matchImpactChart.destroy(); } catch(_) {} matchImpactChart = null; }

    // X range from CI bounds including zero
    const minCI = Math.min(...lowers); const maxCI = Math.max(...uppers);
    const span = maxCI - minCI || 1; const pad = span * 0.05;
    let xMin = minCI - pad; let xMax = maxCI + pad;
    if (xMin > 0) xMin = 0; if (xMax < 0) xMax = 0;

    const errorBarPlugin = { id:'errorBars', afterDatasetsDraw(chart){
      const {ctx} = chart; const meta = chart.getDatasetMeta(0); const xScale = chart.scales.x;
      ctx.save(); ctx.lineWidth = 1.2;
      for (let i=0;i<meta.data.length;i++){ const pt = meta.data[i]; if(!pt) continue; const y = pt.y;
        const xL = xScale.getPixelForValue(lowers[i]); const xH = xScale.getPixelForValue(uppers[i]);
        ctx.strokeStyle = significant[i] ? '#1b5e20' : '#444'; ctx.beginPath(); ctx.moveTo(xL,y); ctx.lineTo(xH,y);
        const cap=5; ctx.moveTo(xL,y-cap/2); ctx.lineTo(xL,y+cap/2); ctx.moveTo(xH,y-cap/2); ctx.lineTo(xH,y+cap/2); ctx.stroke(); }
      // zero line
      const zeroX = xScale.getPixelForValue(0); ctx.strokeStyle='#999'; ctx.lineWidth=1; ctx.setLineDash([4,3]); ctx.beginPath(); ctx.moveTo(zeroX, chart.chartArea.top); ctx.lineTo(zeroX, chart.chartArea.bottom); ctx.stroke(); ctx.setLineDash([]); ctx.restore(); } };

  matchImpactChart = new Chart(canvas.getContext('2d'), {
      type:'scatter',
      data:{ datasets:[{ label:'Match Win Rate Δ % (mean)', data: means.map((m,i)=>({x:m,y:labels[i]})), showLine:false, pointRadius:5, pointHoverRadius:7, pointBackgroundColor: means.map((v,i)=> significant[i] ? (v>=0?'#1976d2':'#c62828') : (v>=0?'#64b5f6':'#ef9a9a')), pointBorderColor: means.map(v=> v>=0?'#0d47a1':'#b71c1c'), pointBorderWidth:1.5 }]},
      options:{ responsive:true, maintainAspectRatio:false, animation:false, parsing:false,
        plugins:{ legend:{display:false}, tooltip:{ callbacks:{ title:(items)=> items[0].raw && items[0].raw.y, label:(ctx)=>{ const i=ctx.dataIndex; const mean=means[i]; const lo=lowers[i]; const hi=uppers[i]; const sig=significant[i]?' (significant)':''; return `${mean>=0?'+':''}${mean.toFixed(2)}%  CI [${lo>=0?'+':''}${lo.toFixed(2)}%, ${hi>=0?'+':''}${hi.toFixed(2)}%]${sig}`; } } }, title:{display:true,text:'Match Win Rate Impact (mean & 95% CI)'} },
        scales:{
          x:{ title:{display:true,text:'Δ Win Rate %'}, min:xMin, max:xMax, ticks:{ callback:v=> (v>0?'+':'')+v+'%' } },
          y:{ type:'category', labels, offset:true, grid:{display:false}, ticks:{ padding:15, autoSkip:false, font:{ size:13 }, maxRotation:0, minRotation:0 } }
        }
      }, plugins:[errorBarPlugin]
    });

  // Clear status once finished rendering
  setMatchImpactStatus('', false);

    // Build legend
    const legendEl = document.getElementById('matchImpactLegend');
    if (legendEl) {
      legendEl.innerHTML = '';
      const entries = [
        { color:'#1976d2', label:'Significant positive (CI excludes 0, mean > 0)' },
        { color:'#c62828', label:'Significant negative (CI excludes 0, mean < 0)' },
        { color:'#64b5f6', label:'Non-significant positive (CI includes 0)' },
        { color:'#ef9a9a', label:'Non-significant negative (CI includes 0)' }
      ];
      entries.forEach(e=>{
        const item=document.createElement('div');
        item.style.display='flex'; item.style.alignItems='center'; item.style.gap='6px'; item.style.fontSize='0.7rem'; item.style.margin='2px 12px 2px 0';
        const swatch=document.createElement('span'); swatch.style.width='14px'; swatch.style.height='14px'; swatch.style.borderRadius='50%'; swatch.style.background=e.color; swatch.style.border='1px solid #133';
        item.appendChild(swatch); const txt=document.createElement('span'); txt.textContent=e.label; item.appendChild(txt); legendEl.appendChild(item);
      });
    }

    // Build detailed table with match and (if available) point CIs
    const tableContainer = document.getElementById('matchImpactTableContainer');
    if (tableContainer) {
      const hasPoint = topSkills.some(s=> s.point_mean !== undefined || (s.point && s.point.mean !== undefined) || s.point_mean !== undefined);
      const rows = topSkills.map(s=>{
        const m = s.match || {}; // expected {mean,lower,upper}
        // Try to derive point stats if present (various naming possibilities)
        const pMean = s.point_mean ?? (s.point && s.point.mean);
        const pLower = s.point_lower ?? (s.point && s.point.lower);
        const pUpper = s.point_upper ?? (s.point && s.point.upper);
        const sig = s.significant ? (m.mean>=0?'pos':'neg') : '';
        const cls = s.significant ? (m.mean>=0?'sig-pos':'sig-neg') : '';
        return `<tr class="${cls}">`+
          `<td>${s.parameter}</td>`+
          (hasPoint? `<td>${pMean!==undefined? (pMean>=0?'+':'')+pMean.toFixed(2)+'%':''}</td>`: '')+
          (hasPoint? `<td>${pLower!==undefined? (pLower>=0?'+':'')+pLower.toFixed(2)+'%':''}</td>`: '')+
          (hasPoint? `<td>${pUpper!==undefined? (pUpper>=0?'+':'')+pUpper.toFixed(2)+'%':''}</td>`: '')+
          `<td>${m.mean!==undefined? (m.mean>=0?'+':'')+m.mean.toFixed(2)+'%':''}</td>`+
          `<td>${m.lower!==undefined? (m.lower>=0?'+':'')+m.lower.toFixed(2)+'%':''}</td>`+
          `<td>${m.upper!==undefined? (m.upper>=0?'+':'')+m.upper.toFixed(2)+'%':''}</td>`+
          `<td>${s.significant? (sig==='pos'?'Yes (+)':'Yes (-)'):'No'}</td>`+
        `</tr>`; }).join('');
      const headerPoint = hasPoint ? `<th colspan="3">Point Impact 95% CI</th>` : '';
      const subHeaderPoint = hasPoint ? `<tr><th>Parameter</th><th>Mean</th><th>Lower</th><th>Upper</th><th>Match Mean</th><th>Match Lower</th><th>Match Upper</th><th>Significant?</th></tr>` : '';
      // Simpler single header row to keep size small
      const header = `<tr><th>Parameter</th>${hasPoint?'<th>Point Mean</th><th>Point Low</th><th>Point High</th>':''}<th>Match Mean</th><th>Match Low</th><th>Match High</th><th>Significant</th></tr>`;
  tableContainer.innerHTML = `<table class="match-impact"><thead>${header}</thead><tbody>${rows}</tbody><caption>All ${topSkills.length} parameters by match impact. Values show percentage point change (Δ) in win probability. Confidence intervals at 95% level.</caption></table>`;
    }
  } catch(e) { console.warn('renderMatchImpactChart failed', e); }
}

// Bar chart for a single simulation win rates (Team A vs Team B)
function renderSimulationChart(sim) {
  if (!sim || !sim.summary) return;
  const canvas = document.getElementById('matchImpactChart');
  if (!canvas) return;
  const titleEl = document.getElementById('chartPaneTitle');
  if (titleEl) titleEl.textContent = 'Simulation Win Rates';
  // Destroy only non-skills charts if present
  if (simulateChart) { try { simulateChart.destroy(); } catch(_){} simulateChart=null; }
  if (matchImpactChart) { /* keep skills scatter if user wants? We clear before each new source anyway */ }
  if (compareChart) { try { compareChart.destroy(); } catch(_){} compareChart=null; }
  const { team_a, team_b, team_a_win_rate, team_b_win_rate } = sim.summary;
  const data = {
    labels: [team_a, team_b],
    datasets: [{ label: 'Win Rate %', data: [team_a_win_rate, team_b_win_rate], backgroundColor: ['#1976d2','#c62828'] }]
  };
  simulateChart = new Chart(canvas.getContext('2d'), {
    type: 'bar', data,
    options: { responsive:true, maintainAspectRatio:false, animation:false,
      plugins:{ title:{display:true,text:'Simulation Win Rates'}, legend:{display:false}, tooltip:{ callbacks:{ label: ctx=> `${ctx.parsed.y.toFixed(2)}%` } } },
      scales:{ y:{ beginAtZero:true, title:{display:true,text:'Win %'} } }
    }
  });
  setMatchImpactStatus('', false);
  const legendEl = document.getElementById('matchImpactLegend');
  if (legendEl) {
    legendEl.innerHTML = '';
    const note = document.createElement('div');
    note.style.fontSize = '0.65rem';
    note.textContent = `Simulation: ${sim.parameters.points} points`;
    legendEl.appendChild(note);
  }
  const tableContainer = document.getElementById('matchImpactTableContainer');
  if (tableContainer) {
    tableContainer.innerHTML = `<table class="match-impact"><thead><tr><th>Team</th><th>Win %</th><th>Wins</th></tr></thead><tbody><tr><td>${team_a}</td><td>${team_a_win_rate.toFixed(2)}%</td><td>${sim.summary.team_a_wins}</td></tr><tr><td>${team_b}</td><td>${team_b_win_rate.toFixed(2)}%</td><td>${sim.summary.team_b_wins}</td></tr></tbody><caption>Single simulation results.</caption></table>`;
  }
}

// Bar chart for comparison rankings plus matrix table
function renderComparisonChart(comp) {
  if (!comp || !comp.results) return;
  const canvas = document.getElementById('matchImpactChart');
  if (!canvas) return;
  const titleEl = document.getElementById('chartPaneTitle');
  if (titleEl) titleEl.textContent = 'Team Comparison Rankings';
  if (compareChart) { try { compareChart.destroy(); } catch(_){} compareChart=null; }
  if (simulateChart) { try { simulateChart.destroy(); } catch(_){} simulateChart=null; }
  const rankings = comp.results.rankings || [];
  const labels = rankings.map(r=> r.name);
  const dataVals = rankings.map(r=> r.average_win_rate);
  compareChart = new Chart(canvas.getContext('2d'), {
    type:'bar',
    data:{ labels, datasets:[{ label:'Avg Win %', data:dataVals, backgroundColor:'#6a1b9a' }]},
    options:{ responsive:true, maintainAspectRatio:false, animation:false,
      plugins:{ title:{display:true,text:'Comparison Average Win Rates'}, legend:{display:false}, tooltip:{ callbacks:{ label: ctx=> `${ctx.parsed.y.toFixed(2)}%` } } },
      scales:{ y:{ beginAtZero:true, title:{display:true,text:'Avg Win %'} } }
    }
  });
  setMatchImpactStatus('', false);
  // Legend note
  const legendEl = document.getElementById('matchImpactLegend');
  if (legendEl) {
    legendEl.innerHTML='';
    const note=document.createElement('div'); note.style.fontSize='0.65rem'; note.textContent=`Comparison: ${comp.parameters.points} points per matchup`;
    legendEl.appendChild(note);
  }
  // Build matrix table
  const tableContainer = document.getElementById('matchImpactTableContainer');
  if (tableContainer) {
    const teams = comp.results.teams || [];
    const matrix = comp.results.results_matrix || {};
    // header
    let html = '<table class="match-impact"><thead><tr><th>Team</th>' + teams.map(t=>`<th>${t}</th>`).join('') + '</tr></thead><tbody>';
    teams.forEach(a=> {
      html += `<tr><td>${a}</td>`;
      teams.forEach(b=> {
        if (a===b) html += '<td>-</td>'; else {
          const val = matrix[a] && matrix[a][b] !== undefined ? matrix[a][b].toFixed(1)+'%' : '';
          html += `<td>${val}</td>`;
        }
      });
      html += '</tr>';
    });
    html += '</tbody><caption>Win rate matrix (row vs column). Rankings ordered by average win %.</caption></table>';
    tableContainer.innerHTML = html;
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
    if (!list) return; // defensive
    list.innerHTML='';
    data.teams.forEach(t=>{
      const li=document.createElement('li');
      li.innerHTML = `<span>${t.name || '(unnamed)'} <small>${t.file || ''}</small></span>`;
      list.appendChild(li);
    });
  } catch(e){ out(e.message); }
}

async function createTeam() {
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
  clearMatchImpactDisplay();
  renderSimulationChart(res);
  } catch (e) { out(e.message); }
}
function simulate() { simulateCommon({}); }
function simulateQuick() { simulateCommon({ quick: true }); }
function simulateAccurate() { simulateCommon({ accurate: true }); }

async function skillsCommon(opts) {
  startWorking('Analyzing skills');
  setSkillsStatus('Running skills analysis...', true);
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
    // Backend currently returns single-run improvements without statistical_analysis / CI.
    // Synthesize a structure compatible with renderMatchImpactChart using improvement deltas.
  if (res && res.results && res.results.parameter_improvements) {
      const improvs = res.results.parameter_improvements;
      const skills = Object.entries(improvs).map(([parameter, v]) => {
    // Prefer match-level improvement if available
    const hasMatch = v.match_improvement !== undefined;
    const mean = hasMatch ? v.match_improvement : (v.improvement || 0);
    const lower = hasMatch ? (v.match_lower ?? mean) : (v.improvement_lower !== undefined ? v.improvement_lower : mean);
    const upper = hasMatch ? (v.match_upper ?? mean) : (v.improvement_upper !== undefined ? v.improvement_upper : mean);
        const significant = lower > 0 || upper < 0; // CI excludes zero
  // Point impact (raw win-rate improvement) values
  const pMean = v.improvement !== undefined ? v.improvement : undefined;
  const pLower = v.improvement_lower !== undefined ? v.improvement_lower : pMean;
  const pUpper = v.improvement_upper !== undefined ? v.improvement_upper : pMean;
  return { parameter, point: { mean: pMean, lower: pLower, upper: pUpper }, match: { mean, lower, upper }, significant };
      });
      // Only attempt to render if we have at least one improvement
      if (skills.length) {
        renderMatchImpactChart({ statistical_analysis: true, skills });
      }
    } else if (res && res.statistical_analysis) {
      // Future multi-run pathway
      renderMatchImpactChart(res);
    }
  setSkillsStatus('Skills analysis complete.', false);
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
  clearMatchImpactDisplay();
  renderComparisonChart(res);
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
    if (res && Array.isArray(res.rallies)) {
      renderRallies(res.rallies, { teamA: team_a || 'A', teamB: team_b || 'B' });
    }
  } catch (e) { out(e.message); }
}

refreshTeams();

// ---------------- RALLIES VISUALIZATION -----------------
// Expected rally object shape: { point_type: 'attack_error', sequence: '[A] A.srv(ok)→B.rcv(gd)→B.set(exc)→B.att(err) → attack_error', winner: 'A' }
// Parsing strategy:
// 1. Strip leading team indicator like "[A]" capturing initial serving side.
// 2. Split by arrow symbols (→) ignoring spaces around.
// 3. Each token of form Team.action(qual) where team is single char (A/B) or name prefix; map quality synonyms.
// 4. Final token after last arrow may contain point result (e.g. 'attack_error', 'ace'). We already have point_type.
// 5. Produce steps: { team: 'A'|'B', action: 'srv'|'rcv'|..., quality: 'ok'|'gd'|'err'|'exc'|'ace', raw: original }.
// Quality normalization: exc/excellent->exc, gd/good->good, ok->ok, err/error->err, ace->ace.

function parseRallySequence(seq) {
  if (!seq || typeof seq !== 'string') return { steps: [], raw: seq };
  let original = seq.trim();
  // Remove leading [A] or [B]
  let leadingTeam = null;
  const leadMatch = original.match(/^\[([A-Za-z])\]\s*/);
  if (leadMatch) {
    leadingTeam = leadMatch[1];
    original = original.slice(leadMatch[0].length);
  }
  // Split by arrow unicode or fallback '->'
  const parts = original.split(/(?:→|->)/).map(p => p.trim()).filter(Boolean);
  const steps = [];
  const actionRegex = /^([A-Za-z0-9_]+)\.([a-z]{2,5})\(([^)]*)\)$/i; // Team.action(qual)
  for (let i=0;i<parts.length;i++) {
    let token = parts[i];
    // If token contains a space before the last arrow (like 'B.att(err)  '), keep token before spaces
    token = token.trim();
    // Attempt extraction
    const m = token.match(actionRegex);
    if (m) {
      let team = m[1];
      let action = m[2];
      let qualityRaw = (m[3]||'').toLowerCase();
      // Normalize team to single letter if it's longer and starts with A or B
      if (team.length>1 && /^[AB]/i.test(team)) team = team[0];
      team = team.toUpperCase();
      action = action.toLowerCase();
      let quality = qualityRaw;
      if (/exc|excellent/.test(qualityRaw)) quality = 'exc';
      else if (/gd|good/.test(qualityRaw)) quality = 'good';
      else if (/ok/.test(qualityRaw)) quality = 'ok';
      else if (/err|error/.test(qualityRaw)) quality = 'err';
      else if (/ace/.test(qualityRaw)) quality = 'ace';
      steps.push({ team, action, quality, raw: token });
    } else {
      // Possibly the result token (e.g., 'attack_error') – ignore here; handled separately
    }
  }
  return { steps, leadingTeam, raw: seq };
}

function renderRallies(rallies, { teamA='A', teamB='B' }={}) {
  const container = document.getElementById('ralliesContainer');
  if (!container) return;
  container.innerHTML='';
  container.style.display = rallies.length ? 'block' : 'none';
  const legend = document.getElementById('ralliesLegend');
  if (legend) {
    legend.style.display='block';
    legend.innerHTML = `
      <strong style="font-size:.6rem;">Legend</strong><br/>
      <span class="swatch teamA"></span>${teamA} action&nbsp;&nbsp;
      <span class="swatch teamB"></span>${teamB} action&nbsp;&nbsp;
      <span class="swatch exc"></span>excellent <span class="swatch good"></span>good <span class="swatch ok"></span>ok <span class="swatch err"></span>error <span class="swatch ace"></span>ace / terminal
    `;
  }
  rallies.forEach((r, idx) => {
    const parsed = parseRallySequence(r.sequence || '');
    const wrap = document.createElement('div');
    wrap.className = 'rally-wrapper';
    // Header
    const header = document.createElement('div'); header.className='rally-header';
    const title = document.createElement('div'); title.textContent = `Rally ${idx+1}`; header.appendChild(title);
    const winner = document.createElement('div'); winner.className='winner '+(r.winner==='B'?'team-B':'team-A'); winner.textContent = `Winner: ${r.winner}`; header.appendChild(winner);
    wrap.appendChild(header);
    // Timeline
    const timeline = document.createElement('div'); timeline.className='rally-timeline';
    parsed.steps.forEach(step => {
      const stepEl = document.createElement('div');
      stepEl.className = 'rally-step team-' + (step.team==='B'?'B':'A');
      // Action label mapping
      const actMap = { srv:'Serve', rcv:'Receive', set:'Set', att:'Attack', blk:'Block', dig:'Dig', trg:'Target', pass:'Pass', def:'Def', lib:'Lib', unk:'Play' };
      const actLabel = actMap[step.action] || step.action;
      const actDiv = document.createElement('div'); actDiv.className='act'; actDiv.textContent = actLabel; stepEl.appendChild(actDiv);
      if (step.quality) {
        const qualDiv = document.createElement('div');
        let cls = 'q-ok';
        if (step.quality==='exc') cls='q-exc';
        else if (step.quality==='good') cls='q-good';
        else if (step.quality==='err') cls='q-err';
        else if (step.quality==='ace') cls='q-ace';
        qualDiv.className = 'qual '+cls; qualDiv.textContent = step.quality; stepEl.appendChild(qualDiv);
      }
      stepEl.title = step.raw; // tooltip
      timeline.appendChild(stepEl);
    });
    // Result
    const result = document.createElement('div'); result.className='rally-result';
    result.textContent = r.point_type || (parsed.steps.slice(-1)[0]?.quality==='ace' ? 'ace' : 'result');
    timeline.appendChild(result);
    wrap.appendChild(timeline);
    // Footer details
    const footer = document.createElement('div'); footer.className='rally-footer';
    footer.textContent = r.sequence || '';
    wrap.appendChild(footer);
    container.appendChild(wrap);
  });
  // Update chart pane title to indicate we are viewing rallies
  const titleEl = document.getElementById('chartPaneTitle'); if (titleEl) titleEl.textContent='Rallies';
  // Clear any existing chart visuals
  clearMatchImpactDisplay();
  // Re-attach container (clearMatchImpactDisplay clears legend/table but not our container since we appended after chart section markup). Reappend to ensure visibility.
  const chartSection = document.getElementById('confidenceChartSection');
  if (chartSection && !container.parentElement) chartSection.appendChild(container);
}
