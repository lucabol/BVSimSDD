import json
import pytest

from bvsim_web import create_app
from bvsim_core.summary import cuda_backend_available

@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def test_version(client):
    rv = client.get('/api/version')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'version' in data


def test_create_team_and_list(client):
    # Use overwrite to make test idempotent if file persists from earlier test run
    rv = client.post('/api/teams', json={"name": "WebTestTeam", "template": "basic", "overwrite": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data.get('created')
    # Enable inclusion of test teams in list endpoint
    import os
    os.environ['BVSIM_INCLUDE_TEST_TEAMS'] = '1'
    # list
    rv2 = client.get('/api/teams')
    assert rv2.status_code == 200
    names = [t.get('name') for t in rv2.get_json().get('teams', [])]
    assert any('WebTestTeam' in (n or '') for n in names)


def test_create_team_rejects_inconsistent_probabilities_without_writing(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    content = """name: Invalid Totals
serve_probabilities:
  ace: 0.2
  in_play: 0.7
  error: 0.05
"""

    rv = client.post(
        '/api/teams',
        json={"name": "Invalid Totals", "content": content},
    )

    assert rv.status_code == 400
    assert not (tmp_path / "team_invalid_totals.yaml").exists()


def test_simulate_quick(client):
    rv = client.post('/api/simulate', json={"team_a": "WebTestTeam", "team_b": "WebTestTeam", "quick": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert 'summary' in data
    assert data['summary']['team_a_win_rate'] >= 0
    assert data['parameters']['backend'] in {'python', 'numba'}
    assert sum(data['breakdown']['point_type_breakdown'].values()) == 10_000
    assert data['breakdown']['duration_by_type']


def test_simulate_accepts_explicit_cpu_backend(client):
    rv = client.post(
        '/api/simulate',
        json={
            "team_a": "WebTestTeam",
            "team_b": "WebTestTeam",
            "quick": True,
            "backend": "cpu",
        },
    )
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters']['requested_backend'] == 'cpu'
    assert data['parameters']['backend'] in {'python', 'numba'}


def test_simulate_accepts_explicit_cuda_backend_when_available(client):
    if not cuda_backend_available():
        pytest.skip("CUDA is unavailable")
    rv = client.post(
        '/api/simulate',
        json={
            "team_a": "WebTestTeam",
            "team_b": "WebTestTeam",
            "quick": True,
            "backend": "cuda",
        },
    )
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters']['requested_backend'] == 'cuda'
    assert data['parameters']['backend'] == 'cuda'


def test_simulate_blank_defaults(client):
    # Both team names blank: should auto-use defaults and not 500
    rv = client.post('/api/simulate', json={"team_a": "", "team_b": "", "quick": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True
    assert data['summary']['team_a_win_rate'] >= 0

def test_simulate_one_blank_other_basic(client):
    # Provide only team_a, leave team_b blank -> team_b should be Basic (not Advanced)
    rv = client.post('/api/teams', json={"name": "SoloTeamX", "template": "basic", "overwrite": True})
    assert rv.status_code == 200
    rv2 = client.post('/api/simulate', json={"team_a": "tests/data/teams/team_soloteamx.yaml", "team_b": "", "quick": True})
    assert rv2.status_code == 200, rv2.data
    data = rv2.get_json()
    assert data['parameters'].get('used_defaults') is True
    # Team B should be Basic template name "Team B" (since created basic differs, we just ensure note present or used_defaults)
    assert data['summary']['team_b'] == 'Team B'

def test_skills_blank_defaults(client):
    rv = client.post(
        '/api/skills',
        json={"points": 20, "seed": 123},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True
    assert data['teams']['team'] == 'Team A'
    assert data['teams']['opponent'] == 'Team B'
    assert data['parameters']['master_seed'] == 123
    assert data['parameters']['runs'] == 1
    assert data['effect_statistics'][0]['point_lower'] is None
    assert data['holdout_statistics'] == []

def test_skills_one_blank_other_basic(client):
    rv = client.post(
        '/api/skills',
        json={
            "team": "tests/data/teams/team_soloteamx.yaml",
            "points": 20,
            "runs": 1,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    # Opponent blank -> Basic template Team B
    assert data['teams']['opponent'] == 'Team B'


def test_compare(client):
    # Ensure at least two teams exist
    client.post('/api/teams', json={"name": "WebTestTeam2", "template": "basic"})
    rv = client.post('/api/compare', json={"teams": ["WebTestTeam", "WebTestTeam2"], "quick": True})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'results' in data
    assert set(data['parameters']['backends']).issubset({'python', 'numba'})


def test_compare_accepts_explicit_cpu_backend(client):
    rv = client.post(
        '/api/compare',
        json={
            "teams": ["WebTestTeam", "WebTestTeam2"],
            "quick": True,
            "backend": "cpu",
        },
    )
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters']['requested_backend'] == 'cpu'
    assert set(data['parameters']['backends']).issubset({'python', 'numba'})

def test_compare_basic_advanced_keywords(client):
    # Use Basic and Advanced keywords directly (case-insensitive) without existing files
    rv = client.post('/api/compare', json={"teams": ["Basic", "Advanced"], "quick": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert 'results' in data
    assert set(data['results']['teams']) == {"Basic", "Advanced"}

def test_compare_defaults_when_empty(client):
    rv = client.post('/api/compare', json={})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True
    assert 'results' in data

def test_compare_single_defaults_other(client):
    rv = client.post('/api/compare', json={"teams": ["WebTestTeam"]})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True


def test_examples(client):
    rv = client.post('/api/examples', json={"team_a": "WebTestTeam", "team_b": "WebTestTeam2", "count": 3})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'rallies' in data and len(data['rallies']) == 3


def test_skills_quick(client):
    rv = client.post('/api/skills', json={"team": "WebTestTeam", "quick": True, "improve": "5%", "runs": 1})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'results' in data


def test_skills_accepts_explicit_cuda_backend_when_available(client):
    if not cuda_backend_available():
        pytest.skip("CUDA is unavailable")
    rv = client.post(
        '/api/skills',
        json={
            "team": "WebTestTeam",
            "quick": True,
            "runs": 1,
            "backend": "cuda",
        },
    )
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters']['requested_backend'] == 'cuda'
    assert data['parameters']['backend'] == 'cuda'


def test_skills_explicit_multi_run_includes_holdout(client):
    rv = client.post(
        '/api/skills',
        json={"points": 20, "runs": 2, "seed": 456},
    )

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters']['runs'] == 2
    assert len(data['holdout_statistics']) == 3
    assert all(
        row['adjusted_p_value'] is not None
        for row in data['effect_statistics']
    )
def test_scenarios_default_to_one_interactive_run(client):
    rv = client.post(
        '/api/skills',
        json={
            "custom": ["sample_team_a.yaml"],
            "points": 20,
            "seed": 789,
        },
    )

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters']['runs'] == 1
    assert data['holdout_statistics'] == []
    assert data['skills'][0]['match']['lower'] is None


def test_compare_honors_custom_point_count(client):
    rv = client.post(
        '/api/compare',
        json={"teams": ["Basic", "Advanced"], "points": 20},
    )

    assert rv.status_code == 200
    assert rv.get_json()['parameters']['points'] == 20


def test_workload_controls_are_present(client):
    rv = client.get('/')

    assert rv.status_code == 200
    page = rv.get_data(as_text=True)
    assert 'id="skillsRuns"' in page
    assert 'id="scenariosRuns"' in page
    assert 'id="comparePoints"' in page
    assert 'id="simBackend"' in page
    assert 'id="compareBackend"' in page
    assert 'id="skillsBackend"' in page
    assert 'id="scenariosBackend"' in page
    assert 'onclick="openSelectedScenario()"' in page
    assert 'id="visualTeamEditor"' in page
    assert 'id="teamsStatus"' in page
    assert 'id="addTeamBtn"' in page


def test_scenario_visual_editor_api(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scenario = tmp_path / "scenario_visual.yaml"
    scenario.write_text("serve_probabilities.ace: 0.05\n")

    rv = client.get('/api/scenarios/scenario_visual.yaml')
    assert rv.status_code == 200
    assert rv.get_json()['content'] == "serve_probabilities.ace: 0.05\n"

    updated = "serve_probabilities.ace: 0.08\n"
    rv = client.put(
        '/api/scenarios/scenario_visual.yaml',
        json={"content": updated},
    )
    assert rv.status_code == 200
    assert scenario.read_text() == updated


def test_scenario_visual_editor_rejects_non_numeric_values(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scenario = tmp_path / "scenario_visual.yaml"
    scenario.write_text("serve_probabilities.ace: 0.05\n")

    rv = client.put(
        '/api/scenarios/scenario_visual.yaml',
        json={"content": "serve_probabilities.ace: aggressive\n"},
    )

    assert rv.status_code == 400
    assert scenario.read_text() == "serve_probabilities.ace: 0.05\n"


def test_scenario_visual_editor_accepts_team_variant(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scenario = tmp_path / "scenario_team.yaml"
    content = """name: Visual Variant
serve_probabilities:
  ace: 0.2
  in_play: 0.75
  error: 0.05
"""
    scenario.write_text(content)

    rv = client.put(
        '/api/scenarios/scenario_team.yaml',
        json={"content": content},
    )

    assert rv.status_code == 200
    assert scenario.read_text() == content
