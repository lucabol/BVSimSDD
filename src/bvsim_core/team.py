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
        """Create team from dictionary"""
        return cls(
            name=data.get('name', ''),
            serve_probabilities=data.get('serve_probabilities', {}),
            receive_probabilities=data.get('receive_probabilities', {}),
            set_probabilities=data.get('set_probabilities', {}),
            attack_probabilities=data.get('attack_probabilities', {}),
            block_probabilities=data.get('block_probabilities', {}),
            dig_probabilities=data.get('dig_probabilities', {})
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