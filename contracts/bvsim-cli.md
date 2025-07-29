# bvsim-cli CLI Contract

## Commands

### create-team
**Contract**: Interactive team configuration creation

**Usage**: `python -m bvsim_cli create-team --name <name> [options]`

**Required Arguments**:
- `--name <name>`: Team name

**Optional Arguments**:
- `--output <file>`: Output file (default: <name>.yaml)
- `--template <basic|advanced>`: Configuration template (default: basic)
- `--interactive`: Interactive mode with prompts (default: false)
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid arguments or template
- 2: File write error
- 3: Invalid arguments

**Output**: Creates YAML team configuration file

**Basic Template**: Standard probability distributions for all required states
**Advanced Template**: More detailed probability matrices with additional conditional states

### run-simulation
**Contract**: Run large-scale point simulation

**Usage**: `python -m bvsim_cli run-simulation --team-a <file> --team-b <file> --points <int> [options]`

**Required Arguments**:
- `--team-a <file>`: Team A YAML configuration
- `--team-b <file>`: Team B YAML configuration
- `--points <int>`: Number of points to simulate

**Optional Arguments**:
- `--output <file>`: Output file for results (default: stdout, JSON format)
- `--progress`: Show progress bar
- `--seed <int>`: Random seed for reproducibility
- `--format <json|text>`: Output format (default: text)
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid team configuration
- 2: File not found or write error
- 3: Invalid arguments

**Text Output Format**:
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
**Contract**: Compare multiple team configurations

**Usage**: `python -m bvsim_cli compare-teams --teams <file1,file2,file3> [options]`

**Required Arguments**:
- `--teams <files>`: Comma-separated team YAML configuration files

**Optional Arguments**:
- `--points <int>`: Points per matchup (default: 1000)
- `--format <json|text>`: Output format (default: text)
- `--matrix`: Show full comparison matrix
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid team configuration
- 2: File not found
- 3: Invalid arguments

**Text Output Format**:
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

## Global Options
All commands must support:
- `--help`: Show usage information
- `--version`: Show version information
- `--format <json|text>`: Output format selection (where applicable)