# Contract Test Specifications

## Test Philosophy

Contract tests verify that CLI commands behave exactly as specified in their contracts. These tests must be written FIRST and must FAIL before implementation begins.

## bvsim-core Contract Tests

### simulate-point Command Tests

#### Test: Valid Team Configurations
```python
def test_simulate_point_valid_teams():
    # Arrange
    team_a_file = create_temp_file(VALID_TEAM_A_YAML)
    team_b_file = create_temp_file(VALID_TEAM_B_YAML)
    
    # Act
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--seed", "12345"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Point Result:" in result.stdout
    assert "Serving Team:" in result.stdout
    assert "Winner:" in result.stdout
    assert "Point Type:" in result.stdout
    assert "States:" in result.stdout
```

#### Test: JSON Output Format
```python
def test_simulate_point_json_output():
    # Arrange
    team_a_file = create_temp_file(VALID_TEAM_A_YAML)
    team_b_file = create_temp_file(VALID_TEAM_B_YAML)
    
    # Act
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--format", "json",
        "--seed", "12345"
    ])
    
    # Assert
    assert result.exit_code == 0
    point_data = json.loads(result.stdout)
    assert "serving_team" in point_data
    assert point_data["serving_team"] in ["A", "B"]
    assert "winner" in point_data
    assert point_data["winner"] in ["A", "B"]
    assert "point_type" in point_data
    assert "states" in point_data
    assert isinstance(point_data["states"], list)
    assert len(point_data["states"]) > 0
```

#### Test: Invalid Team Configuration
```python
def test_simulate_point_invalid_team():
    # Arrange
    invalid_team_file = create_temp_file(INVALID_TEAM_YAML)  # Probabilities don't sum to 1.0
    valid_team_file = create_temp_file(VALID_TEAM_A_YAML)
    
    # Act
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", invalid_team_file,
        "--team-b", valid_team_file
    ])
    
    # Assert
    assert result.exit_code == 1
    assert "Invalid team configuration" in result.stderr
```

#### Test: Missing File
```python
def test_simulate_point_missing_file():
    # Arrange
    valid_team_file = create_temp_file(VALID_TEAM_A_YAML)
    
    # Act
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", "nonexistent.yaml",
        "--team-b", valid_team_file
    ])
    
    # Assert
    assert result.exit_code == 2
    assert "File not found" in result.stderr
```

#### Test: Reproducible Results with Seed
```python
def test_simulate_point_reproducible_seed():
    # Arrange
    team_a_file = create_temp_file(VALID_TEAM_A_YAML)
    team_b_file = create_temp_file(VALID_TEAM_B_YAML)
    
    # Act - Run same simulation twice with same seed
    result1 = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--format", "json",
        "--seed", "12345"
    ])
    
    result2 = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--format", "json", 
        "--seed", "12345"
    ])
    
    # Assert
    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.stdout == result2.stdout  # Identical JSON output
```

### validate-team Command Tests

#### Test: Valid Team Configuration
```python
def test_validate_team_valid():
    # Arrange
    team_file = create_temp_file(VALID_TEAM_A_JSON)
    
    # Act
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_file
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Team validation: PASSED" in result.stdout
    assert "All probability distributions valid" in result.stdout
```

#### Test: Invalid Probability Sums
```python
def test_validate_team_invalid_sums():
    # Arrange
    invalid_team = {
        "name": "Invalid Team",
        "serve_probabilities": {
            "ace": 0.1,
            "in_play": 0.8,  # Sum = 0.9, should be 1.0
            "error": 0.0
        }
        # ... other probabilities
    }
    team_file = create_temp_file(json.dumps(invalid_team))
    
    # Act
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_file
    ])
    
    # Assert
    assert result.exit_code == 1
    assert "Team validation: FAILED" in result.stdout
    assert "serve_probabilities sum to 0.90 (expected 1.00)" in result.stdout
```

#### Test: Missing Required Outcomes
```python
def test_validate_team_missing_outcomes():
    # Arrange
    invalid_team = {
        "name": "Incomplete Team",
        "serve_probabilities": {
            "ace": 0.1,
            "in_play": 0.9
            # Missing "error" outcome
        }
        # ... other probabilities
    }
    team_file = create_temp_file(json.dumps(invalid_team))
    
    # Act
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_file
    ])
    
    # Assert
    assert result.exit_code == 1
    assert "missing 'error' outcome" in result.stdout
```

## bvsim-stats Contract Tests

### analyze-results Command Tests

#### Test: Valid Simulation Results
```python
def test_analyze_results_valid():
    # Arrange
    simulation_data = create_simulation_results(1000)  # 1000 points
    results_file = create_temp_file(json.dumps(simulation_data))
    
    # Act
    result = run_command([
        "bvsim-stats", "analyze-results",
        "--simulation", results_file
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Simulation Analysis:" in result.stdout
    assert "Total Points: 1000" in result.stdout
    assert "Team A Wins:" in result.stdout
    assert "Team B Wins:" in result.stdout
    assert "Point Types:" in result.stdout
    assert "Average Point Duration:" in result.stdout
```

#### Test: JSON Output Format
```python
def test_analyze_results_json():
    # Arrange
    simulation_data = create_simulation_results(100)
    results_file = create_temp_file(json.dumps(simulation_data))
    
    # Act
    result = run_command([
        "bvsim-stats", "analyze-results",
        "--simulation", results_file,
        "--format", "json"
    ])
    
    # Assert
    assert result.exit_code == 0
    analysis = json.loads(result.stdout)
    assert "total_points" in analysis
    assert "team_a_wins" in analysis
    assert "team_b_wins" in analysis
    assert "point_types" in analysis
    assert "average_duration" in analysis
```

### sensitivity-analysis Command Tests

#### Test: Parameter Sensitivity Analysis
```python
def test_sensitivity_analysis_valid():
    # Arrange
    team_file = create_temp_file(VALID_TEAM_A_JSON)
    opponent_file = create_temp_file(VALID_TEAM_B_JSON)
    
    # Act
    result = run_command([
        "bvsim-stats", "sensitivity-analysis",
        "--team", team_file,
        "--parameter", "attack_probabilities.excellent_set.kill",
        "--range", "0.7,0.9,0.05",
        "--opponent", opponent_file,
        "--points", "100"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Sensitivity Analysis:" in result.stdout
    assert "Base win rate:" in result.stdout
    assert "Parameter Value | Win Rate | Change" in result.stdout
    assert "Impact Factor:" in result.stdout
```

## bvsim-cli Contract Tests

### create-team Command Tests

#### Test: Basic Team Creation
```python
def test_create_team_basic():
    # Arrange
    output_file = get_temp_filename("team.json")
    
    # Act
    result = run_command([
        "bvsim-cli", "create-team",
        "--name", "Test Team",
        "--output", output_file,
        "--template", "basic"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert os.path.exists(output_file)
    
    with open(output_file) as f:
        team_data = json.load(f)
    assert team_data["name"] == "Test Team"
    assert "serve_probabilities" in team_data
```

### run-simulation Command Tests

#### Test: Large Simulation Run
```python
def test_run_simulation_large():
    # Arrange
    team_a_file = create_temp_file(VALID_TEAM_A_JSON)
    team_b_file = create_temp_file(VALID_TEAM_B_JSON)
    output_file = get_temp_filename("results.json")
    
    # Act
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "1000",
        "--output", output_file,
        "--seed", "12345"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Simulation Complete:" in result.stdout
    assert "Team A Wins:" in result.stdout
    assert "Team B Wins:" in result.stdout
    assert "Results saved to:" in result.stdout
    assert os.path.exists(output_file)
    
    with open(output_file) as f:
        results = json.load(f)
    assert results["total_points"] == 1000
```

#### Test: Progress Display
```python
def test_run_simulation_progress():
    # Arrange
    team_a_file = create_temp_file(VALID_TEAM_A_JSON)
    team_b_file = create_temp_file(VALID_TEAM_B_JSON)
    
    # Act
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "100",
        "--progress"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Progress:" in result.stderr  # Progress goes to stderr
    assert "████" in result.stderr or "100%" in result.stderr
```

### compare-teams Command Tests

#### Test: Team Comparison Matrix
```python
def test_compare_teams_matrix():
    # Arrange
    team_files = [
        create_temp_file(VALID_TEAM_A_JSON),
        create_temp_file(VALID_TEAM_B_JSON),
        create_temp_file(VALID_TEAM_C_JSON)
    ]
    teams_arg = ",".join(team_files)
    
    # Act
    result = run_command([
        "bvsim-cli", "compare-teams",
        "--teams", teams_arg,
        "--points", "100",
        "--matrix"
    ])
    
    # Assert
    assert result.exit_code == 0
    assert "Team Comparison Matrix" in result.stdout
    assert "Overall Rankings:" in result.stdout
    # Should show 3x3 matrix format
    for team_file in team_files:
        team_name = json.loads(open(team_file).read())["name"]
        assert team_name in result.stdout
```

## Standard CLI Tests (All Commands)

### Test: Help Flag
```python
def test_all_commands_help():
    commands = [
        ["bvsim-core", "simulate-point", "--help"],
        ["bvsim-core", "validate-team", "--help"],
        ["bvsim-stats", "analyze-results", "--help"],
        ["bvsim-stats", "sensitivity-analysis", "--help"],
        ["bvsim-cli", "create-team", "--help"],
        ["bvsim-cli", "run-simulation", "--help"],
        ["bvsim-cli", "compare-teams", "--help"]
    ]
    
    for cmd in commands:
        result = run_command(cmd)
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "--help" in result.stdout
```

### Test: Version Flag
```python
def test_all_commands_version():
    commands = [
        ["bvsim-core", "--version"],
        ["bvsim-stats", "--version"],
        ["bvsim-cli", "--version"]
    ]
    
    for cmd in commands:
        result = run_command(cmd)
        assert result.exit_code == 0
        assert "bvsim" in result.stdout.lower()
        # Version format: major.minor.patch
        assert re.match(r'\d+\.\d+\.\d+', result.stdout)
```

## Test Data Fixtures

### Valid Team Configurations
```python
VALID_TEAM_A_YAML = """
name: "Elite Attackers"
serve_probabilities:
  ace: 0.12
  in_play: 0.83
  error: 0.05

receive_probabilities:
  in_play_serve:
    excellent: 0.35
    good: 0.45
    poor: 0.15
    error: 0.05

attack_probabilities:
  excellent_set:
    kill: 0.85
    error: 0.05
    defended: 0.10
  good_set:
    kill: 0.70
    error: 0.10
    defended: 0.20
  poor_set:
    kill: 0.45
    error: 0.25
    defended: 0.30

block_probabilities:
  power_attack:
    stuff: 0.20
    deflection: 0.30
    no_touch: 0.50

dig_probabilities:
  deflected_attack:
    excellent: 0.25
    good: 0.45
    poor: 0.25
    error: 0.05
"""

VALID_TEAM_B_YAML = """
name: "Strong Defense"
serve_probabilities:
  ace: 0.08
  in_play: 0.87
  error: 0.05

receive_probabilities:
  in_play_serve:
    excellent: 0.40
    good: 0.40
    poor: 0.15
    error: 0.05

attack_probabilities:
  excellent_set:
    kill: 0.75
    error: 0.10
    defended: 0.15
  good_set:
    kill: 0.60
    error: 0.15
    defended: 0.25
  poor_set:
    kill: 0.35
    error: 0.30
    defended: 0.35

block_probabilities:
  power_attack:
    stuff: 0.25
    deflection: 0.35
    no_touch: 0.40

dig_probabilities:
  deflected_attack:
    excellent: 0.35
    good: 0.40
    poor: 0.20
    error: 0.05
"""

INVALID_TEAM_YAML = """
name: "Invalid Team"
serve_probabilities:
  ace: 0.5
  in_play: 0.6  # Sum = 1.1, should be 1.0
  error: 0.0
"""
```

## Test Execution Order

1. **Contract tests MUST be written first**
2. **All contract tests MUST fail initially**
3. **Implementation proceeds only after failing tests exist**
4. **Tests MUST pass before feature is considered complete**

## Continuous Integration

- Run all contract tests on every commit
- Ensure reproducible test environments
- Test with multiple Python versions (3.8+)
- Validate YAML team input and JSON result schema compliance
- Performance regression testing for large simulations