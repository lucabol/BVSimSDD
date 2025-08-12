import json
import pytest

from bvsim_web import create_app

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
    rv = client.post('/api/teams', json={"name": "WebTestTeam", "template": "basic"})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data.get('created')
    # list
    rv2 = client.get('/api/teams')
    assert rv2.status_code == 200
    names = [t.get('name') for t in rv2.get_json().get('teams', [])]
    assert any('WebTestTeam' in (n or '') for n in names)


def test_simulate_quick(client):
    rv = client.post('/api/simulate', json={"team_a": "WebTestTeam", "team_b": "WebTestTeam", "quick": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert 'summary' in data
    assert data['summary']['team_a_win_rate'] >= 0


def test_simulate_blank_defaults(client):
    # Both team names blank: should auto-use defaults and not 500
    rv = client.post('/api/simulate', json={"team_a": "", "team_b": "", "quick": True})
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True
    assert data['summary']['team_a_win_rate'] >= 0

def test_simulate_one_blank_other_basic(client):
    # Provide only team_a, leave team_b blank -> team_b should be Basic (not Advanced)
    rv = client.post('/api/teams', json={"name": "SoloTeamX", "template": "basic"})
    assert rv.status_code == 200
    rv2 = client.post('/api/simulate', json={"team_a": "team_soloteamx.yaml", "team_b": "", "quick": True})
    assert rv2.status_code == 200, rv2.data
    data = rv2.get_json()
    assert data['parameters'].get('used_defaults') is True
    # Team B should be Basic template name "Team B" (since created basic differs, we just ensure note present or used_defaults)
    assert data['summary']['team_b'] == 'Team B'

def test_skills_blank_defaults(client):
    rv = client.post('/api/skills', json={"quick": True})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['parameters'].get('used_defaults') is True
    assert data['teams']['team'] == 'Team A'
    assert data['teams']['opponent'] == 'Team B'

def test_skills_one_blank_other_basic(client):
    rv = client.post('/api/skills', json={"team": "team_soloteamx.yaml", "quick": True})
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
    rv = client.post('/api/skills', json={"team": "WebTestTeam", "quick": True, "improve": "5%"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'results' in data
