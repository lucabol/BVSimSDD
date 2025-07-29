"""
BVSim Core Library - Beach Volleyball Point Simulation Engine

This library provides the core functionality for simulating individual 
beach volleyball points using conditional probability state machines.
"""

__version__ = "1.0.0"

from .team import Team
from .point import Point
from .state_machine import simulate_point
from .validation import validate_team_configuration

__all__ = [
    'Team',
    'Point', 
    'simulate_point',
    'validate_team_configuration'
]