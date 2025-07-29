# bvsim-core CLI Contract

## Commands

### simulate-point
**Contract**: Simulate a single volleyball point between two teams

**Usage**: `python -m bvsim_core simulate-point --team-a <file> --team-b <file> [options]`

**Required Arguments**:
- `--team-a <file>`: YAML file containing Team A configuration
- `--team-b <file>`: YAML file containing Team B configuration

**Optional Arguments**:
- `--serving <A|B>`: Which team serves (default: A)
- `--seed <int>`: Random seed for reproducible results
- `--format <json|text>`: Output format (default: text)
- `--verbose`: Include detailed state progression
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success
- 1: Invalid team configuration
- 2: File not found
- 3: Invalid arguments

**Text Output Format**:
```
Point Result:
Serving Team: A
Winner: B
Point Type: kill
Duration: 6 states
States: A:serve(in_play) -> B:receive(good) -> B:set(excellent) -> B:attack(kill)
```

**JSON Output Format**:
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

### validate-team
**Contract**: Validate team probability configuration

**Usage**: `python -m bvsim_core validate-team --team <file> [options]`

**Required Arguments**:
- `--team <file>`: YAML file containing team configuration

**Optional Arguments**:
- `--format <json|text>`: Output format (default: text)
- `--help`: Show usage information
- `--version`: Show version information

**Exit Codes**:
- 0: Success (valid configuration)
- 1: Invalid team configuration
- 2: File not found
- 3: Invalid arguments

**Text Output Format (Success)**:
```
Team validation: PASSED
Team: Elite Attackers
All probability distributions valid
```

**Text Output Format (Failure)**:
```
Team validation: FAILED
Team: Elite Attackers
Errors:
- serve_probabilities sum to 0.98 (expected 1.00)
- attack_probabilities.excellent_set missing 'defended' outcome
```

**JSON Output Format**:
```json
{
  "valid": true,
  "team_name": "Elite Attackers",
  "errors": []
}
```

## Global Options
All commands must support:
- `--help`: Show usage information
- `--version`: Show version information
- `--format <json|text>`: Output format selection