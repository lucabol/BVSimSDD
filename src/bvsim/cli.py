#!/usr/bin/env python3
"""
Unified CLI for BVSim - Beach Volleyball Point Simulator
Consolidates functionality from bvsim_core, bvsim_stats, and bvsim_cli
"""

import argparse
import json
import sys
import glob
import time
import statistics
import math
import random
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import __version__
from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_stats.models import SimulationResults
from bvsim_stats.analysis import analyze_simulation_results, delta_skill_analysis, full_skill_analysis, sensitivity_analysis, multi_team_skill_analysis
from bvsim_cli.templates import get_basic_template, get_advanced_template, create_team_template
from bvsim_cli.comparison import compare_teams


# ANSI color codes for statistical analysis output
class Colors:
    RED = '\033[31m'      # Standard red
    GREEN = '\033[32m'    # Standard green  
    YELLOW = '\033[33m'   # Standard yellow
    BLUE = '\033[34m'     # Standard blue
    MAGENTA = '\033[35m'  # Standard magenta
    CYAN = '\033[36m'     # Standard cyan
    WHITE = '\033[37m'    # Standard white
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def simulate_volleyball_match(a_win_prob: float = 0.52, max_games: int = 10000, sets_to_win: int = 2, 
                             points_to_win_standard: int = 21, points_to_win_last: int = 15) -> float:
    """
    Simulate volleyball matches and return the win rate for team A.
    
    Parameters:
    a_win_prob: Probability of team A winning a point
    max_games: Number of matches to simulate
    sets_to_win: Number of sets to win the match
    points_to_win_standard: Points to win a set (unless deciding set)
    points_to_win_last: Points to win the deciding set
    
    Returns:
    Match win rate for team A
    """
    a_wins = b_wins = 0

    while a_wins + b_wins < max_games:
        a_sets = b_sets = 0

        while a_sets < sets_to_win and b_sets < sets_to_win:
            a_points = b_points = 0
            points_to_win = points_to_win_standard if a_sets + b_sets < 2 * sets_to_win - 1 else points_to_win_last

            while not (a_points >= points_to_win and a_points - b_points >= 2) and not (b_points >= points_to_win and b_points - a_points >= 2):
                a_win_point = random.random() < a_win_prob
                if a_win_point:
                    a_points += 1
                else:
                    b_points += 1

                if a_points >= points_to_win and a_points - b_points >= 2:
                    a_sets += 1
                elif b_points >= points_to_win and b_points - a_points >= 2:
                    b_sets += 1

                if a_sets == sets_to_win:
                    a_wins += 1
                    break
                elif b_sets == sets_to_win:
                    b_wins += 1
                    break
            
            if a_sets == sets_to_win or b_sets == sets_to_win:
                break

    return a_wins / (a_wins + b_wins) if (a_wins + b_wins) > 0 else 0.5


def point_to_match_impact(point_improvement: float, baseline_point_rate: float = 0.5) -> float:
    """Convert point win rate improvement to match win rate improvement."""
    baseline_match_rate = simulate_volleyball_match(baseline_point_rate)
    improved_match_rate = simulate_volleyball_match(baseline_point_rate + point_improvement / 100.0)
    return (improved_match_rate - baseline_match_rate) * 100.0


def calculate_confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float, float]:
    """Calculate mean and confidence interval for a list of values."""
    if len(values) < 2:
        return values[0] if values else 0.0, 0.0, 0.0
    
    n = len(values)
    mean = statistics.mean(values)
    
    if n == 2:
        # For n=2, use the range as a simple interval
        half_range = abs(values[1] - values[0]) / 2
        return mean, mean - half_range, mean + half_range
    
    stdev = statistics.stdev(values)
    
    # Choose appropriate distribution based on sample size
    if n >= 30:
        # Large sample: use normal distribution (z-distribution)
        z_critical = 1.96 if confidence >= 0.95 else 1.645  # 95% or 90%
        margin_of_error = z_critical * (stdev / math.sqrt(n))
    else:
        # Small sample: use t-distribution
        # t-critical values for 95% confidence interval
        t_critical_map = {3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262,
                         11: 2.228, 12: 2.201, 13: 2.179, 14: 2.160, 15: 2.145, 20: 2.086, 25: 2.064, 29: 2.045}
        t_critical = t_critical_map.get(n, 2.045)  # Default to n=29 value for n>29 but <30
        margin_of_error = t_critical * (stdev / math.sqrt(n))
    
    return mean, mean - margin_of_error, mean + margin_of_error


def format_parameter_name(param_name: str) -> str:
    """Format parameter names for better readability."""
    # Apply the same abbreviations as in the CLI
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_defense", "block_probabilities.power_attack.deflection_to_d")
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_attack", "block_probabilities.power_attack.deflection_to_a")
    
    # Truncate if too long
    if len(param_name) > 50:
        return param_name[:47] + "..."
    return param_name


def run_single_skills_analysis(team: Team, opponent: Team, change_value: float, points_per_test: int, parallel: bool, run_number: int) -> Tuple[Dict[str, Any], float]:
    """Run a single skills analysis and return the results and duration."""
    start_time = time.time()
    
    results = full_skill_analysis(
        team=team,
        opponent=opponent,
        change_value=change_value,
        points_per_test=points_per_test,
        parallel=parallel
    )
    
    duration = time.time() - start_time
    return results, duration


def run_single_custom_analysis(team: Team, opponent: Team, custom_team_files: List[str], points_per_test: int, run_number: int) -> Tuple[Dict[str, Any], float]:
    """Run a single custom scenario analysis (team variant files) and return the results and duration."""
    start_time = time.time()

    results = multi_team_skill_analysis(
        base_team=team,
        opponent=opponent,
        team_variant_files=custom_team_files,
        points_per_test=points_per_test
    )

    duration = time.time() - start_time
    return results, duration


def print_custom_statistical_analysis(all_results: List[Dict[str, Any]], all_durations: List[float], delta_files: List[str], points: int):
    """Print statistical analysis of custom scenario impacts across multiple runs with confidence intervals."""
    
    num_runs = len(all_results)
    avg_duration = statistics.mean(all_durations)
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}CUSTOM SCENARIOS STATISTICAL ANALYSIS{Colors.END}")
    print(f"Number of Runs: {num_runs} | Average Duration: {avg_duration:.2f}s")
    
    # Extract baseline win rates from all runs
    baseline_rates = [result.get("baseline_win_rate", 0) for result in all_results]
    baseline_mean, baseline_lower, baseline_upper = calculate_confidence_interval(baseline_rates)
    
    print(f"Baseline Win Rate: {baseline_mean:.1f}% [95% CI: {baseline_lower:.1f}% - {baseline_upper:.1f}%]")
    print(f"Testing {len(delta_files)} custom scenarios ({points:,} points each)")
    print("=" * 140)
    
    # Collect scenario data across runs
    scenario_data = {}
    
    # Get scenario names from first run
    first_run_files = all_results[0].get("file_results", {})
    
    for scenario_name in first_run_files.keys():
        improvements = []
        win_rates = []
        
        # Collect data from all runs for this scenario
        for result in all_results:
            file_results = result.get("file_results", {})
            if scenario_name in file_results:
                improvement = file_results[scenario_name].get("improvement", 0)
                win_rate = file_results[scenario_name].get("win_rate", 0)
                improvements.append(improvement)
                win_rates.append(win_rate)
        
        if improvements:
            # Point impact statistics
            point_mean, point_lower, point_upper = calculate_confidence_interval(improvements)
            
            # Calculate match win rate impacts
            match_improvements = []
            for point_improvement in improvements:
                match_impact = point_to_match_impact(point_improvement)
                match_improvements.append(match_impact)
            
            # Match impact statistics
            match_mean, match_lower, match_upper = calculate_confidence_interval(match_improvements)
            
            # Check for statistical significance
            is_significant = (match_lower > 0 and match_upper > 0) or (match_lower < 0 and match_upper < 0)
            
            scenario_data[scenario_name] = {
                'scenario': scenario_name,
                'point_mean': point_mean,
                'point_lower': point_lower,
                'point_upper': point_upper,
                'match_mean': match_mean,
                'match_lower': match_lower,
                'match_upper': match_upper,
                'is_significant': is_significant,
                'num_runs': len(improvements)
            }
    
    # Sort by match impact (most positive first)
    scenario_comparisons = list(scenario_data.values())
    scenario_comparisons.sort(key=lambda x: x['match_mean'], reverse=True)
    
    # Print table header
    print(f"{Colors.BOLD}Scenario File                                      Point Impact  Match Impact  95% Match CI              Significant{Colors.END}")
    print(f"{Colors.BOLD}                                                   (% improve)   (% improve)   (Lower - Upper)           (Yes/No)   {Colors.END}")
    print("-" * 140)
    
    # Print each scenario with its confidence interval
    significant_scenarios = []
    for i, scenario in enumerate(scenario_comparisons):
        scenario_name = scenario['scenario']
        point_mean = scenario['point_mean']
        point_lower = scenario['point_lower']
        point_upper = scenario['point_upper']
        match_mean = scenario['match_mean']
        match_lower = scenario['match_lower'] 
        match_upper = scenario['match_upper']
        is_sig = scenario['is_significant']
        
        # Color coding based on statistical significance
        if is_sig:
            if match_mean > 0:
                color = Colors.GREEN
            else:
                color = Colors.RED
            significant_scenarios.append(scenario)
        else:
            color = Colors.YELLOW
        
        # Format significance indicator
        sig_text = "YES" if is_sig else "No"
        
        # Format scenario name (truncate if too long)
        display_name = scenario_name
        if len(display_name) > 50:
            display_name = display_name[:47] + "..."
        
        print(f"{color}{display_name:<50} {point_mean:+6.2f}%     {match_mean:+6.2f}%     [{match_lower:+6.2f}% - {match_upper:+6.2f}%]       {sig_text:<3}{Colors.END}")
    
    print("-" * 140)
    
    # Visual confidence interval chart
    print(f"\n{Colors.BOLD}MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Scenarios):{Colors.END}")
    print("Match % │")
    
    # Calculate chart scale using match impact values
    all_values = []
    for scenario in scenario_comparisons:
        all_values.extend([scenario['match_lower'], scenario['match_mean'], scenario['match_upper']])
    
    if all_values:
        chart_min = min(all_values)
        chart_max = max(all_values)
        
        # Always ensure 0% is visible in the chart
        chart_min = min(chart_min, 0.0)
        chart_max = max(chart_max, 0.0)
        
        chart_range = chart_max - chart_min
        
        # Add padding
        padding = chart_range * 0.1 if chart_range > 0 else 1.0
        chart_min -= padding
        chart_max += padding
        chart_range = chart_max - chart_min
        
        # Chart width (characters)
        chart_width = 80
        
        # Draw each scenario's confidence interval
        for scenario in scenario_comparisons:
            scenario_name = scenario['scenario']
            match_mean = scenario['match_mean']
            match_lower = scenario['match_lower']
            match_upper = scenario['match_upper']
            is_sig = scenario['is_significant']
            
            # Calculate positions
            if chart_range > 0:
                mean_pos = int((match_mean - chart_min) / chart_range * chart_width)
                lower_pos = int((match_lower - chart_min) / chart_range * chart_width)
                upper_pos = int((match_upper - chart_min) / chart_range * chart_width)
                zero_pos = int((0 - chart_min) / chart_range * chart_width) if chart_min <= 0 <= chart_max else -1
            else:
                mean_pos = chart_width // 2
                lower_pos = chart_width // 2
                upper_pos = chart_width // 2
                zero_pos = chart_width // 2
            
            # Build the visual line
            line = [' '] * chart_width
            
            # Draw confidence interval bar
            for i in range(max(0, lower_pos), min(chart_width, upper_pos + 1)):
                line[i] = '─'
            
            # Draw zero line if visible
            if 0 <= zero_pos < chart_width:
                line[zero_pos] = '┊'
            
            # Draw mean point
            if 0 <= mean_pos < chart_width:
                if is_sig:
                    line[mean_pos] = '●'  # Solid dot for significant
                else:
                    line[mean_pos] = '○'  # Hollow dot for non-significant
            
            # Color the entire line
            if is_sig:
                color = Colors.GREEN if match_mean > 0 else Colors.RED
            else:
                color = Colors.YELLOW
            
            print(f"         │ {color}{''.join(line)}{Colors.END} {scenario_name}")
        
        # Add scale markers (similar to previous function)
        print(f"         │{'─' * chart_width}")
        scale_line = ' ' * 9 + '│'
        
        markers = []
        if chart_range > 0:
            markers.append((0, f"{chart_min:+.1f}%"))
            if chart_min <= 0 <= chart_max:
                zero_pos = int((0 - chart_min) / chart_range * chart_width)
                markers.append((zero_pos, "0%"))
            markers.append((chart_width-1, f"{chart_max:+.1f}%"))
        
        markers.sort()
        scale_positions = [' '] * chart_width
        
        for pos, label in markers:
            if 0 <= pos < chart_width:
                start_pos = max(0, pos - len(label)//2)
                end_pos = min(chart_width, start_pos + len(label))
                
                overlap = False
                for i in range(start_pos, end_pos):
                    if i < len(scale_positions) and scale_positions[i] != ' ':
                        overlap = True
                        break
                
                if not overlap and end_pos - start_pos == len(label):
                    for i, char in enumerate(label):
                        if start_pos + i < chart_width:
                            scale_positions[start_pos + i] = char
        
        scale_line += ''.join(scale_positions)
        print(scale_line)
        
        # Legend
        print(f"\nLegend: {Colors.GREEN}●{Colors.END} Significant positive  {Colors.RED}●{Colors.END} Significant negative  {Colors.YELLOW}○{Colors.END} Non-significant  ┊ Zero line")
    
    # Summary statistics
    total_scenarios = len(scenario_comparisons)
    significant_positive = len([s for s in significant_scenarios if s['match_mean'] > 0])
    significant_negative = len([s for s in significant_scenarios if s['match_mean'] < 0])
    
    print(f"\n{Colors.BOLD}STATISTICAL SUMMARY:{Colors.END}")
    print(f"Total scenarios analyzed: {total_scenarios}")
    print(f"Statistically significant positive impacts: {significant_positive}")
    print(f"Statistically significant negative impacts: {significant_negative}")
    
    if scenario_comparisons:
        best_scenario = scenario_comparisons[0]
        print(f"Best scenario: {Colors.GREEN}{best_scenario['scenario']}{Colors.END}")
        print(f"Point Impact: {Colors.GREEN}{best_scenario['point_mean']:+5.2f}% [{best_scenario['point_lower']:+5.2f}% - {best_scenario['point_upper']:+5.2f}%]{Colors.END}")
        print(f"Match Impact: {Colors.GREEN}{best_scenario['match_mean']:+5.2f}% [{best_scenario['match_lower']:+5.2f}% - {best_scenario['match_upper']:+5.2f}%]{Colors.END}")
    
    # Show significant scenarios for training focus
    if significant_scenarios:
        print(f"\n{Colors.BOLD}RECOMMENDED TRAINING SCENARIOS:{Colors.END}")
        for i, scenario in enumerate(significant_scenarios[:5]):  # Top 5
            scenario_name = scenario['scenario']
            point_mean = scenario['point_mean']
            match_mean = scenario['match_mean']
            point_lower = scenario['point_lower']
            point_upper = scenario['point_upper']
            match_lower = scenario['match_lower']
            match_upper = scenario['match_upper']
            
            color = Colors.GREEN if match_mean > 0 else Colors.RED
            print(f"{i+1}. {color}{scenario_name}:{Colors.END}")
            print(f"   {color}Point: {point_mean:+5.2f}% [{point_lower:+5.2f}% - {point_upper:+5.2f}%] | Match: {match_mean:+5.2f}% [{match_lower:+5.2f}% - {match_upper:+5.2f}%]{Colors.END}")


def print_skills_statistical_analysis(all_results: List[Dict[str, Any]], all_durations: List[float], change_value: float, points: int):
    """Print a statistical analysis of skill impacts across multiple runs with confidence intervals."""
    
    num_runs = len(all_results)
    avg_duration = statistics.mean(all_durations)
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}BVSIM SKILLS STATISTICAL ANALYSIS{Colors.END}")
    print(f"Number of Runs: {num_runs} | Average Duration: {avg_duration:.2f}s")
    
    # Extract baseline win rates from all runs
    baseline_rates = [result.get("baseline_win_rate", 0) for result in all_results]
    baseline_mean, baseline_lower, baseline_upper = calculate_confidence_interval(baseline_rates)
    
    print(f"Baseline Win Rate: {baseline_mean:.1f}% [95% CI: {baseline_lower:.1f}% - {baseline_upper:.1f}%]")
    change_pct = change_value * 100
    print(f"Testing {change_pct:+.1f}% improvement on {all_results[0]['total_parameters']} parameters ({points:,} points each)")
    print("=" * 140)
    
    # Collect all skill improvement data across runs
    skill_data = {}
    
    # Get all parameter names from first run
    first_run_params = all_results[0].get("parameter_improvements", {})
    
    for param_name in first_run_params.keys():
        improvements = []
        
        # Collect improvement values from all runs for this parameter
        for result in all_results:
            params = result.get("parameter_improvements", {})
            if param_name in params:
                improvement = params[param_name].get("improvement", 0)
                improvements.append(improvement)
        
        if improvements:
            mean, lower_ci, upper_ci = calculate_confidence_interval(improvements)
            
            # Calculate match win rate impacts for all point improvements
            match_improvements = []
            for point_improvement in improvements:
                match_impact = point_to_match_impact(point_improvement)
                match_improvements.append(match_impact)
            
            # Calculate match impact statistics
            match_mean, match_lower, match_upper = calculate_confidence_interval(match_improvements)
            
            # Check for statistical significance based on match impact CI
            is_significant = (match_lower > 0 and match_upper > 0) or (match_lower < 0 and match_upper < 0)
            
            skill_data[param_name] = {
                'parameter': param_name,
                'mean_improvement': mean,
                'lower_ci': lower_ci,
                'upper_ci': upper_ci,
                'match_mean': match_mean,
                'match_lower': match_lower,
                'match_upper': match_upper,
                'is_significant': is_significant,
                'num_runs': len(improvements)
            }
    
    # Sort by mean improvement (most positive impact first, then most negative)
    skill_comparisons = list(skill_data.values())
    skill_comparisons.sort(key=lambda x: x['mean_improvement'], reverse=True)
    
    # Print table header
    print(f"{Colors.BOLD}Skill Parameter                                    Point Impact  Match Impact  95% Match CI              Significant{Colors.END}")
    print(f"{Colors.BOLD}                                                   (% improve)   (% improve)   (Lower - Upper)           (Yes/No)   {Colors.END}")
    print("-" * 140)
    
    # Print each skill with its confidence interval
    significant_skills = []
    for i, skill in enumerate(skill_comparisons):
        param_name = skill['parameter']
        mean_imp = skill['mean_improvement']
        lower_ci = skill['lower_ci']
        upper_ci = skill['upper_ci']
        match_mean = skill['match_mean']
        match_lower = skill['match_lower'] 
        match_upper = skill['match_upper']
        is_sig = skill['is_significant']
        
        # Color coding based on statistical significance
        if is_sig:
            # Statistically significant - use green for positive, red for negative
            if mean_imp > 0:
                color = Colors.GREEN
            else:
                color = Colors.RED
            significant_skills.append(skill)
        else:
            # Not statistically significant - use yellow (regardless of direction)
            color = Colors.YELLOW
        
        # Format significance indicator
        sig_text = "YES" if is_sig else "No"
        
        # Format parameter name (truncate if too long)
        display_name = format_parameter_name(param_name)
        
        print(f"{color}{display_name:<50} {mean_imp:+6.2f}%     {match_mean:+6.2f}%     [{match_lower:+6.2f}% - {match_upper:+6.2f}%]       {sig_text:<3}{Colors.END}")
    
    print("-" * 140)
    
    # Visual confidence interval chart
    print(f"\n{Colors.BOLD}MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Skills):{Colors.END}")
    print("Match % │")
    
    # Use all skills, already sorted by mean improvement
    chart_skills = skill_comparisons
    
    # Calculate chart scale using match impact values
    all_values = []
    for skill in chart_skills:
        all_values.extend([skill['match_lower'], skill['match_mean'], skill['match_upper']])
    
    if all_values:
        chart_min = min(all_values)
        chart_max = max(all_values)
        
        # Always ensure 0% is visible in the chart
        chart_min = min(chart_min, 0.0)
        chart_max = max(chart_max, 0.0)
        
        chart_range = chart_max - chart_min
        
        # Add padding
        padding = chart_range * 0.1 if chart_range > 0 else 1.0
        chart_min -= padding
        chart_max += padding
        chart_range = chart_max - chart_min
        
        # Chart width (characters)
        chart_width = 80
        
        # Draw each skill's confidence interval
        for skill in chart_skills:
            param_name = format_parameter_name(skill['parameter'])
            mean_imp = skill['mean_improvement']  # Keep for significance color coding
            match_mean = skill['match_mean']
            match_lower = skill['match_lower']
            match_upper = skill['match_upper']
            is_sig = skill['is_significant']
            
            # Calculate positions (0 to chart_width) using match values
            if chart_range > 0:
                mean_pos = int((match_mean - chart_min) / chart_range * chart_width)
                lower_pos = int((match_lower - chart_min) / chart_range * chart_width)
                upper_pos = int((match_upper - chart_min) / chart_range * chart_width)
                zero_pos = int((0 - chart_min) / chart_range * chart_width) if chart_min <= 0 <= chart_max else -1
            else:
                mean_pos = chart_width // 2
                lower_pos = chart_width // 2
                upper_pos = chart_width // 2
                zero_pos = chart_width // 2
            
            # Build the visual line
            line = [' '] * chart_width
            
            # Draw confidence interval bar
            for i in range(max(0, lower_pos), min(chart_width, upper_pos + 1)):
                line[i] = '─'
            
            # Draw zero line if visible
            if 0 <= zero_pos < chart_width:
                line[zero_pos] = '┊'
            
            # Draw mean point (overwrites other symbols)
            if 0 <= mean_pos < chart_width:
                if is_sig:
                    line[mean_pos] = '●'  # Solid dot for significant
                else:
                    line[mean_pos] = '○'  # Hollow dot for non-significant
            
            # Color the entire line
            if is_sig:
                color = Colors.GREEN if mean_imp > 0 else Colors.RED
            else:
                color = Colors.YELLOW
            
            # Use full parameter name (no truncation)
            display_name = param_name
            
            print(f"         │ {color}{''.join(line)}{Colors.END} {display_name}")
        
        # Add scale markers
        print(f"         │{'─' * chart_width}")
        scale_line = ' ' * 9 + '│'
        
        # Add scale markers at key points
        markers = []
        if chart_range > 0:
            # Left end
            markers.append((0, f"{chart_min:+.1f}%"))
            # Zero line if visible
            if chart_min <= 0 <= chart_max:
                zero_pos = int((0 - chart_min) / chart_range * chart_width)
                markers.append((zero_pos, "0%"))
            # Additional markers for better readability
            quarter_pos = int(chart_width * 0.25)
            three_quarter_pos = int(chart_width * 0.75)
            quarter_val = chart_min + chart_range * 0.25
            three_quarter_val = chart_min + chart_range * 0.75
            markers.append((quarter_pos, f"{quarter_val:+.1f}%"))
            markers.append((three_quarter_pos, f"{three_quarter_val:+.1f}%"))
            # Right end
            markers.append((chart_width-1, f"{chart_max:+.1f}%"))
        
        # Sort markers by position to avoid overlap
        markers.sort()
        scale_positions = [' '] * chart_width
        
        for pos, label in markers:
            if 0 <= pos < chart_width:
                # Try to center the label on the position, avoid overlap
                start_pos = max(0, pos - len(label)//2)
                end_pos = min(chart_width, start_pos + len(label))
                
                # Check for overlap with existing markers
                overlap = False
                for i in range(start_pos, end_pos):
                    if i < len(scale_positions) and scale_positions[i] != ' ':
                        overlap = True
                        break
                
                if not overlap and end_pos - start_pos == len(label):
                    for i, char in enumerate(label):
                        if start_pos + i < chart_width:
                            scale_positions[start_pos + i] = char
        
        scale_line += ''.join(scale_positions)
        print(scale_line)
        
        # Legend
        print(f"\nLegend: {Colors.GREEN}●{Colors.END} Significant positive  {Colors.RED}●{Colors.END} Significant negative  {Colors.YELLOW}○{Colors.END} Non-significant  ┊ Zero line")
    
    # Summary statistics
    total_skills = len(skill_comparisons)
    significant_positive = len([s for s in significant_skills if s['mean_improvement'] > 0])
    significant_negative = len([s for s in significant_skills if s['mean_improvement'] < 0])
    high_impact_skills = len([s for s in significant_skills if abs(s['mean_improvement']) > 1.0])
    
    print(f"\n{Colors.BOLD}STATISTICAL SUMMARY:{Colors.END}")
    print(f"Total skills analyzed: {total_skills}")
    print(f"Statistically significant positive impacts: {significant_positive}")
    print(f"Statistically significant negative impacts: {significant_negative}")  
    print(f"High-impact skills (>1% improvement): {high_impact_skills}")
    
    if skill_comparisons:
        top_skill = skill_comparisons[0]
        print(f"Most impactful skill: {Colors.GREEN}{format_parameter_name(top_skill['parameter'])}{Colors.END}")
        print(f"Point Impact: {Colors.GREEN}{top_skill['mean_improvement']:+5.2f}% [{top_skill['lower_ci']:+5.2f}% - {top_skill['upper_ci']:+5.2f}%]{Colors.END}")
        print(f"Match Impact: {Colors.GREEN}{top_skill['match_mean']:+5.2f}% [{top_skill['match_lower']:+5.2f}% - {top_skill['match_upper']:+5.2f}%]{Colors.END}")
    
    # Show only statistically significant high-impact skills
    if significant_skills:
        print(f"\n{Colors.BOLD}STATISTICALLY SIGNIFICANT SKILLS (FOCUS TRAINING HERE):{Colors.END}")
        high_impact_significant = [s for s in significant_skills if abs(s['mean_improvement']) > 0.5][:10]
        for i, skill in enumerate(high_impact_significant):
            param_name = skill['parameter']
            mean_imp = skill['mean_improvement']
            match_mean = skill['match_mean']
            lower_ci = skill['lower_ci']
            upper_ci = skill['upper_ci']
            match_lower = skill['match_lower']
            match_upper = skill['match_upper']
            
            color = Colors.GREEN if mean_imp > 0 else Colors.RED
            print(f"{i+1:2d}. {color}{format_parameter_name(param_name)}:{Colors.END}")
            print(f"    {color}Point: {mean_imp:+5.2f}% [{lower_ci:+5.2f}% - {upper_ci:+5.2f}%] | Match: {match_mean:+5.2f}% [{match_lower:+5.2f}% - {match_upper:+5.2f}%]{Colors.END}")


def auto_discover_teams() -> List[str]:
    """Auto-discover team YAML files in current directory"""
    team_files = []
    patterns = ['team_*.yaml', 'team_*.yml', '*.yaml', '*.yml']
    
    for pattern in patterns:
        files = glob.glob(pattern)
        team_files.extend([f for f in files if f not in team_files])
    
    # Filter to only valid team files with complete probability structures
    valid_teams = []
    for file in team_files:
        try:
            team = Team.from_yaml_file(file)
            # Validate that the team has complete probability distributions
            if (team.serve_probabilities and 
                team.receive_probabilities and 
                team.attack_probabilities and 
                team.set_probabilities and
                team.block_probabilities and 
                team.dig_probabilities):
                valid_teams.append(file)
        except:
            continue
            
    return valid_teams


def auto_discover_results() -> List[str]:
    """Auto-discover simulation result JSON files"""
    result_files = glob.glob('*.json')
    valid_results = []
    
    for file in result_files:
        try:
            SimulationResults.from_json_file(file)
            valid_results.append(file)
        except:
            continue
            
    return valid_results


def get_team_or_default(team_arg: Optional[str], default_name: str = "Default Team") -> Team:
    """Get team from argument or create default"""
    if team_arg:
        if Path(team_arg + '.yaml').exists():
            return Team.from_yaml_file(team_arg + '.yaml')
        elif Path(team_arg).exists():
            return Team.from_yaml_file(team_arg)
        else:
            raise FileNotFoundError(f"Team file not found: {team_arg}")
    else:
        # Use basic template as default
        return Team.from_dict(get_basic_template(default_name))


def cmd_skills(args):
    """Handle 'bvsim skills' command - skill impact analysis"""
    try:
        # Determine teams
        if len(args.teams) == 0:
            # No teams specified - use defaults
            team = Team.from_dict(get_basic_template("Default Team"))
            opponent = team
        elif len(args.teams) == 1:
            # One team specified - vs itself
            team = get_team_or_default(args.teams[0])
            opponent = team
        elif len(args.teams) == 2:
            # Two teams specified
            team = get_team_or_default(args.teams[0])
            opponent = get_team_or_default(args.teams[1])
        else:
            print("Error: skills command accepts 0-2 teams", file=sys.stderr)
            return 1
        
        # ALWAYS default to 200k points, 5% improvement, 5 runs unless explicitly overridden
        # Determine points - default is ALWAYS 200k unless explicitly overridden
        if args.quick:
            points = 10000
        elif args.accurate:
            points = 200000
        else:
            points = args.points or 200000  # Default to high precision ALWAYS
        
        # Determine improvement - default is ALWAYS 5% unless explicitly overridden  
        change_value = args.improve or 0.05
        if isinstance(change_value, str):
            if change_value.endswith('%'):
                change_value = float(change_value[:-1]) / 100.0
            else:
                change_value = float(change_value)
        
        # Determine runs - default is ALWAYS 5 unless explicitly overridden
        num_runs = args.runs or 5
        
        # Parse custom comma-separated list into array if provided
        custom_files = None
        if args.custom:
            raw = args.custom.strip()
            if raw:
                custom_files = [f.strip() for f in raw.split(',') if f.strip()]
        # Always use statistical analysis mode including for custom analysis
        if custom_files:
            # Custom scenarios statistical analysis
            points_desc = f"{points//1000}k points each" if points >= 1000 else f"{points} points each"
            
            print(f"{Colors.BOLD}Custom Scenarios Statistical Analysis{Colors.END}")
            print(f"Running {num_runs} scenario analyses ({points_desc}) for statistical comparison...")
            
            total_start_time = time.time()
            
            # Run multiple custom analyses in parallel
            try:
                print(f"{Colors.CYAN}Starting {num_runs} custom scenario analyses in parallel...{Colors.END}")
                
                # Create a thread pool to run all analyses concurrently
                max_workers = min(num_runs, 8)  # Cap at 8 concurrent analyses
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks
                    futures = [
                        executor.submit(run_single_custom_analysis, team, opponent, custom_files, points, i+1)
                        for i in range(num_runs)
                    ]
                    
                    # Wait for all to complete and collect results
                    all_results = []
                    all_durations = []
                    completed_count = 0
                    
                    for future in as_completed(futures):
                        completed_count += 1
                        run_data, duration = future.result()
                        all_results.append(run_data)
                        all_durations.append(duration)
                        print(f"\r{Colors.GREEN}✓ Analysis {completed_count} completed in {duration:.2f}s ({completed_count}/{num_runs}){Colors.END}", end="", flush=True)
                    
                    print()  # Final newline after all analyses complete
                
                # Display statistical analysis
                if args.format == 'json':
                    # For JSON output, combine all results
                    combined_results = {
                        "custom_statistical_analysis": True,
                        "num_runs": num_runs,
                        "scenario_files": custom_files,
                        "points_per_test": points,
                        "individual_runs": all_results,
                        "execution_summary": {
                            "total_duration": time.time() - total_start_time,
                            "average_duration": statistics.mean(all_durations),
                            "runs_completed": num_runs
                        }
                    }
                    print(json.dumps(combined_results, indent=2))
                else:
                    print_custom_statistical_analysis(all_results, all_durations, custom_files, points)
                    
                    total_duration = time.time() - total_start_time
                    avg_duration = statistics.mean(all_durations)
                    
                    print(f"\n{Colors.BOLD}EXECUTION SUMMARY:{Colors.END}")
                    print(f"Total script execution time: {Colors.GREEN}{total_duration:.2f} seconds{Colors.END}")
                    print(f"Average analysis time: {Colors.GREEN}{avg_duration:.2f} seconds{Colors.END}")
                    print(f"Number of runs completed: {Colors.GREEN}{num_runs}{Colors.END}")
                    
                    # Statistical note
                    print(f"\n{Colors.YELLOW}Statistical Analysis: Confidence intervals show the range where the true scenario impact likely falls.")
                    print(f"Scenarios marked 'YES' have statistically significant impacts (confidence interval doesn't include 0).") 
                    print(f"Focus training on scenarios with significant positive impacts.{Colors.END}")
                
            except KeyboardInterrupt:
                print(f"\n{Colors.RED}Custom scenario analysis interrupted by user{Colors.END}")
                return 130
            except Exception as e:
                print(f"\n{Colors.RED}Error in custom scenario analysis: {e}{Colors.END}")
                return 1
        else:
            # ALWAYS use statistical analysis mode (with default 5 runs)
            points_desc = f"{points//1000}k points each" if points >= 1000 else f"{points} points each"
            
            print(f"{Colors.BOLD}BVSim Skills Statistical Analysis{Colors.END}")
            print(f"Running {num_runs} skills analyses ({points_desc}) for statistical comparison...")
            
            total_start_time = time.time()
            
            # Run multiple skills analyses in parallel
            try:
                print(f"{Colors.CYAN}Starting {num_runs} analyses in parallel...{Colors.END}")
                
                # Create a thread pool to run all analyses concurrently
                max_workers = min(num_runs, 8)  # Cap at 8 concurrent analyses
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks
                    futures = [
                        executor.submit(run_single_skills_analysis, team, opponent, change_value, points, not args.no_parallel, i+1)
                        for i in range(num_runs)
                    ]
                    
                    # Wait for all to complete and collect results
                    all_results = []
                    all_durations = []
                    completed_count = 0
                    
                    for future in as_completed(futures):
                        completed_count += 1
                        run_data, duration = future.result()
                        all_results.append(run_data)
                        all_durations.append(duration)
                        print(f"\r{Colors.GREEN}✓ Analysis {completed_count} completed in {duration:.2f}s ({completed_count}/{num_runs}){Colors.END}", end="", flush=True)
                    
                    print()  # Final newline after all analyses complete
                
                # Display statistical analysis
                if args.format == 'json':
                    # For JSON output, combine all results
                    combined_results = {
                        "statistical_analysis": True,
                        "num_runs": num_runs,
                        "change_value": change_value,
                        "points_per_test": points,
                        "individual_runs": all_results,
                        "execution_summary": {
                            "total_duration": time.time() - total_start_time,
                            "average_duration": statistics.mean(all_durations),
                            "runs_completed": num_runs
                        }
                    }
                    print(json.dumps(combined_results, indent=2))
                else:
                    print_skills_statistical_analysis(all_results, all_durations, change_value, points)
                    
                    total_duration = time.time() - total_start_time
                    avg_duration = statistics.mean(all_durations)
                    
                    print(f"\n{Colors.BOLD}EXECUTION SUMMARY:{Colors.END}")
                    print(f"Total script execution time: {Colors.GREEN}{total_duration:.2f} seconds{Colors.END}")
                    print(f"Average analysis time: {Colors.GREEN}{avg_duration:.2f} seconds{Colors.END}")
                    print(f"Number of runs completed: {Colors.GREEN}{num_runs}{Colors.END}")
                    
                    # Statistical note
                    print(f"\n{Colors.YELLOW}Statistical Analysis: Confidence intervals show the range where the true skill impact likely falls.")
                    print(f"Skills marked 'YES' have statistically significant impacts (confidence interval doesn't include 0).")
                    print(f"Focus training on skills with significant positive impacts and wide confidence intervals.{Colors.END}")
                
            except KeyboardInterrupt:
                print(f"\n{Colors.RED}Statistical analysis interrupted by user{Colors.END}")
                return 130
            except Exception as e:
                print(f"\n{Colors.RED}Error in statistical analysis: {e}{Colors.END}")
                return 1
        
        return 0
        
    except FileNotFoundError as e:
        print("Team file not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Error in skill analysis", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_compare(args):
    """Handle 'bvsim compare' command - team comparisons"""
    try:
        # Auto-discover teams if none specified
        if not args.teams:
            teams = auto_discover_teams()
            if len(teams) < 2:
                print("Creating default teams for comparison...")
                # Create some default teams
                team_a = Team.from_dict(get_basic_template("Team A"))
                team_b = Team.from_dict(get_advanced_template("Team B"))
                teams = [team_a, team_b]
                team_names = ["Team A", "Team B"]
            else:
                teams = [Team.from_yaml_file(f) for f in teams[:3]]  # Max 3 teams
                team_names = [t.name for t in teams]
        else:
            teams = [get_team_or_default(t) for t in args.teams]
            team_names = [t.name for t in teams]
        
        if len(teams) < 2:
            print("Error: Need at least 2 teams to compare", file=sys.stderr)
            return 1
        
        # Determine points based on speed options
        if args.quick:
            points = 10000
        elif args.accurate:
            points = 200000
        else:
            points = args.points or 50000
        
        # Run comparisons using existing compare_teams functionality
        results = compare_teams(teams, points_per_matchup=points)
        
        if args.format == 'json':
            print(json.dumps(results, indent=2))
        else:
            # Use the existing text formatting function
            from bvsim_cli.comparison import format_comparison_text
            output = format_comparison_text(results)
            print(output)
        
        return 0
        
    except Exception as e:
        print("Error in team comparison", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_simulate(args):
    """Handle 'bvsim simulate' command - point simulation"""
    try:
        # Determine teams
        if len(args.teams) == 0:
            team_a = Team.from_dict(get_basic_template("Team A"))
            team_b = Team.from_dict(get_basic_template("Team B"))
        elif len(args.teams) == 1:
            team_a = get_team_or_default(args.teams[0])
            team_b = Team.from_dict(get_basic_template("Opponent"))
        elif len(args.teams) == 2:
            team_a = get_team_or_default(args.teams[0])
            team_b = get_team_or_default(args.teams[1])
        else:
            print("Error: simulate command accepts 0-2 teams", file=sys.stderr)
            return 1
        
        # Determine points based on speed options
        if args.quick:
            points = 10000
        elif args.accurate:
            points = 200000
        else:
            points = args.points or 100000
        
        output_file = args.output or "simulation_results.json"
        
        print(f"Simulating {points:,} points: {team_a.name} vs {team_b.name}")
        if args.progress:
            print("Progress: ", end="", flush=True)
        
        # Run simulation
        from bvsim_cli.simulation import run_large_simulation
        sim_data = run_large_simulation(
            team_a=team_a,
            team_b=team_b,
            num_points=points,
            seed=args.seed,
            show_progress=args.progress
        )
        
        # Convert to SimulationResults format
        from bvsim_stats.models import PointResult
        point_results = []
        for p in sim_data['points']:
            point_results.append(PointResult(
                serving_team=p['serving_team'],
                winner=p['winner'],
                point_type=p['point_type'],
                duration=p['duration'],
                states=p['states']
            ))
        
        results = SimulationResults(
            team_a_name=sim_data['team_a_name'],
            team_b_name=sim_data['team_b_name'],
            total_points=sim_data['total_points'],
            points=point_results
        )
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"\nSimulation complete. Results saved to {output_file}")
        
        # Show summary unless quiet mode
        if not args.quiet:
            analysis = analyze_simulation_results(results, breakdown=args.breakdown)
            
            if args.breakdown:
                # Show full detailed analysis
                text_output = analysis.to_text(team_a.name, team_b.name)
                print(f"\n{text_output}")
            else:
                # Show quick summary
                print(f"\nQuick Summary:")
                print(f"{team_a.name}: {analysis.team_a_win_rate:.1f}% win rate ({analysis.team_a_wins:,} wins)")
                print(f"{team_b.name}: {analysis.team_b_win_rate:.1f}% win rate ({analysis.team_b_wins:,} wins)")
                print(f"Average point duration: {analysis.average_duration:.1f} actions")
        
        return 0
        
    except Exception as e:
        print("Error in simulation", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_analyze(args):
    """Handle 'bvsim analyze' command - results analysis"""
    try:
        # Auto-discover results file if not specified
        if not args.file:
            results_files = auto_discover_results()
            if not results_files:
                print("No simulation results found. Run 'bvsim simulate' first.", file=sys.stderr)
                return 1
            results_file = results_files[-1]  # Use most recent
            print(f"Analyzing {results_file}...")
        else:
            results_file = args.file
        
        # Load and analyze results
        results = SimulationResults.from_json_file(results_file)
        analysis = analyze_simulation_results(results, breakdown=args.breakdown)
        
        if args.format == 'json':
            print(json.dumps(analysis.to_dict(), indent=2))
        else:
            text_output = analysis.to_text(results.team_a_name, results.team_b_name)
            print(text_output)
        
        return 0
        
    except FileNotFoundError as e:
        print("Results file not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Error analyzing results", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_create_team(args):
    """Handle 'bvsim create-team' command"""
    try:
        template_type = "advanced" if args.advanced else "basic"
        output_file = args.output or f"{args.name.lower().replace(' ', '_')}.yaml"
        
        file_path = create_team_template(
            team_name=args.name,
            template_type=template_type,
            output_file=output_file,
            interactive=args.interactive
        )
        
        print(f"Team '{args.name}' created: {file_path}")
        
        # Validate the created team
        team = Team.from_yaml_file(file_path)
        print(f"✓ Team validation successful")
        
        return 0
        
    except Exception as e:
        print("Error creating team", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_validate(args):
    """Handle 'bvsim validate' command"""
    try:
        team = Team.from_yaml_file(args.team)
        print(f"✓ Team '{team.name}' is valid")
        
        if args.format == 'json':
            print(json.dumps({"valid": True, "team_name": team.name}, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"✗ Team validation failed: {e}", file=sys.stderr)
        
        if args.format == 'json':
            print(json.dumps({"valid": False, "error": str(e)}, indent=2))
        
        return 1


def cmd_examples(args):
    """Handle 'bvsim examples' command - generate concise rally representations"""
    try:
        # Determine teams
        teams = args.teams or []
        if len(teams) == 0:
            team_a = Team.from_dict(get_basic_template("Team A"))
            team_b = Team.from_dict(get_basic_template("Team B"))
        elif len(teams) == 1:
            team_a = get_team_or_default(teams[0])
            team_b = Team.from_dict(get_basic_template("Opponent"))
        elif len(teams) == 2:
            team_a = get_team_or_default(teams[0])
            team_b = get_team_or_default(teams[1])
        else:
            print("Error: examples command accepts 0-2 teams", file=sys.stderr)
            return 1
        
        # Number of rallies to generate
        num_rallies = args.count
        
        print(f"Rally Examples ({num_rallies} rallies): {team_a.name} vs {team_b.name}")
        print(f"Format: [Winner] Team.Action(Quality)→Team.Action(Quality)... → Point Type")
        print("")
        
        # Generate rallies
        for i in range(num_rallies):
            # Alternate serving team
            serving_team = "A" if i % 2 == 0 else "B"
            
            # Simulate point
            point = simulate_point(team_a, team_b, serving_team=serving_team, seed=args.seed + i if args.seed else None)
            
            # Create concise representation
            rally_str = f"[{point.winner}] "
            
            # Add state sequence
            state_parts = []
            for state in point.states:
                # Abbreviate common actions and qualities
                action_abbrev = {
                    'serve': 'srv', 'receive': 'rcv', 'set': 'set', 'attack': 'att', 
                    'block': 'blk', 'dig': 'dig'
                }.get(state.action, state.action)
                
                quality_abbrev = {
                    'excellent': 'exc', 'good': 'gd', 'poor': 'pr', 'error': 'err',
                    'ace': 'ace', 'in_play': 'ok', 'kill': 'kill', 'defended': 'def',
                    'stuff': 'stuff', 'deflection_to_attack': 'def→att', 
                    'deflection_to_defense': 'def→def', 'no_touch': 'miss'
                }.get(state.quality, state.quality)
                
                state_parts.append(f"{state.team}.{action_abbrev}({quality_abbrev})")
            
            rally_str += "→".join(state_parts)
            rally_str += f" → {point.point_type}"
            
            print(f"{i+1:2d}. {rally_str}")
        
        print(f"\nGenerated {num_rallies} rally examples.")
        print("Legend: srv=serve, rcv=receive, set=set, att=attack, blk=block, dig=dig")
        print("        exc=excellent, gd=good, pr=poor, err=error, def=defended")
        
        return 0
        
    except Exception as e:
        print("Error generating rally examples", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def main(argv=None):
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        prog='bvsim',
        description='Beach Volleyball Point Simulator - Unified CLI'
    )
    parser.add_argument('--version', action='version', version=f'bvsim {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # bvsim skills - skill impact analysis
    parser_skills = subparsers.add_parser('skills', help='Analyze which skills have biggest impact on winning')
    parser_skills.add_argument('teams', nargs='*', help='Team files (0=default, 1=vs self, 2=vs opponent)')
    parser_skills.add_argument('--improve', help='Test improvement amount (e.g., "5%%" or "0.05")')
    parser_skills.add_argument('--custom', help='Comma-separated team variant YAML files (each a full or partial team definition)')
    parser_skills.add_argument('--quick', action='store_true', help='Fast analysis (10k points)')
    parser_skills.add_argument('--accurate', action='store_true', help='High precision (200k points)')
    parser_skills.add_argument('--points', type=int, help='Custom points per test')
    parser_skills.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_skills.add_argument('--no-parallel', action='store_true', help='Disable parallel processing (for testing)')
    parser_skills.add_argument('--runs', type=int, help='Number of analysis runs for statistical comparison (overrides default of 5)')
    parser_skills.add_argument('--confidence', type=float, default=0.95, help='Confidence level for intervals (default: 0.95)')
    parser_skills.set_defaults(func=cmd_skills)
    
    # bvsim compare - team comparisons
    parser_compare = subparsers.add_parser('compare', help='Compare team performance head-to-head')
    parser_compare.add_argument('teams', nargs='*', help='Team files to compare (auto-discover if none)')
    parser_compare.add_argument('--tournament', action='store_true', help='Show tournament rankings')
    parser_compare.add_argument('--quick', action='store_true', help='Fast comparison (10k points)')
    parser_compare.add_argument('--accurate', action='store_true', help='High precision comparison (200k points)')
    parser_compare.add_argument('--points', type=int, help='Points per matchup')
    parser_compare.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_compare.set_defaults(func=cmd_compare)
    
    # bvsim simulate - run simulations
    parser_simulate = subparsers.add_parser('simulate', help='Run point simulations')
    parser_simulate.add_argument('teams', nargs='*', help='Team files (0=defaults, 1=vs template, 2=custom)')
    parser_simulate.add_argument('--quick', action='store_true', help='Fast simulation (10k points)')
    parser_simulate.add_argument('--accurate', action='store_true', help='High precision simulation (200k points)')
    parser_simulate.add_argument('--points', type=int, help='Custom number of points to simulate')
    parser_simulate.add_argument('--output', help='Output file for results')
    parser_simulate.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser_simulate.add_argument('--breakdown', action='store_true', help='Include detailed breakdown')
    parser_simulate.add_argument('--progress', action='store_true', help='Show progress indicator')
    parser_simulate.add_argument('--quiet', action='store_true', help='Suppress summary output')
    parser_simulate.set_defaults(func=cmd_simulate)
    
    # bvsim analyze - analyze results
    parser_analyze = subparsers.add_parser('analyze', help='Analyze simulation results')
    parser_analyze.add_argument('file', nargs='?', help='Results JSON file (auto-discover if none)')
    parser_analyze.add_argument('--breakdown', action='store_true', help='Detailed breakdown analysis')
    parser_analyze.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_analyze.set_defaults(func=cmd_analyze)
    
    # bvsim create-team - create team configurations
    parser_create = subparsers.add_parser('create-team', help='Create new team configurations')
    parser_create.add_argument('name', help='Team name')
    parser_create.add_argument('--template', choices=['basic', 'advanced'], default='basic', help='Template type')
    parser_create.add_argument('--advanced', action='store_true', help='Use advanced template')
    parser_create.add_argument('--output', help='Output file path')
    parser_create.add_argument('--interactive', action='store_true', help='Interactive team creation')
    parser_create.set_defaults(func=cmd_create_team)
    
    # bvsim validate - validate team files
    parser_validate = subparsers.add_parser('validate', help='Validate team configuration files')
    parser_validate.add_argument('team', help='Team YAML file to validate')
    parser_validate.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_validate.set_defaults(func=cmd_validate)
    
    # bvsim examples - generate rally examples
    parser_examples = subparsers.add_parser('examples', help='Generate concise rally representations')
    parser_examples.add_argument('count', nargs='?', type=int, default=20, help='Number of rallies to generate (default: 20)')
    parser_examples.add_argument('--teams', nargs='*', help='Team files (0=defaults, 1=vs template, 2=custom)')
    parser_examples.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser_examples.set_defaults(func=cmd_examples)
    
    # Parse and execute
    if not argv:
        parser.print_help()
        return 0
    
    args = parser.parse_args(argv)
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 0
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())