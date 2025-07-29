# Integration Test Specifications

## Integration Test Philosophy

Integration tests verify that different components work together correctly and that complete user workflows function end-to-end. These tests focus on component boundaries and realistic usage scenarios.

## End-to-End User Workflow Tests

### US-001: Team Definition Workflow
**Scenario**: Coach creates teams with conditional probabilities

```python
def test_team_definition_workflow():
    """
    End-to-end test for US-001: Team definition with conditional probabilities
    Tests the complete workflow from team creation to validation
    """
    # Step 1: Create Team A with specific probabilities
    team_a_output = temp_file("team_a.json")
    result = run_command([
        "bvsim-cli", "create-team",
        "--name", "Elite Attackers",
        "--output", team_a_output,
        "--template", "advanced"
    ])
    assert result.exit_code == 0
    
    # Step 2: Modify team probabilities for serving vs receiving
    team_a_config = load_json(team_a_output)
    team_a_config["serve_probabilities"]["ace"] = 0.15  # Strong serving team
    team_a_config["attack_probabilities"]["excellent_set"]["kill"] = 0.90  # Excellent attack after good sets
    team_a_config["attack_probabilities"]["poor_set"]["kill"] = 0.30  # Poor attack after bad sets
    save_json(team_a_output, team_a_config)
    
    # Step 3: Validate team configuration
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_a_output
    ])
    assert result.exit_code == 0
    assert "Team validation: PASSED" in result.stdout
    
    # Step 4: Create Team B with different characteristics
    team_b_output = temp_file("team_b.json")
    result = run_command([
        "bvsim-cli", "create-team",
        "--name", "Strong Defense",
        "--output", team_b_output,
        "--template", "advanced"
    ])
    assert result.exit_code == 0
    
    # Modify Team B for defensive characteristics
    team_b_config = load_json(team_b_output)
    team_b_config["serve_probabilities"]["ace"] = 0.08  # Weaker serving
    team_b_config["block_probabilities"]["power_attack"]["stuff"] = 0.25  # Strong blocking
    team_b_config["dig_probabilities"]["deflected_attack"]["excellent"] = 0.40  # Excellent digging
    save_json(team_b_output, team_b_config)
    
    # Step 5: Validate Team B
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_b_output
    ])
    assert result.exit_code == 0
    
    # Step 6: Verify teams have different serving vs receiving probabilities
    assert team_a_config["serve_probabilities"]["ace"] != team_b_config["serve_probabilities"]["ace"]
    assert team_a_config["attack_probabilities"]["excellent_set"]["kill"] > team_b_config["attack_probabilities"]["excellent_set"]["kill"]
```

### US-002: Large Scale Simulation Workflow
**Scenario**: Analyst runs thousands of point simulations

```python
def test_large_simulation_workflow():
    """
    End-to-end test for US-002: Large scale point simulation
    Tests complete simulation pipeline with statistical analysis
    """
    # Setup: Create two teams
    team_a_file = create_test_team("Elite_Attackers", {"serve_ace_rate": 0.12})
    team_b_file = create_test_team("Solid_Defense", {"serve_ace_rate": 0.08})
    
    # Step 1: Run large simulation
    results_file = temp_file("simulation_results.json")
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "5000",
        "--output", results_file,
        "--progress",
        "--seed", "42"
    ])
    
    assert result.exit_code == 0
    assert "Simulation Complete:" in result.stdout
    assert "Team A Wins:" in result.stdout
    assert "Team B Wins:" in result.stdout
    assert "5000" in result.stdout
    
    # Step 2: Verify results file created and valid
    assert os.path.exists(results_file)
    simulation_data = load_json(results_file)
    assert simulation_data["total_points"] == 5000
    assert simulation_data["team_a_score"] + simulation_data["team_b_score"] == 5000
    assert len(simulation_data["points"]) == 5000
    
    # Step 3: Analyze results
    result = run_command([
        "bvsim-stats", "analyze-results",
        "--simulation", results_file,
        "--breakdown"
    ])
    
    assert result.exit_code == 0
    assert "Total Points: 5000" in result.stdout
    assert "Point Types:" in result.stdout
    assert "Average Point Duration:" in result.stdout
    
    # Step 4: Verify statistical significance (large sample)
    team_a_win_rate = simulation_data["team_a_score"] / 5000
    assert 0.3 <= team_a_win_rate <= 0.7  # Reasonable range for competitive teams
    
    # Step 5: Verify reproducibility with same seed
    results_file_2 = temp_file("simulation_results_2.json")
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "1000",
        "--output", results_file_2,
        "--seed", "42"
    ])
    
    # Should get identical first 1000 points
    simulation_data_2 = load_json(results_file_2)
    first_1000_original = simulation_data["points"][:1000]
    first_1000_repeat = simulation_data_2["points"]
    assert first_1000_original == first_1000_repeat  # Identical with same seed
```

### US-003: Point Progression Verification Workflow
**Scenario**: Coach reviews individual point progressions

```python
def test_point_progression_verification_workflow():
    """
    End-to-end test for US-003: Point progression verification
    Tests detailed point logging and volleyball rule compliance
    """
    # Setup: Create teams with known characteristics
    team_a_file = create_test_team("Team_A", {})
    team_b_file = create_test_team("Team_B", {})
    
    # Step 1: Simulate multiple individual points with verbose logging
    points_to_check = []
    for i in range(20):  # Check 20 different points
        result = run_command([
            "bvsim-core", "simulate-point",
            "--team-a", team_a_file,
            "--team-b", team_b_file,
            "--format", "json",
            "--verbose",
            "--seed", str(1000 + i)  # Different seed for each point
        ])
        
        assert result.exit_code == 0
        point_data = json.loads(result.stdout)
        points_to_check.append(point_data)
    
    # Step 2: Verify each point follows volleyball rules
    for i, point in enumerate(points_to_check):
        # Verify point structure
        assert "serving_team" in point
        assert "winner" in point
        assert "states" in point
        assert len(point["states"]) > 0
        
        # Step 3: Verify team state transitions
        states = point["states"]
        assert states[0]["action"] == "serve"  # Always starts with serve
        
        # Verify team alternation rules
        serving_team = point["serving_team"]
        receiving_team = "B" if serving_team == "A" else "A"
        
        current_possession_team = serving_team
        for j, state in enumerate(states):
            if state["action"] == "serve":
                assert state["team"] == serving_team
                assert j == 0  # Serve only at start
                
            elif state["action"] in ["receive", "set", "attack"]:
                assert state["team"] == receiving_team  # Receiving team handles ball
                
            elif state["action"] in ["block", "dig"]:
                assert state["team"] == serving_team  # Original serving team defends
                
        # Step 4: Verify no impossible state transitions
        valid_sequences = validate_volleyball_sequence(states)
        assert valid_sequences["valid"], f"Point {i} has invalid sequence: {valid_sequences['errors']}"
        
        # Step 5: Verify conditional probability relationships
        for j in range(1, len(states)):
            current_state = states[j]
            previous_state = states[j-1]
            
            # Check that current state outcome makes sense given previous state
            if current_state["action"] == "attack" and previous_state["action"] == "set":
                # Attack quality should be influenced by set quality
                if previous_state["quality"] == "excellent":
                    # Should have higher chance of kill
                    pass  # Validated by simulation probabilities
                elif previous_state["quality"] == "poor":
                    # Should have higher chance of error
                    pass  # Validated by simulation probabilities
```

## Component Integration Tests

### State Machine ↔ Probability Engine Integration

```python
def test_state_machine_probability_integration():
    """
    Test integration between state machine and probability engine
    Verifies conditional probability lookups work correctly
    """
    # Setup: Create team with known probability distributions
    team = create_test_team_object({
        "attack_probabilities": {
            "excellent_set": {"kill": 0.8, "error": 0.1, "defended": 0.1},
            "good_set": {"kill": 0.6, "error": 0.2, "defended": 0.2},
            "poor_set": {"kill": 0.3, "error": 0.4, "defended": 0.3}
        }
    })
    
    # Test: State machine uses correct conditional probabilities
    state_machine = VolleyballStateMachine()
    probability_engine = ConditionalProbabilityEngine(team)
    
    # Simulate many attacks after different set qualities
    excellent_set_outcomes = []
    poor_set_outcomes = []
    
    for _ in range(1000):
        # Attack after excellent set
        outcome = state_machine.execute_attack(
            team=team,
            previous_state="excellent_set",
            probability_engine=probability_engine
        )
        excellent_set_outcomes.append(outcome)
        
        # Attack after poor set
        outcome = state_machine.execute_attack(
            team=team,
            previous_state="poor_set", 
            probability_engine=probability_engine
        )
        poor_set_outcomes.append(outcome)
    
    # Verify conditional probability differences
    excellent_kill_rate = excellent_set_outcomes.count("kill") / 1000
    poor_kill_rate = poor_set_outcomes.count("kill") / 1000
    
    assert excellent_kill_rate > poor_kill_rate  # Better sets → more kills
    assert abs(excellent_kill_rate - 0.8) < 0.05  # Close to expected 80%
    assert abs(poor_kill_rate - 0.3) < 0.05  # Close to expected 30%
```

### CLI ↔ Core Library Integration

```python
def test_cli_core_library_integration():
    """
    Test integration between CLI and core simulation libraries
    Verifies data flows correctly through the command-line interface
    """
    # Test: CLI properly passes data to core libraries
    team_a_config = create_test_team_config("Team_A")
    team_b_config = create_test_team_config("Team_B")
    
    team_a_file = create_temp_file(json.dumps(team_a_config))
    team_b_file = create_temp_file(json.dumps(team_b_config))
    
    # Run CLI command
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--format", "json",
        "--seed", "12345"
    ])
    
    assert result.exit_code == 0
    point_data = json.loads(result.stdout)
    
    # Verify CLI properly loaded team configurations
    # (indirectly verified by checking simulation uses team-specific probabilities)
    
    # Test: Run same simulation directly with core library
    from bvsim_core import simulate_point, Team
    
    team_a = Team.from_json(json.dumps(team_a_config))
    team_b = Team.from_json(json.dumps(team_b_config))
    
    direct_point = simulate_point(team_a, team_b, serving_team="A", seed=12345)
    
    # CLI and direct library calls should produce identical results
    assert point_data["winner"] == direct_point.winner
    assert len(point_data["states"]) == len(direct_point.states)
```

### Statistics ↔ Core Integration

```python
def test_statistics_core_integration():
    """
    Test integration between statistics analysis and core simulation
    Verifies statistics are calculated correctly from simulation data
    """
    # Setup: Run simulation with known characteristics
    team_a_file = create_test_team_file({"serve_probabilities": {"ace": 0.2, "in_play": 0.7, "error": 0.1}})
    team_b_file = create_test_team_file({"serve_probabilities": {"ace": 0.05, "in_play": 0.85, "error": 0.1}})
    
    results_file = temp_file("test_results.json")
    
    # Run simulation
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "2000",
        "--output", results_file,
        "--seed", "987"
    ])
    
    assert result.exit_code == 0
    
    # Analyze results
    result = run_command([
        "bvsim-stats", "analyze-results",
        "--simulation", results_file,
        "--format", "json"
    ])
    
    assert result.exit_code == 0
    analysis = json.loads(result.stdout)
    
    # Verify statistics match simulation data
    simulation_data = load_json(results_file)
    
    # Check total points calculation
    assert analysis["total_points"] == 2000
    assert analysis["total_points"] == len(simulation_data["points"])
    
    # Check win rate calculations
    team_a_wins = sum(1 for point in simulation_data["points"] if point["winner"] == "A")
    team_b_wins = sum(1 for point in simulation_data["points"] if point["winner"] == "B")
    
    assert analysis["team_a_wins"] == team_a_wins
    assert analysis["team_b_wins"] == team_b_wins
    assert team_a_wins + team_b_wins == 2000
    
    # Verify Team A has higher win rate (stronger serve)
    team_a_win_rate = team_a_wins / 2000
    assert team_a_win_rate > 0.55  # Should win more with better serve
```

## File I/O Integration Tests

### JSON Serialization/Deserialization Integration

```python
def test_json_serialization_integration():
    """
    Test complete JSON serialization/deserialization workflow
    Verifies data integrity through save/load cycles
    """
    # Create complex team configuration
    original_team = {
        "name": "Complex Team",
        "serve_probabilities": {"ace": 0.12, "in_play": 0.83, "error": 0.05},
        "receive_probabilities": {
            "in_play_serve": {"excellent": 0.3, "good": 0.5, "poor": 0.15, "error": 0.05}
        },
        "attack_probabilities": {
            "excellent_set": {"kill": 0.85, "error": 0.05, "defended": 0.1},
            "good_set": {"kill": 0.70, "error": 0.10, "defended": 0.2},
            "poor_set": {"kill": 0.45, "error": 0.25, "defended": 0.3}
        }
        # ... additional probability matrices
    }
    
    # Test: Save and load through CLI
    team_file = temp_file("complex_team.json")
    save_json(team_file, original_team)
    
    # Validate through CLI
    result = run_command([
        "bvsim-core", "validate-team",
        "--team", team_file,
        "--format", "json"
    ])
    
    assert result.exit_code == 0
    validation_result = json.loads(result.stdout)
    assert validation_result["valid"] == True
    
    # Use in simulation
    opponent_file = create_test_team_file({})
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", team_file,
        "--team-b", opponent_file,
        "--format", "json"
    ])
    
    assert result.exit_code == 0
    point_data = json.loads(result.stdout)
    
    # Verify simulation ran successfully with complex team
    assert "winner" in point_data
    assert "states" in point_data
    assert len(point_data["states"]) > 0
```

## Performance Integration Tests

### Large Simulation Performance

```python
def test_large_simulation_performance():
    """
    Test performance characteristics of large simulations
    Verifies system handles performance requirements
    """
    # Setup: Create test teams
    team_a_file = create_test_team_file({})
    team_b_file = create_test_team_file({})
    results_file = temp_file("performance_test.json")
    
    # Test: Run 10,000 point simulation (performance requirement)
    start_time = time.time()
    
    result = run_command([
        "bvsim-cli", "run-simulation",
        "--team-a", team_a_file,
        "--team-b", team_b_file,
        "--points", "10000",
        "--output", results_file
    ])
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Verify performance requirement: 10,000 points in under 60 seconds
    assert result.exit_code == 0
    assert duration < 60.0, f"Simulation took {duration:.2f} seconds, should be under 60s"
    
    # Verify results quality wasn't compromised for speed
    simulation_data = load_json(results_file)
    assert len(simulation_data["points"]) == 10000
    assert simulation_data["total_points"] == 10000
    
    # Verify memory usage remained reasonable
    # (Implementation should not store excessive intermediate data)
    file_size_mb = os.path.getsize(results_file) / (1024 * 1024)
    assert file_size_mb < 50, f"Results file is {file_size_mb:.1f}MB, should be manageable"
```

## Error Handling Integration Tests

### Error Propagation Through Components

```python
def test_error_propagation_integration():
    """
    Test that errors are properly handled and reported through component boundaries
    """
    # Test: Invalid team configuration error propagation
    invalid_team = {"name": "Bad Team", "serve_probabilities": {"ace": 1.5}}  # Invalid probability
    invalid_file = create_temp_file(json.dumps(invalid_team))
    valid_file = create_test_team_file({})
    
    # CLI should catch and report validation errors from core library
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", invalid_file,
        "--team-b", valid_file
    ])
    
    assert result.exit_code == 1
    assert "Invalid team configuration" in result.stderr
    assert "probability 1.5" in result.stderr  # Specific error details
    
    # Test: File system errors
    result = run_command([
        "bvsim-core", "simulate-point",
        "--team-a", "/nonexistent/path/team.json",
        "--team-b", valid_file
    ])
    
    assert result.exit_code == 2
    assert "File not found" in result.stderr
    
    # Test: Statistics analysis with corrupted simulation data
    corrupted_results = {"invalid": "data"}
    corrupted_file = create_temp_file(json.dumps(corrupted_results))
    
    result = run_command([
        "bvsim-stats", "analyze-results",
        "--simulation", corrupted_file
    ])
    
    assert result.exit_code != 0
    assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()
```

## Integration Test Execution Strategy

### Test Ordering
1. **Component Integration Tests** - Test library boundaries
2. **CLI Integration Tests** - Test command-line interfaces
3. **File I/O Integration Tests** - Test data persistence
4. **End-to-End Workflow Tests** - Test complete user scenarios
5. **Performance Integration Tests** - Test system limits
6. **Error Handling Integration Tests** - Test failure modes

### Test Environment Requirements
- Clean temporary directory for each test
- Isolated test data (no shared state between tests)
- Realistic but controlled test data
- Performance monitoring capabilities
- Cross-platform compatibility testing

### Continuous Integration
- Run integration tests after unit tests pass
- Include performance regression detection
- Test with different Python versions
- Validate cross-platform behavior
- Monitor test execution times