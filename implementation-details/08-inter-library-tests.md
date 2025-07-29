# Inter-Library Test Specifications

## Inter-Library Testing Philosophy

Inter-library tests verify the contracts and interactions between the three main libraries (bvsim-core, bvsim-stats, bvsim-cli). These tests focus on the boundaries between libraries and ensure they integrate correctly according to constitutional requirements.

## Library Boundary Definitions

### bvsim-core Library Boundaries
**Exports**:
- `Team` dataclass with validation methods
- `Point` dataclass with state progression
- `simulate_point(team_a, team_b, serving_team, seed)` function
- `validate_team_configuration(team)` function
- CLI commands: `simulate-point`, `validate-team`

**Dependencies**: Python standard library only

### bvsim-stats Library Boundaries  
**Exports**:
- `analyze_simulation_results(simulation_data)` function
- `sensitivity_analysis(base_team, parameter, range, opponent, points)` function
- `compare_teams(teams, points_per_matchup)` function
- CLI commands: `analyze-results`, `sensitivity-analysis`

**Dependencies**: bvsim-core for team validation and point simulation

### bvsim-cli Library Boundaries
**Exports**:
- `create_team_interactive(name, template)` function
- `run_large_simulation(team_a, team_b, points, progress_callback)` function
- CLI commands: `create-team`, `run-simulation`, `compare-teams`

**Dependencies**: bvsim-core for simulation, bvsim-stats for analysis

## Core ↔ Stats Library Contract Tests

### Test: Stats Library Uses Core Simulation Correctly

```python
def test_stats_uses_core_simulation():
    """
    Test that bvsim-stats correctly uses bvsim-core for simulations
    Verifies the contract between stats and core libraries
    """
    # Setup: Create teams using core library
    from bvsim_core import Team, validate_team_configuration
    from bvsim_stats import sensitivity_analysis
    
    base_team_data = {
        "name": "Base Team",
        "serve_probabilities": {"ace": 0.1, "in_play": 0.85, "error": 0.05},
        "attack_probabilities": {
            "excellent_set": {"kill": 0.8, "error": 0.1, "defended": 0.1},
            "good_set": {"kill": 0.6, "error": 0.2, "defended": 0.2}
        }
        # ... other probability matrices
    }
    
    opponent_team_data = {
        "name": "Opponent Team",
        # ... standard opponent configuration
    }
    
    base_team = Team.from_dict(base_team_data)
    opponent_team = Team.from_dict(opponent_team_data)
    
    # Verify teams are valid using core validation
    base_errors = validate_team_configuration(base_team)
    opponent_errors = validate_team_configuration(opponent_team)
    assert len(base_errors) == 0, f"Base team validation failed: {base_errors}"
    assert len(opponent_errors) == 0, f"Opponent team validation failed: {opponent_errors}"
    
    # Test: Stats library uses core simulation correctly
    results = sensitivity_analysis(
        base_team=base_team,
        parameter="attack_probabilities.excellent_set.kill",
        value_range=[0.7, 0.8, 0.9],
        opponent=opponent_team,
        points_per_test=100
    )
    
    # Verify stats library contract compliance
    assert "parameter" in results
    assert "base_win_rate" in results
    assert "results" in results
    assert "impact_factor" in results
    
    # Verify each test used core simulation
    assert len(results["results"]) == 3  # Three test values
    for result in results["results"]:
        assert "parameter_value" in result
        assert "win_rate" in result
        assert "change" in result
        assert 0.0 <= result["win_rate"] <= 1.0  # Valid win rate
    
    # Verify win rates change as expected (higher kill rate → higher win rate)
    win_rates = [r["win_rate"] for r in results["results"]]
    assert win_rates[0] < win_rates[1] < win_rates[2], "Win rates should increase with kill probability"
```

### Test: Core Library Data Integrity in Stats

```python
def test_core_data_integrity_in_stats():
    """
    Test that data passed from core to stats maintains integrity
    Verifies no data corruption at library boundaries
    """
    from bvsim_core import Team, simulate_point
    from bvsim_stats import analyze_simulation_results
    
    # Setup: Create teams and simulate points using core
    team_a = Team.from_dict(create_standard_team_config("Team A"))
    team_b = Team.from_dict(create_standard_team_config("Team B"))
    
    # Generate simulation data using core library
    simulation_points = []
    for i in range(100):
        point = simulate_point(team_a, team_b, serving_team="A", seed=1000+i)
        simulation_points.append({
            "winner": point.winner,
            "point_type": point.point_type,
            "states": [{"team": s.team, "action": s.action, "quality": s.quality} for s in point.states],
            "duration": len(point.states)
        })
    
    simulation_data = {
        "team_a": team_a.to_dict(),
        "team_b": team_b.to_dict(),
        "points": simulation_points,
        "total_points": len(simulation_points)
    }
    
    # Test: Stats library processes core data correctly
    analysis = analyze_simulation_results(simulation_data)
    
    # Verify data integrity preservation
    assert analysis["total_points"] == 100
    assert analysis["team_a_wins"] + analysis["team_b_wins"] == 100
    
    # Verify point type analysis matches source data
    source_aces = sum(1 for p in simulation_points if p["point_type"] == "ace")
    source_kills = sum(1 for p in simulation_points if p["point_type"] == "kill")
    source_errors = sum(1 for p in simulation_points if p["point_type"] == "error")
    
    assert analysis["point_types"]["aces"] == source_aces
    assert analysis["point_types"]["kills"] == source_kills
    assert analysis["point_types"]["errors"] == source_errors
    
    # Verify average duration calculation
    source_avg_duration = sum(p["duration"] for p in simulation_points) / len(simulation_points)
    assert abs(analysis["average_duration"] - source_avg_duration) < 0.01
```

## Core ↔ CLI Library Contract Tests

### Test: CLI Library Uses Core Validation

```python
def test_cli_uses_core_validation():
    """
    Test that bvsim-cli properly uses bvsim-core validation functions
    Verifies validation contract between CLI and core libraries
    """
    from bvsim_core import validate_team_configuration, Team
    from bvsim_cli import create_team_interactive, run_large_simulation
    
    # Test: CLI creates teams that pass core validation
    team_config = create_team_interactive(
        name="CLI Test Team",
        template="basic",
        interactive=False  # Use defaults for testing
    )
    
    # Convert CLI output to core Team object
    team = Team.from_dict(team_config)
    
    # Verify CLI-created team passes core validation
    validation_errors = validate_team_configuration(team)
    assert len(validation_errors) == 0, f"CLI-created team failed core validation: {validation_errors}"
    
    # Test: CLI properly handles validation failures
    invalid_team_config = {
        "name": "Invalid Team",
        "serve_probabilities": {"ace": 0.5, "in_play": 0.6, "error": 0.1}  # Sum = 1.2, invalid
    }
    
    try:
        invalid_team = Team.from_dict(invalid_team_config)
        errors = validate_team_configuration(invalid_team)
        assert len(errors) > 0, "Core validation should catch invalid probability sums"
        
        # CLI should handle this validation error gracefully
        # (This would be tested through CLI interface in integration tests)
        
    except Exception as e:
        # CLI should handle validation exceptions properly
        assert "probability" in str(e).lower() or "validation" in str(e).lower()
```

### Test: CLI Simulation Uses Core Engine

```python
def test_cli_simulation_uses_core_engine():
    """
    Test that CLI simulation functions use core simulation engine correctly
    Verifies simulation contract between libraries
    """
    from bvsim_core import Team, simulate_point
    from bvsim_cli import run_large_simulation
    
    # Setup: Create teams
    team_a_config = create_standard_team_config("Team A")
    team_b_config = create_standard_team_config("Team B")
    
    team_a = Team.from_dict(team_a_config)
    team_b = Team.from_dict(team_b_config)
    
    # Test: CLI simulation produces same results as direct core usage
    seed = 42
    points_to_test = 50
    
    # Run simulation through CLI library
    cli_results = run_large_simulation(
        team_a=team_a,
        team_b=team_b,
        points=points_to_test,
        seed=seed,
        progress_callback=None
    )
    
    # Run equivalent simulation directly with core
    direct_results = []
    for i in range(points_to_test):
        point = simulate_point(team_a, team_b, serving_team="A", seed=seed+i)
        direct_results.append(point)
    
    # Verify CLI and direct results match
    assert len(cli_results["points"]) == points_to_test
    assert len(direct_results) == points_to_test
    
    # Verify same winners (deterministic with seed)
    cli_winners = [p["winner"] for p in cli_results["points"]]
    direct_winners = [p.winner for p in direct_results]
    assert cli_winners == direct_winners, "CLI and direct simulation should produce identical results"
    
    # Verify aggregated statistics match
    cli_team_a_wins = sum(1 for w in cli_winners if w == "A")
    direct_team_a_wins = sum(1 for w in direct_winners if w == "A")
    assert cli_team_a_wins == direct_team_a_wins
    assert cli_results["team_a_score"] == cli_team_a_wins
```

## CLI ↔ Stats Library Contract Tests

### Test: CLI Uses Stats for Analysis

```python
def test_cli_uses_stats_for_analysis():
    """
    Test that bvsim-cli uses bvsim-stats for analysis functions
    Verifies analysis contract between CLI and stats libraries
    """
    from bvsim_core import Team
    from bvsim_stats import compare_teams, sensitivity_analysis
    from bvsim_cli import run_team_comparison, run_sensitivity_analysis
    
    # Setup: Create test teams
    teams_data = [
        create_standard_team_config("Team A"),
        create_standard_team_config("Team B"),
        create_standard_team_config("Team C")
    ]
    
    teams = [Team.from_dict(config) for config in teams_data]
    
    # Test: CLI team comparison uses stats library
    cli_comparison = run_team_comparison(
        teams=teams,
        points_per_matchup=100
    )
    
    # Run same comparison directly with stats library  
    direct_comparison = compare_teams(teams, points_per_matchup=100)
    
    # Verify CLI delegates to stats library correctly
    assert len(cli_comparison["rankings"]) == 3
    assert len(direct_comparison["rankings"]) == 3
    
    # Results should be equivalent (allowing for different presentation formats)
    cli_team_names = [r["team_name"] for r in cli_comparison["rankings"]]
    direct_team_names = [r["team_name"] for r in direct_comparison["rankings"]]
    assert set(cli_team_names) == set(direct_team_names)
    
    # Test: CLI sensitivity analysis uses stats library
    base_team = teams[0]
    
    cli_sensitivity = run_sensitivity_analysis(
        base_team=base_team,
        parameter="attack_probabilities.excellent_set.kill",
        value_range=[0.7, 0.8, 0.9],
        opponent=teams[1],
        points_per_test=50
    )
    
    direct_sensitivity = sensitivity_analysis(
        base_team=base_team,
        parameter="attack_probabilities.excellent_set.kill", 
        value_range=[0.7, 0.8, 0.9],
        opponent=teams[1],
        points_per_test=50
    )
    
    # Verify CLI uses stats library correctly
    assert cli_sensitivity["parameter"] == direct_sensitivity["parameter"]
    assert len(cli_sensitivity["results"]) == len(direct_sensitivity["results"])
    assert cli_sensitivity["impact_factor"] == direct_sensitivity["impact_factor"]
```

## Cross-Library Data Flow Tests

### Test: Complete Data Flow Through All Libraries

```python
def test_complete_data_flow():
    """
    Test data flow through complete pipeline: CLI → Core → Stats → CLI
    Verifies end-to-end library integration
    """
    from bvsim_cli import create_team_interactive, run_large_simulation
    from bvsim_stats import analyze_simulation_results
    from bvsim_core import Team, validate_team_configuration
    
    # Step 1: CLI creates team configuration
    team_a_config = create_team_interactive("Flow Test Team A", "basic", interactive=False)
    team_b_config = create_team_interactive("Flow Test Team B", "basic", interactive=False)
    
    # Step 2: Core validates team configurations
    team_a = Team.from_dict(team_a_config)
    team_b = Team.from_dict(team_b_config)
    
    errors_a = validate_team_configuration(team_a)
    errors_b = validate_team_configuration(team_b)
    assert len(errors_a) == 0, f"Team A validation failed: {errors_a}"
    assert len(errors_b) == 0, f"Team B validation failed: {errors_b}"
    
    # Step 3: CLI runs simulation using Core
    simulation_results = run_large_simulation(
        team_a=team_a,
        team_b=team_b,
        points=200,
        seed=123
    )
    
    # Step 4: Stats analyzes results
    analysis = analyze_simulation_results(simulation_results)
    
    # Step 5: Verify complete data integrity through pipeline
    assert analysis["total_points"] == 200
    assert analysis["team_a_wins"] + analysis["team_b_wins"] == 200
    assert analysis["team_a_wins"] == simulation_results["team_a_score"]
    assert analysis["team_b_wins"] == simulation_results["team_b_score"]
    
    # Verify all libraries contributed correctly
    assert "point_types" in analysis  # Stats library analysis
    assert "average_duration" in analysis  # Stats library calculation
    assert len(simulation_results["points"]) == 200  # Core library simulation
    assert team_a.name == "Flow Test Team A"  # CLI library team creation
```

### Test: Error Propagation Across Libraries

```python
def test_error_propagation_across_libraries():
    """
    Test that errors are properly propagated and handled across library boundaries
    """
    from bvsim_cli import run_large_simulation
    from bvsim_core import Team
    from bvsim_stats import analyze_simulation_results
    
    # Test: Invalid team configuration error propagation
    invalid_config = {
        "name": "Invalid Team",
        "serve_probabilities": {"ace": 1.5, "in_play": 0.5, "error": -0.2}  # Invalid values
    }
    
    try:
        invalid_team = Team.from_dict(invalid_config)
        assert False, "Core library should reject invalid team configuration"
    except Exception as core_error:
        # Core library properly rejects invalid data
        assert "probability" in str(core_error).lower()
    
    # Test: CLI handles core validation errors
    valid_team = Team.from_dict(create_standard_team_config("Valid Team"))
    
    try:
        # This should trigger core validation and fail
        simulation_results = run_large_simulation(
            team_a=Team.from_dict(invalid_config),  # This will fail
            team_b=valid_team,
            points=10
        )
        assert False, "CLI should propagate core validation errors"
    except Exception as cli_error:
        # CLI properly propagates core errors
        assert "invalid" in str(cli_error).lower() or "validation" in str(cli_error).lower()
    
    # Test: Stats handles invalid simulation data
    invalid_simulation_data = {
        "points": "invalid_data_type",  # Should be list
        "total_points": -1  # Invalid value
    }
    
    try:
        analysis = analyze_simulation_results(invalid_simulation_data)
        assert False, "Stats library should reject invalid simulation data"
    except Exception as stats_error:
        # Stats library properly validates input data
        assert "invalid" in str(stats_error).lower() or "data" in str(stats_error).lower()
```

## Contract Validation Tests

### Test: Library Interface Contracts

```python
def test_library_interface_contracts():
    """
    Test that all libraries expose their contracted interfaces correctly
    """
    # Test: bvsim-core exports required functions
    from bvsim_core import Team, Point, simulate_point, validate_team_configuration
    
    assert callable(simulate_point), "simulate_point should be callable"
    assert callable(validate_team_configuration), "validate_team_configuration should be callable"
    assert hasattr(Team, 'from_dict'), "Team should have from_dict class method"
    assert hasattr(Team, 'to_dict'), "Team should have to_dict method"
    assert hasattr(Point, 'add_state'), "Point should have add_state method"
    
    # Test: bvsim-stats exports required functions  
    from bvsim_stats import analyze_simulation_results, sensitivity_analysis, compare_teams
    
    assert callable(analyze_simulation_results), "analyze_simulation_results should be callable"
    assert callable(sensitivity_analysis), "sensitivity_analysis should be callable"
    assert callable(compare_teams), "compare_teams should be callable"
    
    # Test: bvsim-cli exports required functions
    from bvsim_cli import create_team_interactive, run_large_simulation
    
    assert callable(create_team_interactive), "create_team_interactive should be callable"
    assert callable(run_large_simulation), "run_large_simulation should be callable"
```

### Test: Library Version Compatibility

```python
def test_library_version_compatibility():
    """
    Test that libraries are compatible with each other's versions
    """
    import bvsim_core
    import bvsim_stats  
    import bvsim_cli
    
    # All libraries should expose version information
    assert hasattr(bvsim_core, '__version__'), "bvsim-core should have version"
    assert hasattr(bvsim_stats, '__version__'), "bvsim-stats should have version"
    assert hasattr(bvsim_cli, '__version__'), "bvsim-cli should have version"
    
    # Versions should follow semantic versioning
    import re
    version_pattern = r'^\d+\.\d+\.\d+$'
    
    assert re.match(version_pattern, bvsim_core.__version__), f"Invalid core version: {bvsim_core.__version__}"
    assert re.match(version_pattern, bvsim_stats.__version__), f"Invalid stats version: {bvsim_stats.__version__}"
    assert re.match(version_pattern, bvsim_cli.__version__), f"Invalid cli version: {bvsim_cli.__version__}"
```

## Performance Boundary Tests

### Test: Inter-Library Call Performance

```python
def test_inter_library_call_performance():
    """
    Test that inter-library calls don't introduce significant performance overhead
    """
    import time
    from bvsim_core import Team, simulate_point
    from bvsim_cli import run_large_simulation
    
    # Setup test teams
    team_a = Team.from_dict(create_standard_team_config("Team A"))
    team_b = Team.from_dict(create_standard_team_config("Team B"))
    
    # Test: Direct core library performance
    start_time = time.time()
    direct_points = []
    for i in range(1000):
        point = simulate_point(team_a, team_b, serving_team="A", seed=i)
        direct_points.append(point)
    direct_time = time.time() - start_time
    
    # Test: CLI library using core (with overhead)
    start_time = time.time()
    cli_results = run_large_simulation(team_a, team_b, points=1000, seed=0)
    cli_time = time.time() - start_time
    
    # CLI overhead should be minimal (< 50% slower than direct)
    overhead_ratio = cli_time / direct_time
    assert overhead_ratio < 1.5, f"CLI overhead too high: {overhead_ratio:.2f}x slower than direct"
    
    # Both should produce same number of results
    assert len(direct_points) == 1000
    assert len(cli_results["points"]) == 1000
```

## Inter-Library Test Execution

### Test Isolation Requirements
- Each test should use fresh library imports
- No shared state between tests
- Independent test data for each library interaction
- Clean up any temporary files or state

### Test Execution Order
1. **Library Interface Contract Tests** - Verify basic interfaces exist
2. **Data Flow Tests** - Test data passing between libraries  
3. **Error Propagation Tests** - Test error handling across boundaries
4. **Performance Boundary Tests** - Test performance characteristics
5. **Version Compatibility Tests** - Test library version alignment

### Continuous Integration
- Run inter-library tests after unit tests pass
- Test with different library combinations
- Verify library independence (no circular dependencies)
- Monitor inter-library call performance
- Validate constitutional compliance (library-first principle)

## Helper Functions for Inter-Library Tests

```python
def create_standard_team_config(name):
    """Create a standard team configuration for testing"""
    return {
        "name": name,
        "serve_probabilities": {"ace": 0.1, "in_play": 0.85, "error": 0.05},
        "receive_probabilities": {
            "in_play_serve": {"excellent": 0.3, "good": 0.5, "poor": 0.15, "error": 0.05}
        },
        "attack_probabilities": {
            "excellent_set": {"kill": 0.8, "error": 0.1, "defended": 0.1},
            "good_set": {"kill": 0.6, "error": 0.2, "defended": 0.2},
            "poor_set": {"kill": 0.4, "error": 0.3, "defended": 0.3}
        },
        "block_probabilities": {
            "power_attack": {"stuff": 0.2, "deflection": 0.3, "no_touch": 0.5}
        },
        "dig_probabilities": {
            "deflected_attack": {"excellent": 0.3, "good": 0.4, "poor": 0.25, "error": 0.05}
        }
    }
```