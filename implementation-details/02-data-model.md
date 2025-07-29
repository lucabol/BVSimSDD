# Data Model Specifications

## Core Entities

### Team
```python
@dataclass
class Team:
    name: str
    serve_probabilities: Dict[str, float]  # {ace: 0.1, in_play: 0.85, error: 0.05}
    receive_probabilities: Dict[str, Dict[str, float]]  # Conditional on serve quality
    set_probabilities: Dict[str, Dict[str, float]]      # Conditional on receive quality
    attack_probabilities: Dict[str, Dict[str, float]]   # Conditional on set quality
    block_probabilities: Dict[str, Dict[str, float]]    # Conditional on attack type
    dig_probabilities: Dict[str, Dict[str, float]]      # Conditional on attack/block
    
    def validate_probabilities(self) -> List[str]:
        """Validate all probability distributions sum to 1.0"""
        
    def to_yaml(self) -> str:
        """Serialize team to YAML format"""
        
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Team':
        """Deserialize team from YAML format"""
        
    def to_dict(self) -> dict:
        """Convert team to dictionary for JSON serialization of results"""
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Team':
        """Create team from dictionary"""
```

### State
```python
@dataclass
class State:
    name: str           # e.g., "Team_A_Serve", "Team_B_Receive"
    team: str          # "A" or "B"
    action: str        # "serve", "receive", "set", "attack", "block", "dig"
    quality: str       # "excellent", "good", "poor", "error", "ace", "kill", etc.
    touch_count: int   # Current touch number for the team
    
class StateType(Enum):
    SERVE = "serve"
    RECEIVE = "receive"
    SET = "set"
    ATTACK = "attack"
    BLOCK = "block"
    DIG = "dig"
    POINT_END = "point_end"
```

### Point
```python
@dataclass
class Point:
    id: str
    team_a: Team
    team_b: Team
    serving_team: str        # "A" or "B"
    states: List[State]      # Chronological state progression
    winner: str             # "A" or "B"
    point_type: str         # "ace", "kill", "error", "block", etc.
    duration_states: int    # Number of state transitions
    
    def add_state(self, state: State) -> None:
        """Add state transition to point progression"""
        
    def is_valid(self) -> bool:
        """Validate point follows volleyball rules"""
        
    def to_dict(self) -> dict:
        """Convert point to dictionary for JSON serialization"""
```

### Simulation
```python
@dataclass
class Simulation:
    id: str
    team_a: Team
    team_b: Team
    points: List[Point]
    team_a_score: int
    team_b_score: int
    total_points: int
    
    def add_point(self, point: Point) -> None:
        """Add completed point to simulation"""
        
    def get_win_rate(self, team: str) -> float:
        """Calculate win rate for specified team"""
        
    def get_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive simulation statistics"""
        
    def to_dict(self) -> dict:
        """Convert simulation to dictionary for JSON serialization"""
```

### ConditionalProbabilityMatrix
```python
@dataclass
class ConditionalProbabilityMatrix:
    team_name: str
    probabilities: Dict[str, Dict[str, Dict[str, float]]]
    # Structure: {state_type: {previous_condition: {outcome: probability}}}
    
    def get_probability(self, state_type: str, condition: str, outcome: str) -> float:
        """Get probability for specific outcome given condition"""
        
    def validate_matrix(self) -> List[str]:
        """Validate all probability distributions sum to 1.0"""
```

## Validation Rules

### Probability Distribution Validation
- All probability dictionaries must sum to 1.0 (±0.001 tolerance)
- Individual probabilities must be between 0.0 and 1.0
- Required outcomes must be present for each state type

### State Transition Validation
- Team alternation after ball crosses net
- Maximum 3 touches per team per possession
- Valid state sequences only (no impossible transitions)
- Proper point conclusion conditions

### Team Configuration Validation
- All required probability matrices present
- Conditional probabilities cover all possible previous states
- Team names must be unique and non-empty

## YAML Schema

### Team Configuration Schema
```yaml
name: "string"
serve_probabilities:
  ace: 0.0-1.0          # number [0-1]
  in_play: 0.0-1.0      # number [0-1]
  error: 0.0-1.0        # number [0-1]

receive_probabilities:
  in_play_serve:
    excellent: 0.0-1.0  # number [0-1]
    good: 0.0-1.0       # number [0-1]
    poor: 0.0-1.0       # number [0-1]
    error: 0.0-1.0      # number [0-1]

attack_probabilities:
  excellent_set:
    kill: 0.0-1.0       # number [0-1]
    error: 0.0-1.0      # number [0-1]
    defended: 0.0-1.0   # number [0-1]
  good_set:
    kill: 0.0-1.0
    error: 0.0-1.0
    defended: 0.0-1.0
  poor_set:
    kill: 0.0-1.0
    error: 0.0-1.0
    defended: 0.0-1.0

# Additional probability matrices for block, dig, etc.
block_probabilities:
  power_attack:
    stuff: 0.0-1.0
    deflection: 0.0-1.0
    no_touch: 0.0-1.0

dig_probabilities:
  deflected_attack:
    excellent: 0.0-1.0
    good: 0.0-1.0
    poor: 0.0-1.0
    error: 0.0-1.0
```

## Performance Considerations

- Use dataclasses for minimal memory overhead
- Implement efficient probability lookup (O(1) dictionary access)
- YAML serialization for human-readable team configs, JSON for simulation results
- Lazy validation to avoid repeated probability sum checks
- PyYAML safe_load for security (prevent code execution in YAML files)