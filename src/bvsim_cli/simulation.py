#!/usr/bin/env python3
"""
Large-scale simulation runner with progress tracking.
"""

import json
import random
import secrets
import time
import sys
from typing import Optional, List, Dict, Any

# Add bvsim_core to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_core.validation import validate_team_configuration
from bvsim_stats.inference import wilson_interval


class ProgressBar:
    """Simple progress bar for CLI"""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.width = width
        self.current = 0
    
    def update(self, count: int):
        """Update progress bar"""
        self.current = count
        if not sys.stdout.isatty():  # Don't show progress bar if output is redirected
            return
            
        filled = int(self.width * count / self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        percent = 100 * count / self.total
        
        print(f'\rProgress: [{bar}] {percent:.1f}% ({count}/{self.total})', end='', flush=True)
        
        if count >= self.total:
            print()  # New line when complete


def run_large_simulation(team_a: Team, team_b: Team, num_points: int,
                        seed: Optional[int] = None, show_progress: bool = True) -> Dict[str, Any]:
    """
    Run large-scale simulation between two teams.
    
    Args:
        team_a: Team A configuration
        team_b: Team B configuration
        num_points: Number of points to simulate
        seed: Random seed for reproducibility
        show_progress: Whether to show progress bar
        
    Returns:
        Dictionary with simulation results
    """
    start_time = time.time()
    if num_points <= 0:
        raise ValueError("num_points must be positive")

    for team in (team_a, team_b):
        errors = validate_team_configuration(team)
        if errors:
            raise ValueError(
                f"Invalid team configuration '{team.name}': " + "; ".join(errors)
            )
    
    effective_seed = seed if seed is not None else secrets.randbits(64)
    seed_stream = random.Random(effective_seed)

    # Initialize progress bar
    if show_progress:
        progress = ProgressBar(num_points)
    
    # Simulate points
    points = []
    for i in range(num_points):
        # Alternate serving team
        serving_team = "A" if i % 2 == 0 else "B"
        
        # Simulate point
        point = simulate_point(
            team_a,
            team_b,
            serving_team=serving_team,
            seed=seed_stream.getrandbits(64),
        )
        
        # Store result
        points.append({
            'serving_team': point.serving_team,
            'winner': point.winner,
            'point_type': point.point_type,
            'duration': len(point.states),
            'states': [
                {'team': s.team, 'action': s.action, 'quality': s.quality}
                for s in point.states
            ]
        })
        
        # Update progress
        if show_progress and (i + 1) % max(1, num_points // 100) == 0:
            progress.update(i + 1)
    
    # Final progress update
    if show_progress:
        progress.update(num_points)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate basic statistics
    team_a_wins = sum(1 for p in points if p['winner'] == 'A')
    team_b_wins = sum(1 for p in points if p['winner'] == 'B')
    _, team_a_lower, team_a_upper = wilson_interval(
        team_a_wins, num_points
    )
    
    return {
        'team_a_name': team_a.name,
        'team_b_name': team_b.name,
        'total_points': num_points,
        'team_a_wins': team_a_wins,
        'team_b_wins': team_b_wins,
        'team_a_win_rate': (team_a_wins / num_points) * 100,
        'team_b_win_rate': (team_b_wins / num_points) * 100,
        'team_a_win_rate_interval': {
            'confidence': 0.95,
            'method': 'Wilson',
            'lower': team_a_lower * 100,
            'upper': team_a_upper * 100,
        },
        'team_b_win_rate_interval': {
            'confidence': 0.95,
            'method': 'Wilson',
            'lower': (1.0 - team_a_upper) * 100,
            'upper': (1.0 - team_a_lower) * 100,
        },
        'duration_seconds': duration,
        'seed': effective_seed,
        'points': points
    }


def format_simulation_summary(results: Dict[str, Any]) -> str:
    """Format simulation results as text summary"""
    a_interval = results.get('team_a_win_rate_interval')
    b_interval = results.get('team_b_win_rate_interval')
    a_ci = (
        f" [95% Wilson CI: {a_interval['lower']:.2f}% - "
        f"{a_interval['upper']:.2f}%]"
        if a_interval else ""
    )
    b_ci = (
        f" [95% Wilson CI: {b_interval['lower']:.2f}% - "
        f"{b_interval['upper']:.2f}%]"
        if b_interval else ""
    )
    lines = [
        f"Simulation Complete:",
        f"{results['team_a_name']} Wins: {results['team_a_wins']} ({results['team_a_win_rate']:.2f}%){a_ci}",
        f"{results['team_b_name']} Wins: {results['team_b_wins']} ({results['team_b_win_rate']:.2f}%){b_ci}",
        f"Total Duration: {results['duration_seconds']:.1f} seconds"
    ]
    return "\n".join(lines)