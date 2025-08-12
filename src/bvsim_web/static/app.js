let spinnerTimer = null;
let matchImpactChart = null;
let lastSkillsData = null; // reserved for future use (e.g., re-sorting)
// Removed legacy skillsChart variable

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

// Statistical match impact chart (horizontal CI lines)
function renderMatchImpactChart(stat) {
  try {
    if (!stat || !stat.statistical_analysis) return;
    const canvas = document.getElementById('matchImpactChart');
    if (!canvas) return;

  // Sort & select top skills by descending mean impact (most positive first)
  const skills = (stat.skills || []).slice().sort((a,b)=> b.match.mean - a.match.mean);
    const TOP_N = 30;
    const topSkills = skills.slice(0, TOP_N);
    const labels = topSkills.map(s=> s.parameter);
    const means = topSkills.map(s=> s.match.mean);
    const lowers = topSkills.map(s=> s.match.lower);
    const uppers = topSkills.map(s=> s.match.upper);
    const significant = topSkills.map(s=> !!s.significant);

  // Dynamic height per skill
  // Increased base row height & minimum height to create more vertical space between lines.
  // (Was BASE_ROW_HEIGHT=36, MIN_HEIGHT=320)
  const BASE_ROW_HEIGHT = 46; const MIN_HEIGHT = 420; // tweak as needed for readability
  const desiredHeight = Math.max(MIN_HEIGHT, BASE_ROW_HEIGHT * topSkills.length + 60);
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
          y:{ type:'category', labels, offset:true, grid:{display:false}, ticks:{ padding:10, autoSkip:false, font:{ size:12 } } }
        }
      }, plugins:[errorBarPlugin]
    });

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
      tableContainer.innerHTML = `<table class="match-impact"><thead>${header}</thead><tbody>${rows}</tbody><caption>Top ${topSkills.length} parameters by match impact. Values show percentage point change (Δ) in win probability. Confidence intervals at 95% level.</caption></table>`;
    }
  } catch(e) { console.warn('renderMatchImpactChart failed', e); }
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
