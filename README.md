# BVSim - Beach Volleyball Point Simulator 🏐

**A shot-by-shot simulator for beach volleyball points using conditional probability state machines.**

BVSim helps coaches and analysts understand team performance by simulating realistic volleyball points based on team-specific skill probabilities. The simulator accounts for conditional probabilities where success rates depend on previous actions (e.g., attack success varies based on set quality).

## Features

- **🎯 Conditional Probability Engine**: Attack success depends on set quality, dig success depends on block type
- **🏐 Realistic Block Mechanics**: Four distinct block outcomes with proper volleyball rules (2-touch rule for deflections)
- **📊 Statistical Analysis**: Win rates, point type breakdowns, duration analysis
- **🔍 Sensitivity Analysis**: Identify which skills have the biggest impact on winning
- **⚖️ Team Comparison**: Compare multiple team configurations side-by-side
- **⚡ High Performance**: Simulate 100,000+ points per second
- **🔄 Reproducible Results**: Seed-based randomization for consistent testing

## Quick Start

### Installation

**Method 1: Wrapper Script (Recommended)**
```bash
# Clone or download the project
cd /path/to/bvsim

# Make the CLI executable
chmod +x bvsim

# Verify installation
./bvsim --version

# Optional: Add to PATH for global access (then use just 'bvsim' instead of './bvsim')
# sudo ln -s $(pwd)/bvsim /usr/local/bin/bvsim
```

**Method 2: Python Package Installation**
```bash
# Clone the project and install as package
cd /path/to/bvsim
pip install -e .

# Now use 'bvsim' globally
bvsim --version
```

**Method 3: Direct Module Usage**
```bash
# Set Python path and use module directly
export PYTHONPATH=src
python3 -m bvsim --version
```

### Instant Analysis (No Setup Required)
```bash
# Find out which skills matter most - uses built-in team template
./bvsim skills

# Quick team comparison using basic templates
./bvsim compare

# Simulate points between default teams
./bvsim simulate

# See rally examples in action
./bvsim examples
```

## Basic Usage

### 1. Skill Impact Analysis
```bash
# What skills have the biggest impact on winning?
./bvsim skills                        # Basic analysis (100k points each)
./bvsim skills --improve 5%           # Test 5% improvement to all skills  
./bvsim skills --quick                # Fast analysis (10k points)
./bvsim skills --accurate             # High precision (200k points)
./bvsim skills team_a                 # Analyze specific team vs itself
./bvsim skills team_a team_b          # Compare two teams
```

**Sample output:**
```
Skill Impact Analysis (100,000 points each):
Testing 36 parameters with +5.0% improvement
Baseline win rate: 49.3%

Rank Parameter                                     Win Rate  Improvement
---------------------------------------------------------------------------
1    serve_probabilities.ace                       52.7%     +3.4%
2    attack_probabilities.excellent_set.kill       51.8%     +2.5%  
3    block_probabilities.power_attack.no_touch     51.2%     +1.9%
4    attack_probabilities.good_set.kill            50.9%     +1.6%
5    receive_probabilities.in_play_serve.excellent 50.7%     +1.4%

Focus training on: Serve accuracy, attack from excellent sets, blocking
```

#### Custom Improvement Scenarios
```bash
# Compare multiple improvement strategies
./bvsim skills --custom examples/scenario_serve_focused.yaml examples/scenario_attack_focused.yaml examples/scenario_balanced.yaml --quick
```

**Multi-file output example:**
```
Multi-File Skill Impact Analysis (10,000 points each):
Testing 3 custom improvement files: examples/scenario_serve_focused.yaml, examples/scenario_attack_focused.yaml, examples/scenario_balanced.yaml
Baseline win rate: 49.1%

Rank Configuration                Win Rate  Improvement
------------------------------------------------------
1    scenario_attack_focused      53.6    %     +4.5%
2    scenario_balanced            52.6    %     +3.5%
3    scenario_serve_focused       52.2    %     +3.2%

Each configuration applies all deltas from its file together.
```

### 2. Team Comparison
```bash
# Compare multiple teams 
./bvsim compare team_a team_b team_c   # Head-to-head matrix
./bvsim compare --tournament           # Round-robin with rankings
./bvsim compare --quick                # Fast comparison (10k points)
./bvsim compare --accurate             # High precision (200k points)
```

### 3. Point Simulation
```bash
# Simulate volleyball points
./bvsim simulate                       # Basic teams, 100k points
./bvsim simulate team_a team_b         # Custom teams
./bvsim simulate --quick               # Fast simulation (10k points)
./bvsim simulate --accurate            # High precision (200k points)
./bvsim simulate --breakdown           # Detailed statistics
./bvsim simulate --points 5000         # Custom point count
```

### 4. Results Analysis  
```bash
# Analyze simulation results
./bvsim analyze results.json           # From simulation file
./bvsim analyze --breakdown            # Detailed point type analysis
```

### 5. Rally Examples
```bash
# Generate concise rally representations
./bvsim examples                       # 20 rallies with default teams
./bvsim examples 10                    # 10 rallies
./bvsim examples 5 --teams team_a team_b  # 5 rallies with specific teams
./bvsim examples --seed 12345          # Reproducible examples
```

**Sample output:**
```
Rally Examples (5 rallies): Team A vs Team B
Format: [Winner] Server→Action(Quality)→Action(Quality)... → Point Type

 1. [B] A→srv(ok)→B→rcv(pr)→B→set(pr)→B→att(kill) → kill
 2. [A] B→srv(ok)→A→rcv(gd)→A→set(exc)→A→att(def)→B→blk(def→att)→A→dig(pr)→A→set(pr)→A→att(kill) → kill
 3. [A] A→srv(ace) → ace
 4. [A] B→srv(err) → serve_error
 5. [B] A→srv(ok)→B→rcv(exc)→B→set(pr)→B→att(def)→A→blk(miss)→A→dig(gd)→A→set(gd)→A→att(err) → attack_error

Legend: srv=serve, rcv=receive, set=set, att=attack, blk=block, dig=dig
        exc=excellent, gd=good, pr=poor, err=error, def=defended
```

## Team Configuration

Teams are defined in YAML files with conditional probability distributions. The complete structure includes:

- **serve_probabilities**: Serve outcomes (ace, in_play, error)
- **receive_probabilities**: Reception quality conditional on serve type
- **set_probabilities**: Set quality conditional on reception quality (excellent, good, poor, error)
- **attack_probabilities**: Attack outcomes conditional on set quality
- **block_probabilities**: Block outcomes conditional on attack type
- **dig_probabilities**: Dig quality conditional on block outcome

### Templates
```bash
# Quick team creation
./bvsim create-team "Team Name"               # Basic template
./bvsim create-team "Elite Team" --advanced   # Advanced template  
./bvsim create-team "Custom" --interactive    # Guided creation
```

**Key Principle**: All probability distributions must sum to 1.0. The simulator validates this automatically.

## Block Mechanics

BVSim models realistic volleyball blocking with four distinct outcomes:

### Block Outcomes

1. **`stuff`** - Successful block that ends the point immediately
   - Ball is blocked down onto attacking team's court
   - Defending team wins the point

2. **`deflection_to_attack`** - Ball deflects back to attacking team's side
   - Attacking team must dig their own deflected ball
   - Rally continues with normal 3-touch sequence: dig → set → attack

3. **`deflection_to_defense`** - Ball deflects to defending team's side  
   - Defending team has only **2 touches** remaining (volleyball rule)
   - Sequence: set → attack (no dig phase)
   - Realistic implementation of block-touch rule

4. **`no_touch`** - Block attempt misses the ball completely
   - Attack continues as if unblocked
   - Defending team may attempt floor defense

### Volleyball Logic Examples

```
# Deflection to attacking team (3-touch rule)
B:attack(defended) → A:block(deflection_to_attack) → B:dig → B:set → B:attack

# Deflection to defending team (2-touch rule)  
B:attack(defended) → A:block(deflection_to_defense) → A:set → A:attack

# Successful block
B:attack(defended) → A:block(stuff) → Point ends (A wins)

# Missed block
B:attack(defended) → A:block(no_touch) → A:dig (80%) OR attack lands (20%)
```

**Key Insight**: The simulator correctly implements volleyball's block-touch rule where a deflection to the defending team's side limits them to only 2 remaining touches, making the sequence more challenging and realistic.

## Advanced Usage

### Custom Team Analysis
```bash
# Create custom teams
./bvsim create-team "My Team" --advanced --output my_team.yaml

# Analyze custom improvements (single file)
./bvsim skills my_team --custom improvements.yaml

# Compare multiple improvement scenarios
./bvsim skills my_team --custom scenario_a.yaml scenario_b.yaml scenario_c.yaml

# Comprehensive skill testing
./bvsim skills my_team --improve 10% --accurate
```

### Detailed Simulation Analysis
```bash
# High-precision simulation with full breakdown
./bvsim simulate team_a team_b --accurate --breakdown --output detailed.json

# Quick iteration testing
./bvsim simulate --quick --breakdown

# Custom analysis workflows
./bvsim simulate --points 50000 --breakdown
./bvsim analyze detailed.json --breakdown
```

## Command Reference

### Core Commands
- **`./bvsim skills`** - Analyze which skills have biggest impact on winning
- **`./bvsim compare`** - Compare team performance head-to-head  
- **`./bvsim simulate`** - Run point simulations
- **`./bvsim analyze`** - Analyze simulation results
- **`./bvsim create-team`** - Create new team configurations
- **`./bvsim examples`** - Generate concise rally representations

### Speed Options (Consistent Across Commands)
- **`--quick`** - Fast analysis (10,000 points)
- **(default)** - Balanced analysis (100,000 points)
- **`--accurate`** - High precision (200,000 points)
- **`--points N`** - Custom point count

### Other Options
- **`--breakdown`** - Detailed statistics and breakdowns
- **`--format json`** - JSON output for scripting
- **`--tournament`** - Tournament-style rankings (compare only)

### File Handling
```bash
# Auto-discovery (no file paths needed)
./bvsim skills                        # Uses built-in templates
./bvsim compare                       # Finds team_*.yaml files
./bvsim analyze                       # Finds recent results.json

# Explicit files  
./bvsim skills team_a.yaml team_b.yaml
./bvsim analyze simulation_results.json
```

## Consistent Speed Options

All major commands support the same speed options for predictable performance:

| Command | --quick | Default | --accurate |
|---------|---------|---------|------------|
| `./bvsim skills` | 10k points | 100k points | 200k points |
| `./bvsim compare` | 10k points | 50k points | 200k points |
| `./bvsim simulate` | 10k points | 100k points | 200k points |

**Example workflows:**
```bash
# Quick iteration during development
./bvsim skills --quick
./bvsim compare --quick  
./bvsim simulate --quick

# Production analysis (default - no flags needed)
./bvsim skills
./bvsim compare
./bvsim simulate

# High precision for final decisions
./bvsim skills --accurate
./bvsim compare --accurate
./bvsim simulate --accurate --breakdown
```

## Understanding Results

### Point Types
- **ace**: Direct point from serve
- **kill**: Successful attack
- **serve_error**: Failed serve
- **attack_error**: Failed attack
- **receive_error**: Failed reception
- **set_error**: Failed set (setter loses point immediately)
- **stuff**: Successful block
- **dig_error**: Failed dig
- **rally**: Extended rally (simplified ending)

### State Progression
Points follow realistic volleyball sequences:
```
A:serve(in_play) → B:receive(excellent) → B:set(excellent) → B:attack(kill)
A:serve(in_play) → B:receive(poor) → B:set(error) → Point ends (A wins)
A:serve(in_play) → B:receive(good) → B:set(good) → B:attack(defended) → A:block(deflection_to_attack) → B:dig(excellent) → [rally continues]
A:serve(in_play) → B:receive(poor) → B:set(poor) → B:attack(defended) → A:block(deflection_to_defense) → A:set(good) → A:attack(kill)
```

**Key Insights**: 
- Set quality depends on reception quality, which affects attack success (reception→set→attack chain)
- Set errors end points immediately - poor receptions increase the risk of setting mistakes
- Block deflections create different scenarios: deflection_to_attack continues normal rally, deflection_to_defense enforces 2-touch rule
- Realistic volleyball mechanics create dynamic point progressions with proper team role switching

### Sensitivity Analysis Results
- **Impact Factor**: 
  - LOW: <2% win rate change
  - MEDIUM: 2-5% win rate change  
  - HIGH: >5% win rate change

## Performance

- **100,000+ points/second** on modern hardware
- **Auto-optimization** - uses appropriate sample sizes for accuracy vs speed
- **Memory efficient** - stable usage during large simulations  
- **Reproducible** - same seed produces identical results

## Common Use Cases

### Coach Preparation
```bash
# 1. Analyze your team's skill priorities
./bvsim skills my_team --accurate

# 2. Scout the opponent  
./bvsim create-team "Opponent" --output opponent.yaml
# Edit opponent.yaml based on scouting

# 3. Analyze the matchup
./bvsim compare my_team opponent --accurate
./bvsim simulate my_team opponent --accurate --breakdown

# 4. Study rally patterns
./bvsim examples 10 --teams my_team opponent

# 5. Identify training focus
./bvsim skills my_team --custom potential_improvements.yaml --accurate
```

### Tournament Analysis
```bash
# 1. Create all tournament teams
./bvsim create-team "Team A" --output team_a.yaml
./bvsim create-team "Team B" --output team_b.yaml  
./bvsim create-team "Team C" --output team_c.yaml

# 2. Run tournament comparison
./bvsim compare team_*.yaml --tournament --accurate

# 3. Analyze specific matchups
./bvsim compare team_a team_b --accurate
./bvsim simulate team_a team_b --accurate --breakdown
./bvsim examples 5 --teams team_a team_b
```

### Training Focus
```bash
# Find highest-impact skills for training
./bvsim skills my_team --improve 10% --accurate

# Test realistic improvements
./bvsim skills my_team --custom training_goals.yaml --accurate

# Quick iteration during training
./bvsim skills my_team --improve 5% --quick

# Compare multiple improvement scenarios at once
./bvsim skills my_team --custom scenario_a.yaml scenario_b.yaml scenario_c.yaml --accurate

# Generate rally examples to see patterns
./bvsim examples 15 --teams my_team
```

**Example deltas.yaml file:**
```yaml
# Additive improvements to specific probabilities
serve_probabilities.ace: 0.05                           # +5% ace rate
receive_probabilities.in_play_serve.excellent: 0.10     # +10% excellent reception
set_probabilities.excellent_reception.excellent: 0.05   # +5% excellent sets
attack_probabilities.excellent_set.kill: 0.10           # +10% kill rate
block_probabilities.power_attack.stuff: 0.08            # +8% stuff rate
dig_probabilities.deflected_attack.excellent: 0.15      # +15% excellent digs
```

**Example scenario files for multi-file comparison (in `examples/` directory):**

*examples/scenario_serve_focused.yaml:*
```yaml
# Serve-focused improvements
serve_probabilities.ace: 0.08                      # +8% ace rate
serve_probabilities.in_play: 0.02                  # +2% in-play serves
```

*examples/scenario_attack_focused.yaml:*
```yaml
# Attack-focused improvements  
attack_probabilities.excellent_set.kill: 0.12     # +12% kill rate from excellent sets
attack_probabilities.good_set.kill: 0.08          # +8% kill rate from good sets
attack_probabilities.poor_set.kill: 0.05          # +5% kill rate from poor sets
```

*examples/scenario_balanced.yaml:*
```yaml
# Balanced improvements across skills
serve_probabilities.ace: 0.03                      # +3% ace rate
attack_probabilities.excellent_set.kill: 0.05     # +5% kill rate
block_probabilities.power_attack.stuff: 0.04      # +4% stuff rate
receive_probabilities.in_play_serve.excellent: 0.06 # +6% excellent reception
```

## Troubleshooting

### Quick Fixes
```bash
# "Module not found" errors
export PYTHONPATH=src

# "No teams found" 
./bvsim create-team "Default" --template basic

# "Probabilities don't sum to 1.0"
./bvsim validate team.yaml

# Slow performance
./bvsim skills --quick              # Use faster analysis
```

### Common Issues
- **Missing team files**: Use `./bvsim skills` without arguments for instant analysis
- **Invalid probabilities**: Run `./bvsim validate team.yaml` to check configuration
- **Inconsistent results**: Ensure you're using enough sample points (`--accurate`)

## Getting Help

```bash
./bvsim --help                    # General help
./bvsim skills --help             # Command-specific help  
...
```

## Contributing

BVSim follows constitutional development principles:
- Simple Python code with minimal dependencies
- Test-driven development with comprehensive coverage
- Library-first architecture with CLI interfaces
- No unnecessary abstractions or complexity

## License

[Add your license information here]

## Support

For questions about volleyball rules, probability modeling, or advanced usage, please refer to the [manual-testing.md](manual-testing.md) guide for comprehensive examples.

---

**BVSim** - Bringing data-driven insights to beach volleyball coaching! 🏐📊