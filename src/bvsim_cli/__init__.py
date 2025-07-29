"""
BVSim CLI Library - Command-Line Interface for Beach Volleyball Simulation

This library provides high-level CLI commands for team management,
large-scale simulations, and team comparisons.
"""

__version__ = "1.0.0"

from .templates import create_team_template
from .simulation import run_large_simulation
from .comparison import compare_teams

__all__ = [
    'create_team_template',
    'run_large_simulation',
    'compare_teams'
]