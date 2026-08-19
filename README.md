# BVSim - Beach Volleyball Point Simulator 🏐

**A shot-by-shot simulator for beach volleyball points using conditional probability state machines.**

BVSim helps coaches and analysts understand team performance by simulating realistic volleyball points based on team-specific skill probabilities. The simulator accounts for conditional probabilities where success rates depend on previous actions (e.g., attack success varies based on set quality).

Prefer the graphical interface? See the [BVSim Web User Guide](README_WEB.md) for a pane-by-pane walkthrough and explanations of every generated statistic.

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

**Linux/macOS:**
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

**🆕 Windows:**
```cmd
REM Download or clone the project
cd path\to\bvsim

REM Run the Windows installer
install-windows.bat

REM Verify installation
bvsim.bat --version

REM See WINDOWS-SETUP.md for detailed Windows instructions
```

**Method 2: Python Package Installation**
```bash
# Clone the project and install as package
cd /path/to/bvsim
pip install -e .

# Now use 'bvsim' globally
bvsim --version
```

For faster large statistical analyses, install the optional CPU acceleration
backend:

```bash
pip install -e ".[acceleration]"
```

To enable the optional NVIDIA GPU backend, install the CuPy package matching
the CUDA runtime used by the deployment:

```bash
# Recommended for current Azure NVIDIA GPU images
pip install -e ".[acceleration,gpu-cuda12]"

# Use this instead on a CUDA 13 environment
pip install -e ".[acceleration,gpu-cuda13]"
```

BVSim automatically uses the compiled backend for large summary-only
simulations, including web Simulate, Compare, Skills, Scenarios, sensitivity,
and delta analyses. With a working CuPy installation and NVIDIA GPU, jobs of
at least one million points automatically use CUDA; medium jobs use Numba,
and small jobs use Python. The web Simulate and Compare panels also allow an
explicit Auto, CPU, or NVIDIA CUDA selection. Detailed rally histories remain
on Python, and every automatic path falls back to CPU when no GPU is present.

**Method 3: Direct Module Usage**
```bash
# Set Python path and use module directly
export PYTHONPATH=src
python3 -m bvsim --version
```

### Instant Analysis (No Setup Required)

**Linux/macOS:**
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

**Windows:**
```cmd
REM Find out which skills matter most - uses built-in team template
bvsim.bat skills

REM Quick team comparison using basic templates
bvsim.bat compare

REM Simulate points between default teams
bvsim.bat simulate

REM See rally examples in action
bvsim.bat examples
```

## Basic Usage

### 1. Advanced Skills Impact Analysis

**🎯 NEW: Statistical Analysis with Match Simulation & Confidence Intervals**

```bash
# Statistical analysis with confidence intervals (NEW!)
./bvsim skills                        # 5 statistical runs, 200k points each, 95% confidence
./bvsim skills --improve 10%          # Test a 10-point model perturbation
./bvsim skills --runs 10              # 10 statistical runs for higher confidence
./bvsim skills --confidence 0.99      # 99% confidence intervals

# Speed options with consistent statistical approach
./bvsim skills --quick                # Fast: 5 runs × 10k points each
./bvsim skills --accurate             # High precision: 5 runs × 200k points each

# Team-specific analysis
./bvsim skills team_a                 # Analyze specific team vs itself
./bvsim skills team_a team_b          # Compare two teams with statistical rigor
```

**Illustrative output format (values depend on the configured model and seed):**
```
BVSim Skills Statistical Analysis
Number of Runs: 5 | Average Duration: 2.8s
Baseline Win Rate: 50.2% [95% CI: 49.8% - 50.6%]
Testing +5.0% improvement on 36 parameters (200,000 points each)

Skill Parameter                                    Point Impact  Match Impact  95% Match CI              Holm Sig.
                                                   (% improve)   (% improve)   (Lower - Upper)           (Yes/No)   
--------------------------------------------------------------------------------------------------------------------------------------------
serve_probabilities.ace                             +3.24%     +24.15%     [+18.2% - +30.1%]         YES
attack_probabilities.excellent_set.kill             +2.18%     +16.87%     [+12.4% - +21.3%]         YES  
receive_probabilities.in_play_serve.excellent       +1.45%     +11.23%     [ +7.8% - +14.7%]         YES
block_probabilities.power_attack.stuff              +1.21%      +9.34%     [ +5.9% - +12.8%]         YES
set_probabilities.excellent_reception.excellent     +0.87%      +6.12%     [ +2.1% -  +8.9%]         YES

MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Skills):
Match % │
        │ ●────●     ┊                                                       serve_probabilities.ace
        │      ●──●  ┊                                                       attack_probabilities.excellent_set.kill
        │        ●─● ┊                                                       receive_probabilities.in_play_serve.excellent
        │         ●●─┊                                                       block_probabilities.power_attack.stuff
        │          ●─┊                                                       set_probabilities.excellent_reception.excellent
        │────────────────────────────────────────────────────────────────
        │0%          +10%                    +20%                     +30%

Legend: ● Holm-significant positive  ● Holm-significant negative  ○ Non-significant  ┊ Zero line

STATISTICAL SUMMARY:
Total skills analyzed: 36
Holm-significant positive impacts: 12
Top exploratory skill: serve_probabilities.ace
Point Impact: +3.24% [+2.8% - +3.7%]
Match Impact: +24.15% [+18.2% - +30.1%]
```

**🔥 Key Features:**
- **Service-aware Match Conversion**: Separate point rates when each team serves are converted deterministically under 21/21/15, win-by-two rules
- **Monte Carlo Intervals**: Run-level t intervals quantify simulation uncertainty for fixed model inputs
- **Multiplicity Control**: Holm-adjusted p-values are reported across each tested family
- **Holdout Confirmation**: Top exploratory candidates are rerun on independent random streams
- **Visual Charts**: Confidence interval charts with zero baseline for easy interpretation
- **Parallel Processing**: Multiple analyses run simultaneously for speed

#### Custom Team Variant Scenarios with Statistical Analysis

```bash
# Compare multiple full/partial team variant YAML files against baseline (default Basic team unless team args provided)
./bvsim skills --custom team_variant_a.yaml,team_variant_b.yaml,team_variant_c.yaml
./bvsim skills --custom $(echo variants/*.yaml | tr ' ' ',') --runs 10   # Expand then comma-join
./bvsim skills --custom variant_a.yaml --confidence 0.99 # Single file still allowed
```

**NEW Multi-file Statistical Output:**
```
Custom Scenarios Statistical Analysis
Number of Runs: 5 | Average Duration: 1.8s
Baseline Win Rate: 50.1% [95% CI: 49.7% - 50.5%]
Testing 3 custom team variants (200,000 points each)

Scenario File                                      Point Impact  Match Impact  95% Match CI              Holm Sig.
                                                   (% improve)   (% improve)   (Lower - Upper)           (Yes/No)   
--------------------------------------------------------------------------------------------------------------------------------------------
variant_attack_focus                                +4.12%     +31.24%     [+26.8% - +35.7%]         YES
variant_balanced                                    +3.18%     +23.47%     [+19.2% - +27.8%]         YES
variant_serve_focus                                 +2.84%     +20.15%     [+16.1% - +24.2%]         YES

MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Scenarios):
Match % │
        │ ●───────●  ┊                                                       scenario_attack_focused
        │       ●──● ┊                                                       scenario_balanced  
        │        ●─● ┊                                                       scenario_serve_focused
        │────────────────────────────────────────────────────────────────
        │0%          +10%                    +20%                     +30%

HOLM-SIGNIFICANT MODEL EFFECTS (EXPLORATORY):
1. scenario_attack_focused:
   Point: +4.12% [+3.8% - +4.4%] | Match: +31.24% [+26.8% - +35.7%]
2. scenario_balanced:
   Point: +3.18% [+2.9% - +3.5%] | Match: +23.47% [+19.2% - +27.8%]

Each scenario applies all changes from its file. The ranking is model-implied,
not a validated training recommendation.
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
Format: [Winner] Team.Action(Quality)→Team.Action(Quality)... → Point Type

 1. [B] A.srv(ok)→B.rcv(pr)→B.set(pr)→B.att(kill) → kill
 2. [A] B.srv(ok)→A.rcv(gd)→A.set(exc)→A.att(def)→B.blk(def→att)→A.dig(pr)→A.set(pr)→A.att(kill) → kill
 3. [A] A.srv(ace) → ace
 4. [A] B.srv(err) → serve_error
 5. [B] A.srv(ok)→B.rcv(exc)→B.set(pr)→B.att(def)→A.blk(miss)→A.dig(gd)→A.set(gd)→A.att(err) → attack_error

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

### Templates (External Configuration Files)
```bash
# Quick team creation using external template files
./bvsim create-team "Team Name"               # Uses templates/basic_team_template.yaml
./bvsim create-team "Elite Team" --advanced   # Uses templates/advanced_team_template.yaml  
./bvsim create-team "Custom" --interactive    # Guided creation with templates
```

**🆕 Template System:**
- **External Templates**: Team probabilities stored in `templates/*.yaml` files (not hardcoded)
- **Easy Customization**: Modify `templates/basic_team_template.yaml` to change default team characteristics
- **Version Control**: Template changes tracked separately from code changes
- **Key Principles**:
   - Every provided probability distribution must sum to 1.0 (validated automatically)
   - You can now provide **partial / minimal-diff team files**: omit any top-level sections that are unchanged from the Basic template

### Minimal-Diff Team YAMLs (NEW)
Instead of repeating the full structure, a team file may include only the sections that differ from the Basic template. Omitted sections are auto-filled with Basic defaults at load time.

Rules:
1. Any omitted top-level section (`serve_probabilities`, `receive_probabilities`, etc.) is copied from the Basic template.
2. If you include a section, each inner distribution you list must still be complete and sum to 1.0.
3. You may include only a subset of top-level sections (e.g., just `attack_probabilities`).
4. Validation still enforces correctness for the sections you provide.

Example – Full (OLD style) vs Minimal-Diff (NEW) Advanced Template:

Old (verbose):
```yaml
name: EliteAttack
serve_probabilities:
   ace: 0.10
   in_play: 0.85
   error: 0.05
attack_probabilities:
   excellent_set:
      kill: 0.80
      error: 0.10
      defended: 0.10
   good_set:
      kill: 0.60
      error: 0.15
      defended: 0.25
   poor_set:
      kill: 0.35
      error: 0.30
      defended: 0.35
... (other unchanged sections repeated)
```

Minimal-Diff (recommended):
```yaml
name: EliteAttack
attack_probabilities:
   excellent_set:
      kill: 0.80
      error: 0.10
      defended: 0.10
   good_set:
      kill: 0.60
      error: 0.15
      defended: 0.25
   poor_set:
      kill: 0.35
      error: 0.30
      defended: 0.35
```

Example – Single skill override (Serve-only specialist):
```yaml
name: AceMachine
serve_probabilities:
   ace: 1.0
   in_play: 0.0
   error: 0.0
```

Example – Multiple section overrides:
```yaml
name: StrongReceptionDefense
receive_probabilities:
   in_play_serve:
      excellent: 0.38
      good: 0.44
      poor: 0.17
      error: 0.01
block_probabilities:
   power_attack:
      stuff: 0.22
      deflection_to_attack: 0.165
      deflection_to_defense: 0.165
      no_touch: 0.45
```

The loader merges these with the Basic defaults internally, so downstream simulation logic always receives a fully populated team object.

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

### Statistical Options (Skills Analysis)
- **`--runs N`** - Number of statistical runs (default: 5)
- **`--confidence 0.XX`** - Confidence level (default: 0.95 for 95%)
- **`--no-parallel`** - Disable parallel processing (for debugging)

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
| `./bvsim skills` | 5 runs × 10k points | **5 runs × 200k points** | 5 runs × 200k points |
| `./bvsim compare` | 10k points | 50k points | 200k points |
| `./bvsim simulate` | 10k points | 100k points | 200k points |

**🆕 Skills Analysis Statistical Defaults:**
- **Default behavior**: Always runs 5 statistical repetitions for confidence intervals
- **High precision by default**: 200k points per run (was 100k) for better statistical power  
- **Customizable**: Use `--runs N` and `--confidence 0.XX` for different statistical rigor

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

### 🆕 Statistical Analysis Interpretation

**Match Impact vs Point Impact:**
- **Point Impact**: Direct win rate change from improved skill (e.g., +2.5%)  
- **Match Impact**: Amplified effect in actual volleyball matches (e.g., +18.3%)
- **Why the amplification?** In volleyball, small point advantages compound across 21-point sets with win-by-2 rules

**Confidence Intervals:**
- **95% CI [+15.2% - +21.4%]**: Monte Carlo uncertainty across independent runs under the configured model
- **Holm Sig. = YES**: The model effect passes family-wise multiple-comparison correction
- **Holm Sig. = No**: The simulation does not distinguish the effect from zero at the requested level
- One run reports its interval and significance as unavailable.

**Visual Charts:**
- **●**: Holm-significant model effect with confidence interval bar
- **○**: Non-significant result (could be random)
- **┊**: Zero line - no improvement baseline
- **Chart always shows 0%**: Easy comparison to "no change" reference point

**Statistical Significance:**
```
Point Impact: +2.1% | Match Impact: +16.3% [+12.1% - +20.5%] | Significant: YES
↑                    ↑                      ↑                   ↑
Direct effect        Modeled match         Monte Carlo CI      Holm adjusted
                     amplification         interval            improvement
```

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

### Exploratory Model Analysis
```bash
# 1. Explore model sensitivity with controlled Monte Carlo uncertainty
./bvsim skills my_team --runs 10
./bvsim skills my_team --improve 10% --confidence 0.99

# 2. Scout the opponent  
./bvsim create-team "Opponent" --output opponent.yaml
# Edit opponent.yaml based on scouting

# 3. Analyze the matchup with match impact simulation
./bvsim compare my_team opponent --accurate
./bvsim simulate my_team opponent --accurate --breakdown

# 4. Study rally patterns
./bvsim examples 10 --teams my_team opponent

# 5. Compare hypothetical team configurations
./bvsim skills my_team --custom improvements/*.yaml --runs 10    # Compare all training scenarios
# Treat rankings as exploratory until calibrated against observed match data
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

### Scenario Exploration
```bash
# Find model parameters with Holm-significant simulated effects
./bvsim skills my_team --improve 10% --runs 10

# Test realistic training improvements with confidence intervals  
./bvsim skills my_team --custom training_goals.yaml --confidence 0.99
# Review Holm-adjusted results and independent holdout confirmation

# Quick statistical iteration during training planning
./bvsim skills my_team --improve 5% --quick --runs 3        # Fast but still statistical

# Compare multiple hypothetical approaches under the model
./bvsim skills my_team --custom scenario_a.yaml scenario_b.yaml scenario_c.yaml --runs 10
# Do not convert this ranking directly into a training prescription

# Generate rally examples to understand skill application patterns
./bvsim examples 15 --teams my_team
```

> [!IMPORTANT]
> BVSim has not been calibrated or validated against observed match data. Its
> intervals describe Monte Carlo uncertainty under fixed input probabilities,
> not uncertainty about real teams. Rankings and match impacts are
> model-implied exploratory results, not evidence that a training intervention
> will produce the reported real-world effect.

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