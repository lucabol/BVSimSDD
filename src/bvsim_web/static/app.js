let spinnerTimer = null;
let workingActive = false; // tracks if global working spinner loop is running
let matchImpactChart = null;
let simulateChart = null; // bar chart for last simulation
let compareChart = null;  // bar chart for last comparison average win rates
let lastSkillsData = null; // reserved for future use (e.g., re-sorting)
// Removed legacy skillsChart variable

// Formatting helpers for dynamic titles
function fmtInt(n){ if(n==null) return ''; if(n>=1_000_000) return (n/1_000_000).toFixed(n%1_000_000?1:0)+'M'; if(n>=1000) return (n/1000).toFixed(n%1000?1:0)+'k'; return ''+n; }
function fmtPct(p){ if(p==null || isNaN(p)) return ''; return (p>=0?'+':'')+p.toFixed(2)+'%'; }
function fmtChangeVal(v){ if(v==null) return ''; // value as fraction; show also percent
  if(Math.abs(v) <= 1){ return (v*100).toFixed(1)+'%'; }
  return v.toString(); }

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
  canvas.style.display = 'block';
  }
  const legend = document.getElementById('matchImpactLegend');
  if (legend) legend.innerHTML='';
  const table = document.getElementById('matchImpactTableContainer');
  if (table) table.innerHTML='';
  // Hide rallies view (so other displays take full focus)
  const rallies = document.getElementById('ralliesContainer');
  if (rallies) { rallies.style.display='none'; rallies.innerHTML=''; }
  const ralliesLegend = document.getElementById('ralliesLegend');
  if (ralliesLegend) { ralliesLegend.style.display='none'; ralliesLegend.innerHTML=''; }
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

// New per-section status helpers for Simulate & Compare (parity with Skills)
function setSimulateStatus(msg, spinning=true){
  const el = document.getElementById('simulateStatus');
  if(!el) return; if(!msg){ el.textContent=''; return; }
  el.innerHTML = (spinning?'<span class="spinner"></span>':'') + msg;
}
function setCompareStatus(msg, spinning=true){
  const el = document.getElementById('compareStatus');
  if(!el) return; if(!msg){ el.textContent=''; return; }
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
  workingActive = true;
}
function clearWorking() {
  if (spinnerTimer) {
    clearInterval(spinnerTimer);
    spinnerTimer = null;
  }
  workingActive = false;
}
function copyOutput(){
  const pre=document.getElementById('output');
  if(!pre) return;
  // Retrieve raw text by stripping span tags if present
  let text='';
  if(pre.querySelector('span')){ text = pre.textContent; } else { text = pre.textContent || ''; }
  navigator.clipboard.writeText(text).then(()=>flashCopyStatus('Copied')).catch(()=>flashCopyStatus('Copy failed'));
}
function flashCopyStatus(msg){
  const el=document.getElementById('copyStatus'); if(!el) return;
  el.textContent=msg; setTimeout(()=>{ if(el.textContent===msg) el.textContent=''; }, 1600);
}
function out(obj) {
  clearWorking();
  const el = document.getElementById('output');
  if(!el) return;
  let raw = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
  if (!raw) { el.textContent=''; return; }
  function esc(s){ return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
  const lines = raw.split(/\n/).map(line => {
    let outLine=''; let i=0;
    while(i<line.length){
      const ch=line[i];
      if(ch==='"'){
        let j=i+1; let str=''; let escaped=false;
        for(;j<line.length;j++){
          const c=line[j]; str+=c;
          if(escaped){ escaped=false; continue; }
            if(c==='\\'){ escaped=true; continue; }
            if(c==='"') break;
        }
        const full='"'+str; const after=line.slice(j+1).trimStart(); const isKey=after.startsWith(':');
        outLine += `<span class="${isKey?'j-key':'j-string'}">${esc(full)}</span>`; i=j+1; continue;
      }
      if(/[-0-9]/.test(ch)){
        const m=line.slice(i).match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/);
        if(m){ outLine+=`<span class="j-number">${m[0]}</span>`; i+=m[0].length; continue; }
      }
      if(/[tfn]/.test(ch)){
        const rest=line.slice(i);
        if(rest.startsWith('true')) { outLine+='<span class="j-bool">true</span>'; i+=4; continue; }
        if(rest.startsWith('false')) { outLine+='<span class="j-bool">false</span>'; i+=5; continue; }
        if(rest.startsWith('null')) { outLine+='<span class="j-null">null</span>'; i+=4; continue; }
      }
      outLine+=esc(ch); i++;
    }
    return outLine;
  });
  el.innerHTML = lines.join('\n');
}

// Statistical match impact chart (horizontal CI lines)
function renderMatchImpactChart(stat) {
  try {
    if (!stat || !stat.statistical_analysis) return;
    const canvas = document.getElementById('matchImpactChart');
    if (!canvas) return;
  // Title intentionally set by caller (skills analysis) to include dynamic parameters

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
  // Add dynamic title content
  const paneTitle = document.getElementById('chartPaneTitle');
  if (paneTitle && sim && sim.summary) {
  const s = sim.summary; const pts = sim.parameters?.points; 
  paneTitle.textContent = `Simulation: ${s.team_a} ${s.team_a_win_rate.toFixed(1)}% vs ${s.team_b} ${s.team_b_win_rate.toFixed(1)}% (${fmtInt(pts)} pts, breakdown)`;
  }
  if (!sim || !sim.summary) return;
  const canvas = document.getElementById('matchImpactChart');
  if (!canvas) return;
  // Chart.js internal title kept concise; pane title above holds detailed context
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
    // Build optional breakdown tables if present
    let breakdownHTML = '';
    if (sim.breakdown) {
      const bd = sim.breakdown;
      // Point type distribution with % of total points
      if (bd.point_type_breakdown || bd.point_type_percentages) {
        const ptCounts = bd.point_type_breakdown || {};
        const ptPerc = bd.point_type_percentages || {};
        const totalPts = Object.values(ptCounts).reduce((a,b)=>a+b,0) || 1;
        const rows = Object.keys(ptCounts).sort().map(k=> {
          const cnt = ptCounts[k];
          const pct = ptPerc[k] != null ? ptPerc[k] : (cnt/totalPts*100);
          return `<tr><td>${k}</td><td>${cnt}</td><td>${pct.toFixed(2)}%</td></tr>`;}).join('');
        breakdownHTML += `<table class="match-impact" style="margin-top:8px"><thead><tr><th>Point Type</th><th>Count</th><th>% of Points</th></tr></thead><tbody>${rows}</tbody><caption>Distribution of point result types.</caption></table>`;
      }
      // Point type wins by team with share of that team's wins
      if (bd.team_a_point_types || bd.team_b_point_types) {
        const aPT = bd.team_a_point_types || {}; const bPT = bd.team_b_point_types || {};
        const types = Array.from(new Set([...Object.keys(aPT), ...Object.keys(bPT)])).sort();
        const aWins = sim.summary.team_a_wins || 1; const bWins = sim.summary.team_b_wins || 1;
        const rows = types.map(t=> {
          const aCnt = aPT[t]||0; const bCnt = bPT[t]||0;
          const aPct = aCnt ? (aCnt / aWins * 100) : 0;
          const bPct = bCnt ? (bCnt / bWins * 100) : 0;
          return `<tr><td>${t}</td><td>${aCnt}</td><td>${aPct.toFixed(1)}%</td><td>${bCnt}</td><td>${bPct.toFixed(1)}%</td></tr>`; }).join('');
        breakdownHTML += `<table class="match-impact" style="margin-top:8px"><thead><tr><th>Point Type</th><th>${team_a} Wins</th><th>${team_a} %Wins</th><th>${team_b} Wins</th><th>${team_b} %Wins</th></tr></thead><tbody>${rows}</tbody><caption>Point type wins with share of each team's total winning points.</caption></table>`;
      }
      // Serving advantage with serve share
      if (bd.serving_advantage) {
        const sa = bd.serving_advantage;
        const totalServes = (sa.team_a_serves || 0) + (sa.team_b_serves || 0) || 1;
        const aServeShare = ((sa.team_a_serves || 0) / totalServes * 100).toFixed(1);
        const bServeShare = ((sa.team_b_serves || 0) / totalServes * 100).toFixed(1);
        breakdownHTML += `<table class="match-impact" style="margin-top:8px"><thead><tr><th>Metric</th><th>${team_a}</th><th>${team_b}</th></tr></thead><tbody>`+
          `<tr><td>Serve Win %</td><td>${sa.team_a_serve_win_rate.toFixed(2)}%</td><td>${sa.team_b_serve_win_rate.toFixed(2)}%</td></tr>`+
          `<tr><td>Serves (Count / Share)</td><td>${sa.team_a_serves} / ${aServeShare}%</td><td>${sa.team_b_serves} / ${bServeShare}%</td></tr>`+
          `</tbody><caption>Serving performance metrics including share of total serves.</caption></table>`;
      }
      // Duration by type with % of points
      if (bd.duration_by_type) {
        const dbt = bd.duration_by_type;
        const totalPtsDur = Object.values(dbt).reduce((acc,v)=>acc+ (v.count||0),0) || 1;
        const rows = Object.keys(dbt).sort().map(k=>{ const v=dbt[k]; const pct=(v.count/totalPtsDur*100); return `<tr><td>${k}</td><td>${v.count}</td><td>${pct.toFixed(2)}%</td><td>${v.average.toFixed(2)}</td><td>${v.min}</td><td>${v.max}</td></tr>`; }).join('');
        breakdownHTML += `<table class="match-impact" style="margin-top:8px"><thead><tr><th>Point Type</th><th>Count</th><th>% of Points</th><th>Avg Dur</th><th>Min</th><th>Max</th></tr></thead><tbody>${rows}</tbody><caption>Point duration statistics with frequency share.</caption></table>`;
      }
    }
    tableContainer.innerHTML = `<table class="match-impact"><thead><tr><th>Team</th><th>Win %</th><th>Wins</th></tr></thead><tbody><tr><td>${team_a}</td><td>${team_a_win_rate.toFixed(2)}%</td><td>${sim.summary.team_a_wins}</td></tr><tr><td>${team_b}</td><td>${team_b_win_rate.toFixed(2)}%</td><td>${sim.summary.team_b_wins}</td></tr></tbody><caption>Single simulation results with breakdown.</caption></table>` + breakdownHTML;
  }
}

// Bar chart for comparison rankings plus matrix table
function renderComparisonChart(comp) {
  // Add dynamic pane title
  const paneTitle = document.getElementById('chartPaneTitle');
  if (paneTitle && comp && comp.results) {
    const pts = comp.parameters?.points; const teamCount = (comp.results.rankings||[]).length; 
    paneTitle.textContent = `Comparison (${teamCount} teams, ${fmtInt(pts)} pts/matchup)`;
  }
  if (!comp || !comp.results) return;
  const canvas = document.getElementById('matchImpactChart');
  if (!canvas) return;
  // Keep internal chart title short; pane title has full context
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
  // Support internal flag to suppress automatic startWorking (e.g., passive refresh on load)
  if (!options._noProgress && !workingActive) {
    startWorking();
  }
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
  // Passive refresh (e.g., on initial load) should not trigger spinner; provide _noProgress flag
  const data = await api('/api/teams', { _noProgress: true });
    const list = document.getElementById('teamList');
    if (!list) return; // defensive
    list.innerHTML='';
    data.teams.forEach(t=>{
      const li=document.createElement('li');
      const fname = t.file || '';
      const safeFile = fname.replace(/"/g,'');
      const teamDisplayName = t.name || '(unnamed)';
      li.innerHTML = `
        <span class=\"team-name\" onclick=\"openTeam('${safeFile}')\">
          <svg class=\"icon\" aria-hidden=\"true\"><use href='#icon-volleyball'/></svg>
          <span>${teamDisplayName}</span>
        </span>
        <span class=\"actions\">
          <button class=\"btn btn--secondary btn--icon btn--sm\" aria-label=\"Edit team\" onclick=\"event.stopPropagation(); openTeam('${safeFile}')\"><svg class=\"icon\" aria-hidden=\"true\"><use href='#icon-edit'/></svg></button>
          <button class=\"btn btn--danger btn--icon btn--sm\" aria-label=\"Delete team\" onclick=\"event.stopPropagation(); deleteTeam('${safeFile}')\"><svg class=\"icon\" aria-hidden=\"true\"><use href='#icon-delete'/></svg></button>
          <button class=\"btn btn--surface btn--icon btn--sm\" aria-label=\"Download team\" onclick=\"event.stopPropagation(); downloadTeam('${safeFile}')\"><svg class=\"icon\" aria-hidden=\"true\"><use href='#icon-download'/></svg></button>
        </span>`;
      list.appendChild(li);
    });
    // Populate selects with Basic, Advanced, then available teams
    const selects = ['simTeamA','simTeamB','skillsTeam','skillsOpponent','exTeamA','exTeamB']
      .map(id => document.getElementById(id))
      .filter(el => el && el.tagName === 'SELECT');
    if (selects.length) {
      selects.forEach(sel => {
        const prev = sel.value;
        sel.innerHTML='';
        const optBasic=document.createElement('option'); optBasic.value=''; optBasic.textContent='Basic'; sel.appendChild(optBasic);
        const optAdv=document.createElement('option'); optAdv.value='__ADVANCED__'; optAdv.textContent='Advanced'; sel.appendChild(optAdv);
        if (data.teams.length) {
          const optGroupLabel=document.createElement('option'); optGroupLabel.disabled=true; optGroupLabel.textContent='── Available Teams ──'; sel.appendChild(optGroupLabel);
        }
        data.teams.forEach(t=> { if(!t.name) return; const o=document.createElement('option'); o.value=t.file || t.name; o.textContent=t.name; sel.appendChild(o); });
        if (prev && Array.from(sel.options).some(o=>o.value===prev)) sel.value=prev; else sel.value='';
      });
    }
    // Populate base select with current teams
    const baseSel = document.getElementById('newTeamBase');
    if (baseSel) {
      const preserve = baseSel.value;
      baseSel.innerHTML='';
      const optB=document.createElement('option'); optB.value='__BASIC__'; optB.textContent='Basic Template'; baseSel.appendChild(optB);
      const optA=document.createElement('option'); optA.value='__ADVANCED__'; optA.textContent='Advanced Template'; baseSel.appendChild(optA);
      if (data.teams.length) {
        const sep=document.createElement('option'); sep.disabled=true; sep.textContent='── Existing Teams ──'; baseSel.appendChild(sep);
      }
      data.teams.forEach(t=> { if(!t.file) return; const o=document.createElement('option'); o.value=t.file; o.textContent=t.name || t.file; baseSel.appendChild(o); });
      if (preserve && Array.from(baseSel.options).some(o=>o.value===preserve)) baseSel.value=preserve;
    }
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

// New enhanced create using base source
async function createTeamEnhanced() {
  const name = document.getElementById('newTeamName').value.trim();
  const base = document.getElementById('newTeamBase').value;
  if (!name) return out('Enter a team name');
  try {
    const res = await api('/api/teams', { method: 'POST', body: JSON.stringify({ name, base }) });
    out(res);
    document.getElementById('newTeamName').value='';
    refreshTeams();
  } catch(e){ out(e.message); }
}

function triggerTeamUpload(){
  const input = document.getElementById('uploadTeamFile');
  if(!input) return;
  input.value=''; // reset so selecting same file again still triggers change
  input.onchange = () => {
    if(input.files && input.files.length){
      uploadTeam(input.files[0]);
    }
  };
  input.click();
}

async function uploadTeam(file) {
  const f = file;
  if(!f){ return out('No file selected'); }
  startWorking('Uploading team');
  const form = new FormData();
  form.append('file', f);
  try {
    const res = await fetch('/api/teams/upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    out(await res.json());
    refreshTeams();
  } catch (e) { out(e.message); }
}

// --- Modal Team Editor ---
function showTeamModal(){ const m=document.getElementById('teamEditorModal'); if(m) m.style.display='flex'; }
function closeTeamModal(){ const m=document.getElementById('teamEditorModal'); if(m) m.style.display='none'; }

async function openTeam(file){
  if(!file) return;
  try {
    const data = await api(`/api/teams/${encodeURIComponent(file)}`);
    const ed = document.getElementById('teamEditor');
    if(!ed) return;
    ed.value = data.content || '';
    ed.dataset.filename = data.file;
    const fn = document.getElementById('teamEditorFilename'); if(fn) fn.textContent = data.file;
    setTeamEditStatus(`Loaded ${data.file}`);
    showTeamModal();
  } catch(e){ setTeamEditStatus(e.message, true); }
}

async function saveTeamEdit(){
  const ed = document.getElementById('teamEditor');
  const file = ed.dataset.filename;
  if (!file) return setTeamEditStatus('No team loaded', true);
  try {
    // Use fetch directly to capture 400 with JSON errors
    startWorking('Saving team');
    const response = await fetch(`/api/teams/${encodeURIComponent(file)}`, { method: 'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ content: ed.value }) });
    clearWorking();
    if (!response.ok){
      let payload;
      try { payload = await response.json(); } catch { payload = { error: await response.text() }; }
      if (payload && payload.errors){
        // Populate detailed errors list
        const errList = document.getElementById('teamEditErrors');
        if (errList){
          errList.innerHTML='';
          payload.errors.forEach(eMsg => {
            const li=document.createElement('li');
            li.textContent=eMsg;
            errList.appendChild(li);
          });
          errList.style.display='block';
        }
        // Attempt to extract first probability reference for concise status
        const first = payload.errors[0];
        setTeamEditStatus(`${payload.error}: ${first}`, true);
        out(payload); // full JSON in output pane
      } else {
        setTeamEditStatus(payload.error || 'Save failed', true);
      }
      return;
    }
    const res = await response.json();
    setTeamEditStatus(`Saved ${res.file} ✓`);
    const errList = document.getElementById('teamEditErrors'); if (errList){ errList.innerHTML=''; errList.style.display='none'; }
    refreshTeams();
  } catch(e){ setTeamEditStatus(e.message, true); }
}

async function deleteTeam(file){
  if(!file) return;
  if(!confirm(`Delete ${file}?`)) return;
  try {
    const res = await api(`/api/teams/${encodeURIComponent(file)}`, { method: 'DELETE' });
    setTeamEditStatus(`Deleted ${res.file}`);
    const ed = document.getElementById('teamEditor');
    if(ed && ed.dataset.filename === file){ ed.value=''; delete ed.dataset.filename; }
    refreshTeams();
  } catch(e){ setTeamEditStatus(e.message, true); }
}

function downloadTeam(file){
  if(!file) return;
  window.open(`/api/teams/${encodeURIComponent(file)}/download`, '_blank');
}

function downloadCurrentTeam(){ const ed=document.getElementById('teamEditor'); if(!ed || !ed.dataset.filename) return setTeamEditStatus('No team loaded', true); downloadTeam(ed.dataset.filename); }

function setTeamEditStatus(msg,isError){ const el=document.getElementById('teamEditStatus'); if(!el) return; el.textContent=msg; el.style.color=isError?'#b71c1c':'#4a5b6d'; }

function formatTeamYaml(){
  const ed=document.getElementById('teamEditor'); if(!ed || !ed.value.trim()) return;
  // Placeholder: could integrate js-yaml client-side; for now just trims trailing spaces
  ed.value = ed.value.split('\n').map(l=>l.replace(/\s+$/,'')).join('\n');
  setTeamEditStatus('Whitespace trimmed');
}

async function simulateCommon(opts) {
  startWorking('Simulating');
  setSimulateStatus('Running simulation...', true);
  try {
    const team_a = document.getElementById('simTeamA').value.trim();
    const team_b = document.getElementById('simTeamB').value.trim();
    const points = document.getElementById('simPoints').value;
  // Always request breakdown unless explicitly disabled in opts
  const payload = Object.assign({ team_a, team_b, breakdown: true }, opts);
    if (points) payload.points = parseInt(points, 10);
    const res = await api('/api/simulate', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  clearMatchImpactDisplay();
  renderSimulationChart(res);
  setSimulateStatus('Simulation complete.', false);
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
      lastSkillsData = res; // store
      // Dynamic pane title with baseline & change
      const paneTitle = document.getElementById('chartPaneTitle');
      if (paneTitle) {
        const base = res.results.baseline_win_rate; const changeVal = res.results.change_value; const pts = res.parameters?.points || res.results.points_per_test; const tTeam = res.teams?.team || 'Team A'; const tOpp = res.teams?.opponent || 'Team B';
        paneTitle.textContent = `Skills Impact: ${tTeam} vs ${tOpp} (baseline ${base?.toFixed?base.toFixed(1):base}%, Δ each ${fmtChangeVal(changeVal)}, ${fmtInt(pts)} pts/test)`;
      }
      // Build skills array for generic renderer
      const improvs = res.results.parameter_improvements;
      const skills = Object.entries(improvs).map(([parameter, v]) => {
        const mean = v.match_improvement !== undefined ? v.match_improvement : (v.improvement || 0);
        const lower = v.match_lower ?? v.improvement_lower ?? mean;
        const upper = v.match_upper ?? v.improvement_upper ?? mean;
        const significant = lower > 0 || upper < 0;
        const pMean = v.improvement !== undefined ? v.improvement : undefined;
        const pLower = v.improvement_lower !== undefined ? v.improvement_lower : pMean;
        const pUpper = v.improvement_upper !== undefined ? v.improvement_upper : pMean;
        return { parameter, point: { mean: pMean, lower: pLower, upper: pUpper }, match: { mean, lower, upper }, significant };
      });
      if (skills.length) {
        renderMatchImpactChart({ statistical_analysis: true, skills });
        // After rendering restore dynamic pane title (renderMatchImpactChart doesn't override now)
      }
      // Legend supplementary note
      setTimeout(()=>{ const legendEl=document.getElementById('matchImpactLegend'); if(legendEl){ const base = res.results.baseline_win_rate; const changeVal = res.results.change_value; const pts = res.parameters?.points || res.results.points_per_test; const note=document.createElement('div'); note.style.fontSize='.6rem'; note.textContent=`Baseline win rate ${base?.toFixed?base.toFixed(2):base}%. Each parameter increased by ${fmtChangeVal(changeVal)} (additive). ${fmtInt(pts)} pts per test.`; legendEl.appendChild(note);} }, 60);
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
  setCompareStatus('Running comparison...', true);
  try {
    const raw = document.getElementById('compareTeams').value;
    const teams = raw.split(',')
      .map(s => s.trim())
      .filter(Boolean)
      .map(s => {
        const lowered = s.toLowerCase();
        if (lowered === 'basic') return 'Basic';
        if (lowered === 'advanced') return 'Advanced';
        return s; // pass through (file or existing team)
      });
    const payload = Object.assign({ teams }, opts);
    const res = await api('/api/compare', { method: 'POST', body: JSON.stringify(payload) });
    out(res);
  clearMatchImpactDisplay();
  renderComparisonChart(res);
  setCompareStatus('Comparison complete.', false);
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
  // Hide chart-specific artifacts so rallies sit at top cleanly
  const canvas = document.getElementById('matchImpactChart');
  if (canvas) { const ctx = canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width||canvas.clientWidth, canvas.height||canvas.clientHeight); canvas.style.display='none'; }
  const legendChart = document.getElementById('matchImpactLegend'); if (legendChart) legendChart.innerHTML='';
  const table = document.getElementById('matchImpactTableContainer'); if (table) table.innerHTML='';
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
  // No need to clearMatchImpactDisplay here; we explicitly cleared chart artifacts above.
  // Clear any lingering processing status/spinner
  setMatchImpactStatus('', false);
}
