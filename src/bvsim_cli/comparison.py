#!/usr/bin/env python3
"""
Team comparison functionality for multiple team matchups.
"""

import sys
import os
import random
import secrets
from typing import List, Dict, Any
from itertools import combinations

# Add bvsim_core to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_core.validation import validate_team_configuration
from bvsim_stats.inference import wilson_interval


def compare_teams(
    teams: List[Team],
    points_per_matchup: int = 1000,
    seed: int = None,
) -> Dict[str, Any]:
    """
    Compare multiple teams in round-robin format.
    
    Args:
        teams: List of teams to compare
        points_per_matchup: Number of points per team matchup
        
    Returns:
        Dictionary with comparison results
    """
    if len(teams) < 2:
        raise ValueError("Need at least 2 teams for comparison")
    if points_per_matchup <= 0:
        raise ValueError("points_per_matchup must be positive")

    for team in teams:
        errors = validate_team_configuration(team)
        if errors:
            raise ValueError(
                f"Invalid team configuration '{team.name}': " + "; ".join(errors)
            )
    
    effective_seed = seed if seed is not None else secrets.randbits(64)

    # Initialize results matrix
    results_matrix = {}
    interval_matrix = {}
    team_names = [team.name for team in teams]
    
    for team_name in team_names:
        results_matrix[team_name] = {}
        interval_matrix[team_name] = {}
    
    # Run all matchups
    matchups = list(combinations(range(len(teams)), 2))
    
    for i, j in matchups:
        team_a = teams[i]
        team_b = teams[j]
        
        # Simulate matchup
        matchup_seed = random.Random(
            effective_seed ^ (i << 32) ^ j
        )
        wins_a = 0
        for point_idx in range(points_per_matchup):
            # Alternate serving
            serving_team = "A" if point_idx % 2 == 0 else "B"
            point = simulate_point(
                team_a,
                team_b,
                serving_team=serving_team,
                seed=matchup_seed.getrandbits(64),
            )
            
            if point.winner == "A":
                wins_a += 1
        
        wins_b = points_per_matchup - wins_a
        win_rate_a = (wins_a / points_per_matchup) * 100
        win_rate_b = (wins_b / points_per_matchup) * 100
        _, lower_a, upper_a = wilson_interval(wins_a, points_per_matchup)
        
        # Store results (both directions)
        results_matrix[team_a.name][team_b.name] = win_rate_a
        results_matrix[team_b.name][team_a.name] = win_rate_b
        interval_matrix[team_a.name][team_b.name] = {
            'confidence': 0.95,
            'method': 'Wilson',
            'lower': lower_a * 100,
            'upper': upper_a * 100,
        }
        interval_matrix[team_b.name][team_a.name] = {
            'confidence': 0.95,
            'method': 'Wilson',
            'lower': (1.0 - upper_a) * 100,
            'upper': (1.0 - lower_a) * 100,
        }
    
    # Calculate overall rankings
    rankings = []
    for i, team in enumerate(teams):
        # Calculate average win rate against all other teams
        other_teams = [t for j, t in enumerate(teams) if j != i]
        if other_teams:
            total_win_rate = sum(results_matrix[team.name][other.name] for other in other_teams)
            avg_win_rate = total_win_rate / len(other_teams)
        else:
            avg_win_rate = 0
        
        rankings.append({
            'name': team.name,
            'average_win_rate': avg_win_rate
        })
    
    # Sort by average win rate (descending)
    rankings.sort(key=lambda x: x['average_win_rate'], reverse=True)
    
    return {
        'teams': team_names,
        'points_per_matchup': points_per_matchup,
        'seed': effective_seed,
        'results_matrix': results_matrix,
        'interval_matrix': interval_matrix,
        'rankings': rankings
    }


def format_comparison_text(comparison_results: Dict[str, Any]) -> str:
    """Format team comparison results as text"""
    teams = comparison_results['teams']
    matrix = comparison_results['results_matrix']
    rankings = comparison_results['rankings']
    points = comparison_results['points_per_matchup']
    
    lines = [
        f"Team Comparison Matrix ({points} points per matchup):",
        ""
    ]
    
    # Create matrix header
    header = "           "
    for team in teams:
        # Truncate long names for display
        short_name = team[:6] if len(team) > 6 else team
        header += f"| {short_name:6} "
    lines.append(header)
    
    # Create matrix rows
    for team_a in teams:
        short_name_a = team_a[:6] if len(team_a) > 6 else team_a
        row = f"{short_name_a:10} "
        
        for team_b in teams:
            if team_a == team_b:
                row += "|   -    "
            else:
                win_rate = matrix[team_a][team_b]
                row += f"| {win_rate:5.1f}% "
        
        lines.append(row)
    
    lines.extend([
        "",
        "Overall Rankings:"
    ])
    
    # Add rankings
    for i, ranking in enumerate(rankings, 1):
        lines.append(f"{i}. {ranking['name']} ({ranking['average_win_rate']:.2f}% avg)")
    
    return "\n".join(lines)