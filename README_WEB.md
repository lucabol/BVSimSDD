# BVSim Web Interface (MVP)

A minimal Flask-based web UI exposing the core BVSim simulator features without modifying existing library code.

## Features
- List / create / upload team YAML files (stored in working directory)
- Run simulations with quick / standard / accurate presets (10k / 200k / 400k points)
- Perform skills analysis (full skill impact or custom scenario files) with graphical impact chart
- Compare multiple teams
- Generate rally examples
- Download existing team YAML files
- Collapsible raw JSON output panel (minimized by default) to keep UI clean

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
