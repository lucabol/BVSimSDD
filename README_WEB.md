# BVSim Web Interface (MVP)

A minimal Flask-based web UI exposing the core BVSim simulator features without modifying existing library code.

## Quick Start (Scripts)

After installing dependencies (see Running section), you can launch the web UI with provided helper scripts:

### Bash (Linux/macOS)
```bash
./run_web.sh                # default host 0.0.0.0, port 8000, debug on
./run_web.sh 5000           # override port
./run_web.sh 5000 127.0.0.1 # custom port + host
BVSIM_WEB_PORT=9000 BVSIM_WEB_DEBUG=false ./run_web.sh
```

### Windows (CMD)
```bat
run_web.bat                 REM default 0.0.0.0:8000
run_web.bat 5000            REM custom port
run_web.bat 5000 127.0.0.1  REM custom port + host
set BVSIM_WEB_PORT=9000 & set BVSIM_WEB_DEBUG=false & run_web.bat
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| BVSIM_WEB_HOST | 0.0.0.0 | Interface to bind the server |
| BVSIM_WEB_PORT | 8000 | Listening port |
| BVSIM_WEB_DEBUG | true | Flask debug / reload mode |
| BVSIM_WEB_WORKERS | (unset) | If set and gunicorn installed, use that many workers (Unix) |

The Python entrypoint (`python -m bvsim_web`) now respects these environment variables.

## Features
- List / create / upload team YAML files (stored in working directory)
- Run simulations with quick / standard / accurate presets (10k / 200k / 400k points)
- Perform skills analysis (full skill impact or custom scenario files) with graphical impact chart
- Compare multiple teams
- Generate rally examples
	- Visual timeline view of rally sequences with action qualities & winner highlighting
- Download existing team YAML files
- Collapsible raw JSON output panel (minimized by default) to keep UI clean
- Supports **minimal-diff team files**: uploaded / created team YAMLs may omit unchanged top-level probability sections; omitted sections auto-fill from the Basic template.

## Architecture
Package `bvsim_web` (separate from core) provides:
- `create_app()` factory returning a Flask app with JSON API + static UI
- Direct use of internal Python modules (no subprocess CLI calls)
- Synchronous request handling for simplicity (long operations block until done)

## Endpoints & Point Defaults
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/version | Library version |
| GET | /api/teams | List discovered team YAML files |
| POST | /api/teams {name, template} | Create new team (basic/advanced) |
| POST | /api/teams/upload (multipart) | Upload an existing team YAML |
| GET | /api/teams/<name>/download | Download team YAML |
| POST | /api/simulate | Run a simulation (Quick=10k, Standard=200k default, Accurate=400k) |
| POST | /api/skills | Skills analysis (Quick=10k, Standard=200k default, Accurate=400k) |
| POST | /api/compare | Compare teams (Quick=10k, Standard=200k default, Accurate=400k) |
| POST | /api/examples | Rally examples (team_a, team_b, count, seed?) |
| POST | /api/analyze | Analyze existing simulation results file {file, breakdown?} |

## Running
Install Flask (not added to core requirements to avoid altering existing setup):

```bash
pip install Flask
python -m bvsim_web  # runs on http://localhost:8000
```

Or create an app programmatically:
```python
from bvsim_web import create_app
app = create_app()
app.run()
```

## Frontend
Served at `/` (static). Uses fetch + simple DOM updates. All responses are JSON.

### Visualization Pane
Running a Skills Analysis now renders a bar/line composite chart (Chart.js) showing:
- Baseline win rate (line)
- New win rate per parameter improvement (bars, top 25 by absolute improvement)
- Delta improvement line (right axis, point win rate delta in percentage points)

Hover tooltips provide exact values. The underlying full JSON remains available in the Output panel.

### Collapsible Output Panel
The Output (raw JSON / logs) section is minimized by default to reduce scrolling. Click the Output header badge (Show / Hide) to toggle visibility. Programmatic writes do not auto-expand it— preserving user choice during iterative debugging.

### Rally Timeline Visualization (NEW)
Using the Rallies panel (Generate button) now produces a graphical timeline: each action (Serve, Receive, Set, Attack, etc.) is a colored card ordered left-to-right with arrows. Card border/background color indicates the acting team (Team A blue, Team B red). A quality pill (excellent, good, ok, error, ace) is color-coded (green, blue, gray, red, purple). The result (point_type) appears as a labeled box at the end. Hovering over any step shows the raw token. The full original sequence string remains in the footer and the full JSON is still visible in the JSON Output panel.

Parsing rules: sequence tokens like `A.att(err)` become {team:A, action:Attack, quality:error}. Quality synonyms are normalized (exc/excellent → excellent, gd/good → good, err/error → error). Unknown or unmatched tokens are ignored (kept in raw text).

Limitations: currently supports single-letter team codes (A/B) or names beginning with those letters. Extend `parseRallySequence` in `static/app.js` to support more complex naming if needed.

## Notes & Limitations
- Long-running analyses block request (consider async/job queue for large workloads later)
- No authentication (intended for local usage / trusted environment)
- Skills endpoint currently single-run (statistical multi-run can be layered later)
- Team editing is not in-browser; edit YAML files directly

### Point Count Logic
For simulate, skills, and compare endpoints:
- Quick: 10,000 points
- Accurate: 400,000 points
- Standard (no flag, no explicit points): 200,000 points
Providing an explicit `points` overrides all presets.

### Default Team Selection Rules (Updated)
- Simulate / Skills / Examples: If a team field is left blank, that side becomes a Basic template (Team A or Team B label). If both are blank, it runs Basic vs Basic.
- Compare: If no teams are supplied, comparison runs Basic (Team A) vs Basic (Team B). A single provided team will be compared against a Basic template opponent (Team B).

## Future Enhancements
1. Async job queue with progress polling
2. WebSocket/live updates for long simulations
3. Inline probability editor UI
4. Additional chart visualizations (win rate matrices, multi-run confidence intervals)
5. Authentication & role-based access
6. Multi-run statistical skills endpoint parity with CLI
7. Dockerfile for easy deployment

---
This MVP keeps footprint small while exposing core simulator capabilities.

### Added: JSON Syntax Highlighting
The JSON Output panel now uses a lightweight custom tokenizer (no external JS dependency) for syntax coloring (keys, strings, numbers, booleans, null). This avoids layout glitches previously seen with the CDN highlight library. To adjust colors, edit the `.j-key`, `.j-string`, `.j-number`, `.j-bool`, and `.j-null` CSS rules in `index.html`.

### Added: YAML Team Editor Highlighting (NEW)
The Team editing modal now features YAML syntax highlighting, line numbers, and basic editing keybindings powered by a lightweight CodeMirror 6 setup (loaded via CDN). The original `<textarea>` remains in the DOM (hidden) for graceful degradation; if scripts fail to load, plain text editing still works.

Implementation details:
- Module imports for `@codemirror/state`, `@codemirror/view`, `@codemirror/lang-yaml`, and `@codemirror/commands` included inline in `static/index.html`.
- Editor initialized lazily after DOMContentLoaded; content syncs on load, save, and format actions.
- Save action always pulls current document text from the editor instance before sending to the `/api/teams/<file>` endpoint.
- Formatting currently trims trailing whitespace only (future enhancement: integrate js-yaml for structural formatting).

To adjust appearance: edit the `.cm-editor`, `.cm-gutters`, or line number color rules in `index.html`.

