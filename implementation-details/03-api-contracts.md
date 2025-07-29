# CLI API Contracts

## bvsim-core CLI Commands

### simulate-point
**Purpose**: Simulate a single volleyball point between two teams

**Usage**: `bvsim-core simulate-point --team-a <file> --team-b <file> [options]`

**Arguments**:
- `--team-a <file>`: YAML file containing Team A configuration
- `--team-b <file>`: YAML file containing Team B configuration  
- `--serving <A|B>`: Which team serves (default: A)
- `--seed <int>`: Random seed for reproducible results
- `--format <json|text>`: Output format (default: text)
- `--verbose`: Include detailed state progression

**Output (text)**:
```
Point Result:
Serving Team: A
Winner: B
Point Type: kill
Duration: 6 states
States: A:serve(in_play) -> B:receive(good) -> B:set(excellent) -> B:attack(kill)
```

**Output (json)**:
```json
{
  "serving_team": "A",
  "winner": "B", 
  "point_type": "kill",
  "duration": 6,
  "states": [
    {"team": "A", "action": "serve", "quality": "in_play"},
    {"team": "B", "action": "receive", "quality": "good"},
    {"team": "B", "action": "set", "quality": "excellent"},
    {"team": "B", "action": "attack", "quality": "kill"}
  ]
}
```

**Exit Codes**:
- 0: Success
- 1: Invalid team configuration
- 2: File not found
- 3: Invalid arguments

### validate-team
**Purpose**: Validate team probability configuration

**Usage**: `bvsim-core validate-team --team <file> [options]`

**Arguments**:
- `--team <file>`: YAML file containing team configuration
- `--format <json|text>`: Output format (default: text)

**Output (success)**:
```
Team validation: PASSED
Team: Elite Attackers
All probability distributions valid
```

**Output (failure)**:
```
Team validation: FAILED
Team: Elite Attackers
Errors:
- serve_probabilities sum to 0.98 (expected 1.00)
- attack_probabilities.excellent_set missing 'defended' outcome
```

## bvsim-stats CLI Commands

### analyze-results
**Purpose**: Analyze simulation results and generate statistics

**Usage**: `bvsim-stats analyze-results --simulation <file> [options]`

**Arguments**:
- `--simulation <file>`: JSON file containing simulation results
- `--format <json|text>`: Output format (default: text)
- `--breakdown`: Include detailed breakdown by point type

**Output**:
```
Simulation Analysis:
Total Points: 10000
Team A Wins: 6247 (62.47%)
Team B Wins: 3753 (37.53%)

Point Types:
- Aces: 892 (8.92%)
- Kills: 4521 (45.21%) 
- Errors: 2387 (23.87%)
- Blocks: 2200 (22.00%)

Average Point Duration: 4.2 states
```

### sensitivity-analysis
**Purpose**: Perform sensitivity analysis on team parameters

**Usage**: `bvsim-stats sensitivity-analysis --team <file> --parameter <param> [options]`

**Arguments**:
- `--team <file>`: Base team configuration
- `--parameter <param>`: Parameter to vary (e.g., "attack_probabilities.excellent_set.kill")
- `--range <min,max,step>`: Range to test (e.g., "0.7,0.95,0.05")
- `--opponent <file>`: Opponent team configuration
- `--points <int>`: Points per test (default: 1000)
- `--format <json|text>`: Output format

**Output**:
```
Sensitivity Analysis: attack_probabilities.excellent_set.kill
Base win rate: 62.47%

Parameter Value | Win Rate | Change
0.70           | 58.32%   | -4.15%
0.75           | 60.21%   | -2.26%  
0.80           | 62.47%   |  0.00% (base)
0.85           | 64.88%   | +2.41%
0.90           | 67.12%   | +4.65%
0.95           | 69.45%   | +6.98%

Impact Factor: HIGH (6.98% range)
```

## bvsim-cli CLI Commands

### create-team
**Purpose**: Interactive team configuration creation

**Usage**: `bvsim-cli create-team --name <name> [options]`

**Arguments**:
- `--name <name>`: Team name
- `--output <file>`: Output file (default: <name>.yaml)
- `--template <basic|advanced>`: Configuration template
- `--interactive`: Interactive mode with prompts

**Output**: Creates YAML team configuration file

### run-simulation
**Purpose**: Run large-scale point simulation

**Usage**: `bvsim-cli run-simulation --team-a <file> --team-b <file> --points <int> [options]`

**Arguments**:
- `--team-a <file>`: Team A YAML configuration
- `--team-b <file>`: Team B YAML configuration
- `--points <int>`: Number of points to simulate
- `--output <file>`: Output file for results (JSON format)
- `--progress`: Show progress bar
- `--seed <int>`: Random seed
- `--format <json|text>`: Output format

**Output**:
```
Running simulation: 10000 points
Team A: Elite Attackers
Team B: Strong Defense
Progress: [████████████████████] 100% (10000/10000)

Simulation Complete:
Team A Wins: 6247 (62.47%)
Team B Wins: 3753 (37.53%)
Total Duration: 12.3 seconds
Results saved to: simulation_results.json
```

### compare-teams
**Purpose**: Compare multiple team configurations

**Usage**: `bvsim-cli compare-teams --teams <file1,file2,file3> [options]`

**Arguments**:
- `--teams <files>`: Comma-separated team YAML configuration files
- `--points <int>`: Points per matchup (default: 1000) 
- `--format <json|text>`: Output format
- `--matrix`: Show full comparison matrix

**Output**:
```
Team Comparison Matrix (1000 points per matchup):

           | Elite  | Strong | Balanced
Elite      |   -    | 62.4%  | 58.7%
Strong     | 37.6%  |   -    | 51.2%
Balanced   | 41.3%  | 48.8%  |   -

Overall Rankings:
1. Elite Attackers (60.55% avg)
2. Balanced Team (50.00% avg) 
3. Strong Defense (44.40% avg)
```

## Standard CLI Options

All commands support:
- `--help`: Show usage information
- `--version`: Show version information
- `--format <json|text>`: Output format selection
- `--quiet`: Suppress non-essential output
- `--verbose`: Increase output detail

## Error Handling

### Common Error Codes
- 0: Success
- 1: Invalid configuration/input
- 2: File not found
- 3: Invalid arguments
- 4: Calculation/simulation error
- 5: Permission/access error

### Error Message Format
```json
{
  "error": "Invalid team configuration",
  "details": "serve_probabilities sum to 0.98, expected 1.00",
  "file": "team_a.json",
  "line": null
}
```

## Input/Output Standards

### File Formats
- Team configurations: YAML (human-readable, easy to edit)
- Simulation results: JSON (structured data for analysis)
- Progress output: Text to stderr
- Results: JSON or human-readable text

### Schema Validation
- YAML team inputs conform to schemas defined in 02-data-model.md
- JSON simulation outputs conform to schemas defined in 02-data-model.md

### Text Output Standards
- Consistent formatting across all commands
- Progress information to stderr
- Results to stdout
- Machine-parseable when --format=json