#!/usr/bin/env python3
"""
Team data model for beach volleyball simulation.
Represents a team with conditional probability distributions for all skills.
"""

import yaml
from dataclasses import dataclass
from typing import Dict, List, Any
from pathlib import Path


@dataclass
class Team:
    """
    Represents a beach volleyball team with conditional probability distributions.
    
    Each team has probability matrices for different skills (serve, receive, attack, etc.)
    where success rates depend on previous action quality.
    """
    
    name: str
    serve_probabilities: Dict[str, float]
    receive_probabilities: Dict[str, Dict[str, float]]
    set_probabilities: Dict[str, Dict[str, float]]
    attack_probabilities: Dict[str, Dict[str, float]]
    block_probabilities: Dict[str, Dict[str, float]]
    dig_probabilities: Dict[str, Dict[str, float]]
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'Team':
        """Load team from YAML file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Team file not found: {file_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Team':
        """Create team from dictionary, allowing partial definitions.

        Any omitted top-level probability sections are filled from the Basic template
        defaults. If a section is provided it must contain full distributions for
        its included conditions (validation handled elsewhere). This lets users
        specify only the *differences* versus the Basic template.
        """
        # Lazy import to avoid circular dependency (templates module imports core)
        try:
            from bvsim_cli.templates import get_basic_template  # type: ignore
            basic_defaults = get_basic_template("__BASIC_INTERNAL_DEFAULTS__")
        except Exception:
            # Fallback minimal defaults mirroring original basic template values
            basic_defaults = {
                'serve_probabilities': { 'ace': 0.10, 'in_play': 0.85, 'error': 0.05 },
                'receive_probabilities': {
                    'in_play_serve': { 'excellent': 0.35, 'good': 0.40, 'poor': 0.20, 'error': 0.05 }
                },
                'set_probabilities': {
                    'excellent_reception': { 'excellent': 0.69, 'good': 0.25, 'poor': 0.05, 'error': 0.01 },
                    'good_reception': { 'excellent': 0.28, 'good': 0.60, 'poor': 0.10, 'error': 0.02 },
                    'poor_reception': { 'excellent': 0.05, 'good': 0.25, 'poor': 0.67, 'error': 0.03 }
                },
                'attack_probabilities': {
                    'excellent_set': { 'kill': 0.70, 'error': 0.15, 'defended': 0.15 },
                    'good_set': { 'kill': 0.55, 'error': 0.20, 'defended': 0.25 },
                    'poor_set': { 'kill': 0.30, 'error': 0.35, 'defended': 0.35 }
                },
                'block_probabilities': {
                    'power_attack': { 'stuff': 0.20, 'deflection_to_attack': 0.15, 'deflection_to_defense': 0.15, 'no_touch': 0.50 }
                },
                'dig_probabilities': {
                    'deflected_attack': { 'excellent': 0.30, 'good': 0.40, 'poor': 0.25, 'error': 0.05 }
                }
            }

        merged = {}
        # Always keep provided name (or empty string)
        merged['name'] = data.get('name', '')
        # Merge each probability section: take provided if present else default
        for key in [
            'serve_probabilities',
            'receive_probabilities',
            'set_probabilities',
            'attack_probabilities',
            'block_probabilities',
            'dig_probabilities'
        ]:
            if key in data and data[key]:
                merged[key] = data[key]
            else:
                # Use a copy to prevent accidental mutation of cached template
                merged[key] = basic_defaults.get(key, {}).copy()

        return cls(
            name=merged['name'],
            serve_probabilities=merged['serve_probabilities'],
            receive_probabilities=merged['receive_probabilities'],
            set_probabilities=merged['set_probabilities'],
            attack_probabilities=merged['attack_probabilities'],
            block_probabilities=merged['block_probabilities'],
            dig_probabilities=merged['dig_probabilities']
        )
    
    def to_dict(self) -> dict:
        """Convert team to dictionary"""
        return {
            'name': self.name,
            'serve_probabilities': self.serve_probabilities,
            'receive_probabilities': self.receive_probabilities,
            'set_probabilities': self.set_probabilities,
            'attack_probabilities': self.attack_probabilities,
            'block_probabilities': self.block_probabilities,
            'dig_probabilities': self.dig_probabilities
        }
    
    def to_yaml(self) -> str:
        """Serialize team to YAML format"""
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Team':
        """Deserialize team from YAML format"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)