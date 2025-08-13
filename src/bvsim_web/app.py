from __future__ import annotations
import io
import json
import os
import traceback
from typing import Any, Dict, List, Optional
from pathlib import Path
from flask import Flask, jsonify, request, send_file

from bvsim import __version__
from bvsim_core.team import Team
from bvsim_cli.templates import get_basic_template, get_advanced_template, create_team_template
from bvsim_cli.comparison import compare_teams, format_comparison_text
from bvsim_cli.simulation import run_large_simulation
from bvsim_stats.models import SimulationResults, PointResult
from bvsim_stats.analysis import analyze_simulation_results, full_skill_analysis, multi_delta_skill_analysis

TEAM_GLOB_PATTERNS = ["team_*.yaml", "team_*.yml", "*.yaml", "*.yml"]


def list_team_files() -> List[Path]:
    files: List[Path] = []
    seen: set[str] = set()
    include_tests = os.getenv('BVSIM_INCLUDE_TEST_TEAMS') == '1'
    hidden_name_fragments = { 'webtestteam', 'sample_team_a', 'sample_team_b' }
    # Directories to search: project root (cwd), optional tests/data/teams for curated test fixtures
    search_dirs = [Path.cwd()]
    test_teams_dir = Path.cwd() / 'tests' / 'data' / 'teams'
    if test_teams_dir.exists():
        search_dirs.append(test_teams_dir)
    for directory in search_dirs:
        for pattern in TEAM_GLOB_PATTERNS:
            for p in directory.glob(pattern):
                if p.suffix.lower() in ('.yaml', '.yml') and p.name not in seen:
                    # Skip internal/test/demo files unless explicitly included
                    lowered = p.name.lower()
                    if not include_tests:
                        if any(fragment in lowered for fragment in hidden_name_fragments):
                            continue
                    try:
                        Team.from_yaml_file(str(p))
                        files.append(p)
                        seen.add(p.name)
                    except Exception:
                        continue
    return files


def load_team(name_or_file: str) -> Team:
    """Load a team by name or path. Tries current working directory and project root.
    Raises FileNotFoundError if not found instead of silently defaulting so caller can decide fallback policy."""
    search_names = []
    p = Path(name_or_file)
    if p.suffix:
        search_names.append(p.name)
    else:
        # Accept raw name which could correspond to 'name.yaml' or 'team_<normalized>.yaml'
        base = p.name
        normalized = base.lower().replace(' ', '_')
        search_names.extend([
            base + '.yaml',
            f'team_{normalized}.yaml'
        ])
    # candidate directories: cwd, cwd/.. (project root), cwd/../templates maybe not needed
    dirs = [Path.cwd(), Path.cwd().parent]
    test_teams_dir = Path.cwd() / 'tests' / 'data' / 'teams'
    if test_teams_dir.exists():
        dirs.append(test_teams_dir)
    for directory in dirs:
        for fname in search_names:
            candidate = directory / fname
            if candidate.exists():
                return Team.from_yaml_file(str(candidate))
    raise FileNotFoundError(f"Team file not found: {name_or_file}")


def error_response(msg: str, status: int = 400):
    return jsonify({"error": msg}), status


def register_routes(app: Flask) -> None:
    @app.get("/api/version")
    def api_version():
        return jsonify({"version": __version__})

    @app.get("/api/teams")
    def api_list_teams():
        teams = []
        for p in list_team_files():
            try:
                t = Team.from_yaml_file(str(p))
                teams.append({"name": t.name, "file": p.name})
            except Exception as e:
                teams.append({"file": p.name, "error": str(e)})
        return jsonify({"teams": teams})

    @app.post("/api/teams")
    def api_create_team():
        data = request.get_json(force=True, silent=True) or {}
        name = data.get("name")
        template = data.get("template", "basic")
        if not name:
            return error_response("Missing 'name'")
        output_file = f"team_{name.lower().replace(' ', '_')}.yaml"
        try:
            template_type = "advanced" if template == "advanced" else "basic"
            create_team_template(team_name=name, template_type=template_type, output_file=output_file, interactive=False)
            return jsonify({"created": True, "file": output_file})
        except Exception as e:
            return error_response(str(e), 500)

    @app.post("/api/teams/upload")
    def api_upload_team():
        if 'file' not in request.files:
            return error_response("No file part")
        f = request.files['file']
        if f.filename == '':
            return error_response("Empty filename")
        path = Path(f.filename)
        if path.suffix.lower() not in ('.yaml', '.yml'):
            return error_response("Only .yaml/.yml allowed")
        content = f.read()
        path.write_bytes(content)
        # validate
        try:
            Team.from_yaml_file(str(path))
            return jsonify({"uploaded": True, "file": path.name})
        except Exception as e:
            return error_response(f"Invalid team file: {e}", 400)

    @app.get("/api/teams/<name>/download")
    def api_download_team(name: str):
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix('.yaml')
        if not path.exists():
            return error_response("Team file not found", 404)
        return send_file(str(path), as_attachment=True, download_name=path.name)

    @app.post("/api/simulate")
    def api_simulate():
        data = request.get_json(force=True, silent=True) or {}
        team_a_raw = (data.get("team_a") or "").strip()
        team_b_raw = (data.get("team_b") or "").strip()
        quick = data.get("quick")
        accurate = data.get("accurate")
        points = data.get("points")
        # Web UI now defaults to requesting breakdown details; treat absence as True
        breakdown = data.get("breakdown", True)
        seed = data.get("seed")
        used_defaults = False
        try:
            # Determine teams based on provided values
            if not team_a_raw and not team_b_raw:
                team_a = Team.from_dict(get_basic_template("Team A"))
                team_b = Team.from_dict(get_basic_template("Team B"))
                used_defaults = True
                note = "Both team names blank; using Basic templates (Team A vs Team B)."
            else:
                note_parts = []
                if not team_a_raw:
                    team_a = Team.from_dict(get_basic_template("Team A"))
                    used_defaults = True
                    note_parts.append("Team A blank -> Basic template")
                elif team_a_raw == "__ADVANCED__":
                    team_a = Team.from_dict(get_advanced_template("Team A"))
                    note_parts.append("Team A Advanced template")
                else:
                    team_a = load_team(team_a_raw)
                if not team_b_raw:
                    team_b = Team.from_dict(get_basic_template("Team B"))
                    used_defaults = True
                    note_parts.append("Team B blank -> Basic template")
                elif team_b_raw == "__ADVANCED__":
                    team_b = Team.from_dict(get_advanced_template("Team B"))
                    note_parts.append("Team B Advanced template")
                else:
                    team_b = load_team(team_b_raw)
                note = "; ".join(note_parts) if note_parts else None

            if quick:
                num_points = 10_000
            elif accurate:
                num_points = 400_000
            else:
                num_points = points or 200_000

            sim_data = run_large_simulation(team_a=team_a, team_b=team_b, num_points=num_points, seed=seed, show_progress=False)
            point_results = [
                PointResult(
                    serving_team=p['serving_team'],
                    winner=p['winner'],
                    point_type=p['point_type'],
                    duration=p['duration'],
                    states=p['states']
                ) for p in sim_data['points']
            ]
            results = SimulationResults(
                team_a_name=sim_data['team_a_name'],
                team_b_name=sim_data['team_b_name'],
                total_points=sim_data['total_points'],
                points=point_results
            )
            analysis = analyze_simulation_results(results, breakdown=breakdown)
            payload = {
                "summary": {
                    "team_a": results.team_a_name,
                    "team_b": results.team_b_name,
                    "team_a_win_rate": analysis.team_a_win_rate,
                    "team_b_win_rate": analysis.team_b_win_rate,
                    "team_a_wins": analysis.team_a_wins,
                    "team_b_wins": analysis.team_b_wins,
                    "total_points": analysis.total_points,
                    "average_duration": analysis.average_duration,
                },
                "parameters": {
                    "points": num_points,
                    "breakdown": breakdown,
                    "used_defaults": used_defaults
                }
            }
            if used_defaults and note:
                payload["note"] = note
            if breakdown:
                # The analysis.to_dict() currently stores detailed info under 'breakdown_data'.
                # Build a consolidated breakdown payload expected by frontend rendering logic.
                analysis_dict = analysis.to_dict()
                detailed = analysis_dict.get('breakdown_data') or {}
                payload["breakdown"] = {
                    # core distributions
                    "point_type_breakdown": analysis_dict.get('point_type_breakdown'),
                    "point_type_percentages": analysis_dict.get('point_type_percentages'),
                    # detailed sections
                    **{k: v for k, v in detailed.items() if k in (
                        'team_a_point_types','team_b_point_types','duration_by_type','serving_advantage'
                    )}
                }
            return jsonify(payload)
        except Exception as e:
            traceback.print_exc()
            if isinstance(e, FileNotFoundError):
                return error_response(str(e), 404)
            return error_response(f"Simulation failed: {e}", 500)

    @app.post("/api/compare")
    def api_compare():
        data = request.get_json(force=True, silent=True) or {}
        team_names = data.get("teams") or []
        used_defaults = False
        note = None
        teams = []
        try:
            if len(team_names) == 0:
                # Default: Basic vs Basic
                teams = [Team.from_dict(get_basic_template("Team A")), Team.from_dict(get_basic_template("Team B"))]
                used_defaults = True
                note = "No teams supplied; using Basic templates (Team A vs Team B)."
            elif len(team_names) == 1:
                # One provided -> load it (or advanced sentinel) + Basic
                tn = team_names[0]
                lowered = tn.lower()
                if tn == "__ADVANCED__" or lowered == "advanced":
                    teams.append(Team.from_dict(get_advanced_template("Team A")))
                elif lowered == "basic":
                    teams.append(Team.from_dict(get_basic_template("Team A")))
                else:
                    teams.append(load_team(tn))
                teams.append(Team.from_dict(get_basic_template("Team B")))
                used_defaults = True
                note = "Only one team supplied; opponent set to Basic template (Team B)."
            else:
                teams = []
                for i, n in enumerate(team_names):
                    lowered = n.lower()
                    if n == "__ADVANCED__" or lowered == "advanced":
                        # Preserve explicit 'Advanced' keyword label if user typed it
                        label = "Advanced" if lowered == "advanced" else f"Team {chr(65+i)}"
                        tdata = get_advanced_template(label)
                        tdata['name'] = label
                        teams.append(Team.from_dict(tdata))
                    elif lowered == "basic":
                        label = "Basic"
                        tdata = get_basic_template(label)
                        tdata['name'] = label
                        teams.append(Team.from_dict(tdata))
                    else:
                        teams.append(load_team(n))
                if len(teams) < 2:
                    return error_response("Need at least two valid teams")
        except FileNotFoundError as e:
            return error_response(str(e), 404)
        quick = data.get("quick")
        accurate = data.get("accurate")
        points = data.get("points")
        try:
            if quick:
                num_points = 10_000
            elif accurate:
                num_points = 400_000
            else:
                # Standard default: 200k points
                num_points = points or 200_000
            results = compare_teams(teams, points_per_matchup=num_points)
            payload = {"parameters": {"points": num_points, "used_defaults": used_defaults}, "results": results}
            if used_defaults and note:
                payload["note"] = note
            return jsonify(payload)
        except Exception as e:
            return error_response(f"Compare failed: {e}", 500)

    @app.post("/api/examples")
    def api_examples():
        data = request.get_json(force=True, silent=True) or {}
        team_a_name = data.get("team_a") or "Team A"
        team_b_name = data.get("team_b") or "Team B"
        count = int(data.get("count", 5))
        seed = data.get("seed")
        try:
            # New rule: any blank (defaulted to label Team A/Team B) should resolve to Basic template if file not found
            try:
                team_a = load_team(team_a_name)
            except FileNotFoundError:
                team_a = Team.from_dict(get_basic_template("Team A"))
            try:
                team_b = load_team(team_b_name)
            except FileNotFoundError:
                team_b = Team.from_dict(get_basic_template("Team B"))
            rallies = []
            for i in range(count):
                serving_team = 'A' if i % 2 == 0 else 'B'
                point = run_point(team_a, team_b, serving_team=serving_team, seed=(seed + i) if seed else None)
                rallies.append(point)
            return jsonify({"rallies": rallies})
        except Exception as e:
            return error_response(f"Examples failed: {e}", 500)

    # Helper for examples: replicate concise rally representation using existing state machine
    from bvsim_core.state_machine import simulate_point as simulate_point_state
    def run_point(team_a: Team, team_b: Team, serving_team: str, seed: Optional[int]):
        point = simulate_point_state(team_a, team_b, serving_team=serving_team, seed=seed)
        # Build concise description similar to CLI output
        state_parts = []
        for s in point.states:
            action_abbrev = {'serve': 'srv', 'receive': 'rcv', 'set': 'set', 'attack': 'att', 'block': 'blk', 'dig': 'dig'}.get(s.action, s.action)
            quality_map = {'excellent': 'exc', 'good': 'gd', 'poor': 'pr', 'error': 'err', 'ace': 'ace', 'in_play': 'ok', 'kill': 'kill', 'defended': 'def', 'stuff': 'stuff', 'deflection_to_attack': 'def→att', 'deflection_to_defense': 'def→def', 'no_touch': 'miss'}
            quality_abbrev = quality_map.get(s.quality, s.quality)
            state_parts.append(f"{s.team}.{action_abbrev}({quality_abbrev})")
        rally_str = f"[{point.winner}] " + "→".join(state_parts) + f" → {point.point_type}"
        return {"winner": point.winner, "point_type": point.point_type, "sequence": rally_str}

    @app.post("/api/skills")
    def api_skills():
        data = request.get_json(force=True, silent=True) or {}
        team_name_raw = (data.get("team") or "").strip()
        opponent_name_raw = (data.get("opponent") or "").strip()
        custom_files = data.get("custom")  # list of delta yaml
        improve = data.get("improve")  # e.g. 0.05 or 5%
        quick = data.get("quick")
        accurate = data.get("accurate")
        points = data.get("points")
        runs = data.get("runs")  # not implementing multi-run for MVP (could extend)
        try:
            used_defaults = False
            note = None
            if not team_name_raw and not opponent_name_raw:
                # Default both Basic
                team = Team.from_dict(get_basic_template("Team A"))
                opponent = Team.from_dict(get_basic_template("Team B"))
                used_defaults = True
                note = "Both team names blank; using Basic templates (Team A vs Team B)."
            else:
                note_parts = []
                if not team_name_raw:
                    team = Team.from_dict(get_basic_template("Team A"))
                    used_defaults = True
                    note_parts.append("Team blank -> Basic template")
                elif team_name_raw == "__ADVANCED__":
                    team = Team.from_dict(get_advanced_template("Team A"))
                    note_parts.append("Team Advanced template")
                else:
                    team = load_team(team_name_raw)
                if not opponent_name_raw:
                    opponent = Team.from_dict(get_basic_template("Team B"))  # other defaults to Basic per rule
                    used_defaults = True
                    note_parts.append("Opponent blank -> Basic template")
                elif opponent_name_raw == "__ADVANCED__":
                    opponent = Team.from_dict(get_advanced_template("Team B"))
                    note_parts.append("Opponent Advanced template")
                else:
                    opponent = load_team(opponent_name_raw)
                if note_parts:
                    note = "; ".join(note_parts)
            if quick:
                points_per_test = 10_000
            elif accurate:
                points_per_test = 400_000
            else:
                points_per_test = points or 200_000
            if improve:
                if isinstance(improve, str) and improve.endswith('%'):
                    change_value = float(improve[:-1]) / 100.0
                else:
                    change_value = float(improve)
            else:
                change_value = 0.05
            if custom_files:
                results = multi_delta_skill_analysis(team=team, opponent=opponent, deltas_files=custom_files, points_per_test=points_per_test)
            else:
                results = full_skill_analysis(team=team, opponent=opponent, change_value=change_value, points_per_test=points_per_test, parallel=True)
            response = {"parameters": {"points": points_per_test, "change_value": change_value, "custom": bool(custom_files), "used_defaults": used_defaults}, "results": results, "teams": {"team": team.name, "opponent": opponent.name}}
            if used_defaults and note:
                response["note"] = note
            return jsonify(response)
        except Exception as e:
            traceback.print_exc()
            return error_response(f"Skills analysis failed: {e}", 500)

    @app.post("/api/analyze")
    def api_analyze():
        data = request.get_json(force=True, silent=True) or {}
        file = data.get("file")
        breakdown = data.get("breakdown", False)
        if not file:
            return error_response("Missing 'file'")
        p = Path(file)
        if not p.exists():
            return error_response("File not found", 404)
        try:
            results = SimulationResults.from_json_file(str(p))
            analysis = analyze_simulation_results(results, breakdown=breakdown)
            return jsonify(analysis.to_dict())
        except Exception as e:
            return error_response(f"Analyze failed: {e}", 500)

    # Serve frontend
    @app.get("/")
    def index_root():
        return app.send_static_file("index.html")

    # Favicon route: serve single SVG for all favicon requests (lightweight, modern browsers support SVG)
    @app.get('/favicon.ico')
    def favicon():
        svg_path = Path(app.static_folder) / 'favicon.svg'
        if svg_path.exists():
            return send_file(str(svg_path), mimetype='image/svg+xml')
        return ('', 204)
