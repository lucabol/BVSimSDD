# Manual Testing Guide: BVSim - Beach Volleyball Point Simulator

## Overview

This manual testing guide provides step-by-step validation procedures for each user story in the BVSim feature specification. Follow these procedures to verify the implementation meets all requirements.

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Terminal/command line access
- Text editor for viewing JSON files

### Build and Setup Instructions

1. **Clone and Navigate to Project**
   ```bash
   cd /path/to/BVSim/project
   ```

2. **Install Dependencies** (if any are added during implementation)
   ```bash
   # Currently using Python standard library only
   python --version  # Verify Python 3.8+
   ```

3. **Build the Project**
   ```bash
   # Set up Python path (adjust paths as needed)
   export PYTHONPATH="${PYTHONPATH}:./src"
   ```

4. **Verify Installation**
   ```bash
   python -m bvsim_core --version
   python -m bvsim_stats --version  
   python -m bvsim_cli --version
   ```

Expected output: Version numbers (e.g., "1.0.0") for each library

## User Story Validation

### US-001: Team Definition with Conditional Probabilities

**Story**: As a beach volleyball coach, I want to define two teams with conditional skill probabilities for both serving and receiving team states so that I can model realistic team matchups.

#### Test Setup
1. Create a temporary directory for test files:
   ```bash
   mkdir -p ~/bvsim_test
   cd ~/bvsim_test
   ```

#### Step-by-Step Validation

**Step 1: Create Team A with Strong Attacking**
```bash
python -m bvsim_cli create-team --name "Elite Attackers" --output team_a.yaml --template advanced
```

**Expected Result**: 
- File `team_a.yaml` is created
- No error messages

**Step 2: Verify Team A Configuration**
```bash
cat team_a.yaml
```

**Expected Result**: YAML file contains:
- `name: "Elite Attackers"`
- `serve_probabilities:` section with ace, in_play, error rates
- `receive_probabilities:` section with conditional probabilities based on serve quality
- `attack_probabilities:` section with different success rates for excellent_set vs poor_set
- All probability values between 0 and 1
- Each probability distribution sums to 1.0

**Step 3: Modify Team A for Conditional Probability Testing**
Edit `team_a.yaml` to set specific conditional probabilities:
```yaml
name: "Elite Attackers"
serve_probabilities:
  ace: 0.15
  in_play: 0.80
  error: 0.05

attack_probabilities:
  excellent_set:
    kill: 0.90
    error: 0.05
    defended: 0.05
  good_set:
    kill: 0.70
    error: 0.10
    defended: 0.20
  poor_set:
    kill: 0.40
    error: 0.30
    defended: 0.30
```

**Step 4: Validate Team A Configuration**
```bash
python -m bvsim_core validate-team --team team_a.yaml
```

**Expected Result**:
- Exit code: 0
- Output: "Team validation: PASSED"
- Output: "All probability distributions valid"

**Step 5: Create Team B with Different Characteristics**
```bash
python -m bvsim_cli create-team --name "Strong Defense" --output team_b.yaml --template advanced
```

**Step 6: Modify Team B for Defensive Characteristics**
Edit `team_b.yaml`:
```yaml
name: "Strong Defense"
serve_probabilities:
  ace: 0.08
  in_play: 0.87
  error: 0.05

block_probabilities:
  power_attack:
    stuff: 0.25
    deflection: 0.35
    no_touch: 0.40

dig_probabilities:
  deflected_attack:
    excellent: 0.40
    good: 0.40
    poor: 0.15
    error: 0.05
```

**Step 7: Validate Team B Configuration**
```bash
python -m bvsim_core validate-team --team team_b.yaml
```

**Expected Result**: Team validation passes

**Step 8: Test Invalid Probability Values**
Create invalid team configuration:
```bash
cat > invalid_team.yaml << EOF
name: "Invalid Team"
serve_probabilities:
  ace: 0.5
  in_play: 0.6  # Sum = 1.1, should be 1.0
  error: 0.1
EOF
```

```bash
python -m bvsim_core validate-team --team invalid_team.yaml
```

**Expected Result**:
- Exit code: 1 (non-zero)
- Error message about probability sum (should be 1.2, expected 1.0)

**Step 9: Verify Different Team Characteristics**
Compare team configurations:
```bash
echo "Team A serve ace rate:"
grep -A 3 "serve_probabilities:" team_a.yaml

echo "Team B serve ace rate:"
grep -A 3 "serve_probabilities:" team_b.yaml
```

**Expected Result**: Team A has higher ace rate (0.15) than Team B (0.08)

#### US-001 Success Criteria
- [x] Both teams created successfully
- [x] Teams have different serving vs receiving probabilities
- [x] Conditional probabilities validated (attack success varies by set quality)
- [x] Invalid configurations properly rejected
- [x] All probability distributions sum to 1.0

---

### US-002: Large Scale Point Simulation

**Story**: As an analyst, I want to simulate thousands of points between two teams so that I can gather statistically significant data on win rates.

#### Step-by-Step Validation

**Step 1: Run Large Simulation**
```bash
python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 5000 --output simulation_results.json --progress --seed 12345
```

**Expected Result**:
- Progress bar or percentage updates shown
- Completion message with win statistics
- Message: "Results saved to: simulation_results.json"
- Total execution time under 60 seconds (performance requirement)

**Step 2: Verify Results File**
```bash
ls -la simulation_results.json
cat simulation_results.json | head -20
```

**Expected Result**:
- File exists and has reasonable size (not empty, not excessively large)
- JSON format with simulation data
- Contains: total_points, team_a_score, team_b_score, points array

**Step 3: Analyze Results**
```bash
python -m bvsim_stats analyze-results --simulation simulation_results.json
```

**Expected Result**:
- "Total Points: 5000"
- Team A and B win counts that sum to 5000
- Win percentages displayed
- Point type breakdown (aces, kills, errors, blocks)
- Average point duration

**Step 4: Verify Statistical Significance**
```bash
python -m bvsim_stats analyze-results --simulation simulation_results.json --format json
```

**Expected Result**:
- JSON output with precise statistics
- Win rates that seem reasonable (e.g., between 30-70% for either team)
- Point type percentages that sum to 100%

**Step 5: Test Reproducibility**
```bash
python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 1000 --output test1.json --seed 999
python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 1000 --output test2.json --seed 999
```

```bash
diff test1.json test2.json
```

**Expected Result**: No differences (identical results with same seed)

**Step 6: Test Performance Requirement**
```bash
time python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 10000 --output performance_test.json
```

**Expected Result**: Completion in under 60 seconds

#### US-002 Success Criteria
- [x] 5000+ point simulation completes successfully
- [x] Results file created with complete data
- [x] Win statistics sum to total points
- [x] Reproducible results with same seed
- [x] Performance meets requirement (10,000 points in <60 seconds)

---

### US-003: Point Progression Verification

**Story**: As a coach, I want to review individual point progressions so that I can verify the state machine accurately represents beach volleyball rules with distinct serving and receiving team states.

#### Step-by-Step Validation

**Step 1: Generate Sample Points with Detailed Logging**
```bash
for i in {1..10}; do
  echo "=== Point $i ==="
  python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --verbose --seed $((1000 + i))
  echo ""
done
```

**Expected Result**: 10 different point progressions with detailed state information

**Step 2: Analyze Point Progression Format**
```bash
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --verbose --seed 2001
```

**Expected Result**: JSON output showing:
- `serving_team`: "A" or "B"
- `winner`: "A" or "B"  
- `point_type`: "ace", "kill", "error", "block", etc.
- `states`: Array of state objects with team, action, quality

**Step 3: Verify Team State Alternation**
Generate several points and check team sequences:
```bash
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --seed 3001 | jq '.states[] | "\(.team):\(.action)"'
```

**Expected Result**: Sequences like:
```
"A:serve"
"B:receive" 
"B:set"
"B:attack"
"A:block"
"A:dig"
"A:set"
"A:attack"
```

**Step 4: Verify Volleyball Rules Compliance**
Check for valid volleyball sequences:
```bash
# Look for points that start with serve
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --seed 4001 | jq '.states[0].action'

# Check that receiving team handles serve reception
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --seed 4002 | jq '.states | .[0], .[1]'
```

**Expected Result**:
- First action is always "serve"
- If Team A serves, Team B receives (and vice versa)
- Teams don't perform impossible actions (e.g., same team serving and immediately attacking)

**Step 5: Verify Conditional Probability Effects**
Generate many points and look for conditional probability patterns:
```bash
# Generate 50 points and save them
for i in {5001..5050}; do
  python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --seed $i >> sample_points.json
  echo "" >> sample_points.json
done

# Look for patterns in attack success after different set qualities
grep -A 1 -B 1 "excellent.*set" sample_points.json | grep -A 1 "attack"
grep -A 1 -B 1 "poor.*set" sample_points.json | grep -A 1 "attack"
```

**Expected Result**: 
- More kills after excellent sets than after poor sets
- Different outcome patterns based on previous state quality

**Step 6: Test Invalid State Transitions Detection**
This should be tested through the implementation - manually verify that impossible sequences cannot occur by examining many point samples.

**Step 7: Verify Point Conclusion Rules**
```bash
# Check that points end appropriately
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json --seed 6001 | jq '.states[-1]'
```

**Expected Result**: Final state should be a point-ending action (ace, kill, error, stuff block, etc.)

#### US-003 Success Criteria
- [x] All points start with serve action
- [x] Team alternation follows volleyball rules
- [x] No impossible state transitions occur
- [x] Conditional probabilities affect subsequent actions
- [x] Points conclude with valid ending states
- [x] Serving and receiving team states are distinct

---

### US-004: Sensitivity Analysis (Secondary)

**Story**: As an analyst, I want to perturb individual conditional probabilities to identify the most impactful contextual skills on win rate.

#### Step-by-Step Validation

**Step 1: Run Sensitivity Analysis on Attack Skill**
```bash
python -m bvsim_stats sensitivity-analysis --team team_a.yaml --parameter "attack_probabilities.excellent_set.kill" --range "0.7,0.95,0.05" --opponent team_b.yaml --points 500
```

**Expected Result**:
- Analysis showing parameter values from 0.7 to 0.95 in 0.05 increments
- Win rates for each parameter value
- Change from baseline for each value
- Impact factor classification (LOW/MEDIUM/HIGH)

**Step 2: Test Different Parameter**
```bash
python -m bvsim_stats sensitivity-analysis --team team_a.yaml --parameter "serve_probabilities.ace" --range "0.05,0.20,0.03" --opponent team_b.yaml --points 500
```

**Expected Result**: Different sensitivity pattern for serve aces vs attack kills

**Step 3: Verify Impact Calculation**
```bash
python -m bvsim_stats sensitivity-analysis --team team_a.yaml --parameter "attack_probabilities.excellent_set.kill" --range "0.7,0.95,0.05" --opponent team_b.yaml --points 500 --format json
```

**Expected Result**: JSON with precise impact calculations and ranges

#### US-004 Success Criteria
- [x] Sensitivity analysis runs successfully
- [x] Shows how parameter changes affect win rate
- [x] Different parameters show different impact patterns
- [x] Impact factors calculated correctly

---

### US-005: Team Comparison (Secondary)

**Story**: As a coach, I want to compare multiple team configurations side-by-side so that I can evaluate different strategic approaches.

#### Step-by-Step Validation

**Step 1: Create Third Team**
```bash
python -m bvsim_cli create-team --name "Balanced Team" --output team_c.yaml --template basic
```

**Step 2: Run Team Comparison**
```bash
python -m bvsim_cli compare-teams --teams team_a.yaml,team_b.yaml,team_c.yaml --points 300 --matrix
```

**Expected Result**:
- 3x3 comparison matrix showing win rates
- Team rankings in order of overall performance
- Clear formatting showing head-to-head results

**Step 3: Verify Matrix Symmetry**
The comparison matrix should show complementary win rates (if Team A beats Team B 60%, then Team B beats Team A 40%).

#### US-005 Success Criteria
- [x] Multiple teams compared successfully
- [x] Comparison matrix displays correctly
- [x] Rankings calculated from head-to-head results
- [x] Win rates are complementary (sum to 100% for each matchup)

---

## Performance Testing

### Large Scale Performance Test
```bash
time python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 15000 --output large_test.json
```

**Expected Result**: Completion in reasonable time (under 90 seconds for 15,000 points)

### Memory Usage Test
```bash
# Monitor memory usage during large simulation
python -m bvsim_cli run-simulation --team-a team_a.yaml --team-b team_b.yaml --points 10000 --output memory_test.json --progress &
PID=$!
while kill -0 $PID 2>/dev/null; do
  ps -p $PID -o pid,vsz,rss,comm
  sleep 2
done
```

**Expected Result**: Memory usage remains stable, doesn't grow excessively

## Error Handling Testing

### Invalid Input Testing
```bash
# Test missing files
python -m bvsim_core simulate-point --team-a nonexistent.yaml --team-b team_b.yaml

# Test malformed YAML
echo "invalid: yaml: content: [" > bad_team.yaml
python -m bvsim_core validate-team --team bad_team.yaml

# Test negative probabilities  
cat > negative_team.yaml << EOF
name: "Bad Team"
serve_probabilities:
  ace: -0.1
  in_play: 1.1
  error: 0.0
EOF
python -m bvsim_core validate-team --team negative_team.yaml
```

**Expected Results**: 
- Appropriate error codes (non-zero exit codes)
- Clear error messages
- No crashes or unexpected behavior

## CLI Standards Testing

### Help and Version Testing
```bash
# Test help flags
python -m bvsim_core --help
python -m bvsim_core simulate-point --help
python -m bvsim_stats --help
python -m bvsim_cli --help

# Test version flags
python -m bvsim_core --version
python -m bvsim_stats --version  
python -m bvsim_cli --version
```

**Expected Results**:
- All commands show usage information with --help
- All commands show version with --version
- Consistent formatting across all CLI tools

### Output Format Testing
```bash
# Test JSON output format
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format json
python -m bvsim_stats analyze-results --simulation simulation_results.json --format json

# Test text output format (default)
python -m bvsim_core simulate-point --team-a team_a.yaml --team-b team_b.yaml --format text
```

**Expected Results**:
- Valid JSON when --format json specified
- Human-readable text when --format text specified
- Consistent formatting standards

## Final Validation Checklist

### Functional Requirements
- [ ] State machine with distinct serving/receiving team states implemented
- [ ] Conditional probability distributions working correctly  
- [ ] Point simulation using team-specific probabilities
- [ ] Win statistics tracking and display
- [ ] Detailed point progression logging
- [ ] Probability validation (distributions sum to 1.0)
- [ ] Team role context maintained throughout points
- [ ] Sensitivity analysis functionality
- [ ] Correct team alternation in point flow

### Performance Requirements  
- [ ] 10,000 point simulation completes in under 60 seconds
- [ ] Memory usage remains stable during large simulations
- [ ] Results are deterministic with same random seed

### CLI Requirements
- [ ] All CLI commands implement --help, --version, --format flags
- [ ] JSON and text output formats supported
- [ ] Appropriate exit codes for success/failure
- [ ] Clear error messages for invalid inputs

### Data Integrity
- [ ] Team configurations save/load correctly
- [ ] Simulation results are reproducible with same seed
- [ ] Point progressions follow volleyball rules 100% of the time
- [ ] Statistical calculations are accurate

## Cleanup

After completing all tests:
```bash
cd ~
rm -rf ~/bvsim_test
```

## Troubleshooting

### Common Issues and Solutions

**Issue**: "Module not found" errors
**Solution**: Verify PYTHONPATH is set correctly and all libraries are in src/ directory

**Issue**: Simulation runs too slowly
**Solution**: Check for inefficient probability calculations or excessive logging

**Issue**: Invalid probability errors
**Solution**: Verify all probability dictionaries sum to 1.0 within tolerance

**Issue**: JSON parsing errors  
**Solution**: Validate JSON format using external JSON validators

**Issue**: Inconsistent results with same seed
**Solution**: Check that random seed is being set correctly in all simulation components

---

*This manual testing guide ensures comprehensive validation of all BVSim features according to the specification requirements. All tests should pass before the feature is considered complete.*