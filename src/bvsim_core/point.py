#!/usr/bin/env python3
"""
Point data model for beach volleyball simulation.
Represents the complete state progression of a single volleyball point.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class StateQuality(Enum):
    """Quality levels for volleyball actions"""
    EXCELLENT = "excellent"
    GOOD = "good"
    POOR = "poor"
    ERROR = "error"


@dataclass
class State:
    """
    Represents a single state in a volleyball point.
    Each state captures one action by one team with its quality outcome.
    """
    team: str  # "A" or "B"
    action: str  # "serve", "receive", "attack", "block", "dig", etc.
    quality: str  # "excellent", "good", "poor", "error", "ace", "kill", etc.


@dataclass
class Point:
    """
    Represents a complete volleyball point with all state transitions.
    Contains the serving team, winner, point type, and sequence of states.
    """
    serving_team: str  # "A" or "B"
    winner: str  # "A" or "B"
    point_type: str  # "ace", "kill", "error", "stuff", etc.
    states: List[State]  # Complete sequence of actions in the point
    
    def __post_init__(self):
        """Validate point data after initialization"""
        if self.serving_team not in ["A", "B"]:
            raise ValueError(f"Invalid serving_team: {self.serving_team}")
        if self.winner not in ["A", "B"]:
            raise ValueError(f"Invalid winner: {self.winner}")
        if not self.states:
            raise ValueError("Point must have at least one state")