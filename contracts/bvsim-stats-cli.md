# bvsim-stats CLI Contract

## Commands

### analyze-results
**Contract**: Analyze simulation results and generate statistics

**Usage**: `python -m bvsim_stats analyze-results --simulation <file> [options]`

**Required Arguments**:
- `--simulation <file>`: JSON file containing simulation results

**Optional Arguments**:
- `--format <json|text>`: Output format (default: text)
- `--breakdown`: Include detailed breakdown by point type
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid simulation data
- 2: File not found
- 3: Invalid arguments

**Text Output Format**:
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
**Contract**: Perform sensitivity analysis on team parameters

**Usage**: `python -m bvsim_stats sensitivity-analysis --team <file> --parameter <param> [options]`

**Required Arguments**:
- `--team <file>`: Base team YAML configuration
- `--parameter <param>`: Parameter to vary (e.g., "attack_probabilities.excellent_set.kill")
- `--range <min,max,step>`: Range to test (e.g., "0.7,0.95,0.05")
- `--opponent <file>`: Opponent team YAML configuration

**Optional Arguments**:
- `--points <int>`: Points per test (default: 1000)
- `--format <json|text>`: Output format (default: text)
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid configuration or parameter
- 2: File not found
- 3: Invalid arguments

**Text Output Format**:
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

## Global Options
All commands must support:
- `--help`: Show usage information
- `--version`: Show version information
- `--format <json|text>`: Output format selection