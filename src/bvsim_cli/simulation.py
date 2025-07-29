#!/usr/bin/env python3
"""
Large-scale simulation runner with progress tracking.
"""

import json
import time
import sys
from typing import Optional, List, Dict, Any

# Add bvsim_core to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point


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
    
    # Initialize progress bar
    if show_progress:
        progress = ProgressBar(num_points)
    
    # Simulate points
    points = []
    for i in range(num_points):
        # Alternate serving team
        serving_team = "A" if i % 2 == 0 else "B"
        
        # Use seed-based randomization if provided
        point_seed = seed + i if seed is not None else None
        
        # Simulate point
        point = simulate_point(team_a, team_b, serving_team=serving_team, seed=point_seed)
        
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
    
    return {
        'team_a_name': team_a.name,
        'team_b_name': team_b.name,
        'total_points': num_points,
        'team_a_wins': team_a_wins,
        'team_b_wins': team_b_wins,
        'team_a_win_rate': (team_a_wins / num_points) * 100,
        'team_b_win_rate': (team_b_wins / num_points) * 100,
        'duration_seconds': duration,
        'points': points
    }


def format_simulation_summary(results: Dict[str, Any]) -> str:
    """Format simulation results as text summary"""
    lines = [
        f"Simulation Complete:",
        f"{results['team_a_name']} Wins: {results['team_a_wins']} ({results['team_a_win_rate']:.2f}%)",
        f"{results['team_b_name']} Wins: {results['team_b_wins']} ({results['team_b_win_rate']:.2f}%)",
        f"Total Duration: {results['duration_seconds']:.1f} seconds"
    ]
    return "\n".join(lines)