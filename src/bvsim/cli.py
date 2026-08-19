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
import secrets
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import __version__
from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_core.validation import validate_team_configuration
from bvsim_stats.models import SimulationResults
from bvsim_stats.analysis import analyze_simulation_results, delta_skill_analysis, full_skill_analysis, sensitivity_analysis, multi_team_skill_analysis
from bvsim_stats.inference import (
    aggregate_effect_statistics,
    holm_adjust,
    mean_confidence_interval,
    paired_difference_statistics,
)
from bvsim_stats.match import match_impact, match_win_probability
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
    """Compatibility wrapper for the deterministic IID point model."""
    if (
        sets_to_win != 2
        or points_to_win_standard != 21
        or points_to_win_last != 15
    ):
        raise ValueError("Only standard beach-volleyball match rules are supported")
    return match_win_probability(a_win_prob, a_win_prob)


def point_to_match_impact(point_improvement: float, baseline_point_rate: float = 0.5) -> float:
    """Convert point win rate improvement to match win rate improvement."""
    improved = min(
        max(baseline_point_rate + point_improvement / 100.0, 0.0), 1.0
    )
    return match_impact(
        baseline_point_rate, baseline_point_rate, improved, improved
    )


def calculate_confidence_interval(
    values: List[float], confidence: float = 0.95
) -> Tuple[float, Optional[float], Optional[float]]:
    """Calculate mean and confidence interval for a list of values."""
    return mean_confidence_interval(values, confidence)


def format_confidence_interval(
    lower: Optional[float], upper: Optional[float], precision: int = 1
) -> str:
    if lower is None or upper is None:
        return "N/A (requires at least 2 runs)"
    return f"{lower:.{precision}f}% - {upper:.{precision}f}%"


def format_parameter_name(param_name: str) -> str:
    """Format parameter names for better readability."""
    # Apply the same abbreviations as in the CLI
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_defense", "block_probabilities.power_attack.deflection_to_d")
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_attack", "block_probabilities.power_attack.deflection_to_a")
    
    # Truncate if too long
    if len(param_name) > 50:
        return param_name[:47] + "..."
    return param_name


def run_single_skills_analysis(
    team: Team,
    opponent: Team,
    change_value: float,
    points_per_test: int,
    parallel: bool,
    run_number: int,
    run_seed: int,
    parameters: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], float]:
    """Run a single skills analysis and return the results and duration."""
    start_time = time.time()
    
    results = full_skill_analysis(
        team=team,
        opponent=opponent,
        change_value=change_value,
        points_per_test=points_per_test,
        parallel=parallel,
        seed=run_seed,
        parameters=parameters,
    )
    results["run_number"] = run_number
    
    duration = time.time() - start_time
    return results, duration


def run_single_custom_analysis(
    team: Team,
    opponent: Team,
    custom_team_files: List[str],
    points_per_test: int,
    run_number: int,
    run_seed: int,
) -> Tuple[Dict[str, Any], float]:
    """Run a single custom scenario analysis (team variant files) and return the results and duration."""
    start_time = time.time()

    results = multi_team_skill_analysis(
        base_team=team,
        opponent=opponent,
        team_variant_files=custom_team_files,
        points_per_test=points_per_test,
        seed=run_seed,
    )
    results["run_number"] = run_number

    duration = time.time() - start_time
    return results, duration


def print_holdout_confirmation(
    statistics_rows: List[Dict[str, Any]],
    confidence: float,
) -> None:
    """Print independent confirmation results for selected candidates."""
    label = f"{confidence * 100:g}%"
    print(
        f"\n{Colors.BOLD}INDEPENDENT HOLDOUT CONFIRMATION "
        f"({label} Monte Carlo CIs):{Colors.END}"
    )
    for row in sorted(
        statistics_rows, key=lambda item: item["match_mean"], reverse=True
    ):
        match_ci = format_confidence_interval(
            row["match_lower"], row["match_upper"], 2
        )
        status = "YES" if row["holm_significant"] else "No"
        print(
            f"{format_parameter_name(row['name']):<50} "
            f"{row['match_mean']:+6.2f}% [{match_ci}] "
            f"Holm confirmed: {status}"
        )


def print_custom_statistical_analysis(
    all_results: List[Dict[str, Any]],
    all_durations: List[float],
    delta_files: List[str],
    points: int,
    confidence: float,
):
    """Print statistical analysis of custom scenario impacts across multiple runs with confidence intervals."""
    
    num_runs = len(all_results)
    avg_duration = statistics.mean(all_durations)
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}CUSTOM SCENARIOS STATISTICAL ANALYSIS{Colors.END}")
    print(f"Number of Runs: {num_runs} | Average Duration: {avg_duration:.2f}s")
    
    # Extract baseline win rates from all runs
    baseline_rates = [result.get("baseline_win_rate", 0) for result in all_results]
    baseline_mean, baseline_lower, baseline_upper = calculate_confidence_interval(
        baseline_rates, confidence
    )
    
    confidence_label = f"{confidence * 100:g}%"
    print(
        f"Baseline Win Rate: {baseline_mean:.1f}% "
        f"[{confidence_label} CI: "
        f"{format_confidence_interval(baseline_lower, baseline_upper)}]"
    )
    print(f"Testing {len(delta_files)} custom scenarios ({points:,} points each)")
    print("=" * 140)
    
    # Collect scenario data across runs
    scenario_data = {}
    
    # Get scenario names from first run
    first_run_files = all_results[0].get("file_results", {})
    
    for scenario_name in first_run_files.keys():
        improvements = []
        win_rates = []
        match_improvements = []
        
        # Collect data from all runs for this scenario
        for result in all_results:
            file_results = result.get("file_results", {})
            if scenario_name in file_results:
                improvement = file_results[scenario_name].get("improvement", 0)
                win_rate = file_results[scenario_name].get("win_rate", 0)
                improvements.append(improvement)
                win_rates.append(win_rate)
                match_improvements.append(
                    file_results[scenario_name].get("match_improvement", 0)
                )
        
        if improvements:
            # Point impact statistics
            point_mean, point_lower, point_upper = calculate_confidence_interval(
                improvements, confidence
            )
            
            # Match impact statistics
            match_mean, match_lower, match_upper = calculate_confidence_interval(
                match_improvements, confidence
            )
            
            _, _, _, raw_p_value = paired_difference_statistics(
                [0.0] * len(improvements), improvements, confidence
            )
            
            scenario_data[scenario_name] = {
                'scenario': scenario_name,
                'point_mean': point_mean,
                'point_lower': point_lower,
                'point_upper': point_upper,
                'match_mean': match_mean,
                'match_lower': match_lower,
                'match_upper': match_upper,
                'raw_p_value': raw_p_value,
                'adjusted_p_value': None,
                'is_significant': False,
                'num_runs': len(improvements)
            }

    comparable = [
        scenario for scenario in scenario_data.values()
        if scenario['raw_p_value'] is not None
    ]
    adjusted_values = holm_adjust(
        [scenario['raw_p_value'] for scenario in comparable]
    )
    alpha = 1.0 - confidence
    for scenario, adjusted in zip(comparable, adjusted_values):
        scenario['adjusted_p_value'] = adjusted
        scenario['is_significant'] = adjusted < alpha
    
    # Sort by match impact (most positive first)
    scenario_comparisons = list(scenario_data.values())
    scenario_comparisons.sort(key=lambda x: x['match_mean'], reverse=True)
    
    # Print table header
    print(f"{Colors.BOLD}Scenario File                                      Point Impact  Match Impact  {confidence_label} Match CI              Holm Sig.{Colors.END}")
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
        
        match_ci = (
            f"[{match_lower:+6.2f}% - {match_upper:+6.2f}%]"
            if match_lower is not None and match_upper is not None
            else "N/A".ljust(19)
        )
        print(f"{color}{display_name:<50} {point_mean:+6.2f}%     {match_mean:+6.2f}%     {match_ci}       {sig_text:<3}{Colors.END}")
    
    print("-" * 140)
    
    # Visual confidence interval chart
    print(f"\n{Colors.BOLD}MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Scenarios):{Colors.END}")
    print("Match % |")
    
    # Calculate chart scale using match impact values
    all_values = []
    for scenario in scenario_comparisons:
        all_values.extend(
            value for value in [
                scenario['match_lower'],
                scenario['match_mean'],
                scenario['match_upper'],
            ]
            if value is not None
        )
    
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
            match_lower = scenario['match_lower'] if scenario['match_lower'] is not None else match_mean
            match_upper = scenario['match_upper'] if scenario['match_upper'] is not None else match_mean
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
                line[i] = '-'
            
            # Draw zero line if visible
            if 0 <= zero_pos < chart_width:
                line[zero_pos] = '|'
            
            # Draw mean point
            if 0 <= mean_pos < chart_width:
                if is_sig:
                    line[mean_pos] = '*'  # Significant estimate
                else:
                    line[mean_pos] = 'o'  # Non-significant estimate
            
            # Color the entire line
            if is_sig:
                color = Colors.GREEN if match_mean > 0 else Colors.RED
            else:
                color = Colors.YELLOW
            
            print(f"         | {color}{''.join(line)}{Colors.END} {scenario_name}")
        
        # Add scale markers (similar to previous function)
        print(f"         |{'-' * chart_width}")
        scale_line = ' ' * 9 + '|'
        
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
        print(f"\nLegend: {Colors.GREEN}*{Colors.END} Holm-significant positive  {Colors.RED}*{Colors.END} Holm-significant negative  {Colors.YELLOW}o{Colors.END} Non-significant  | Zero line")
    
    # Summary statistics
    total_scenarios = len(scenario_comparisons)
    significant_positive = len([s for s in significant_scenarios if s['match_mean'] > 0])
    significant_negative = len([s for s in significant_scenarios if s['match_mean'] < 0])
    
    print(f"\n{Colors.BOLD}STATISTICAL SUMMARY:{Colors.END}")
    print(f"Total scenarios analyzed: {total_scenarios}")
    print(f"Holm-significant positive impacts: {significant_positive}")
    print(f"Holm-significant negative impacts: {significant_negative}")

    if scenario_comparisons:
        best_scenario = scenario_comparisons[0]
        print(f"Top exploratory scenario: {Colors.GREEN}{best_scenario['scenario']}{Colors.END}")
        point_ci = format_confidence_interval(
            best_scenario['point_lower'], best_scenario['point_upper'], 2
        )
        match_ci = format_confidence_interval(
            best_scenario['match_lower'], best_scenario['match_upper'], 2
        )
        print(f"Point Impact: {Colors.GREEN}{best_scenario['point_mean']:+5.2f}% [{point_ci}]{Colors.END}")
        print(f"Match Impact: {Colors.GREEN}{best_scenario['match_mean']:+5.2f}% [{match_ci}]{Colors.END}")

    # Show model-implied effects without presenting them as empirical guidance.
    if significant_scenarios:
        print(f"\n{Colors.BOLD}HOLM-SIGNIFICANT MODEL EFFECTS (EXPLORATORY):{Colors.END}")
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
            point_ci = format_confidence_interval(point_lower, point_upper, 2)
            match_ci = format_confidence_interval(match_lower, match_upper, 2)
            print(f"   {color}Point: {point_mean:+5.2f}% [{point_ci}] | Match: {match_mean:+5.2f}% [{match_ci}]{Colors.END}")


def print_skills_statistical_analysis(
    all_results: List[Dict[str, Any]],
    all_durations: List[float],
    change_value: float,
    points: int,
    confidence: float,
):
    """Print a statistical analysis of skill impacts across multiple runs with confidence intervals."""
    
    num_runs = len(all_results)
    avg_duration = statistics.mean(all_durations)
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}BVSIM SKILLS STATISTICAL ANALYSIS{Colors.END}")
    print(f"Number of Runs: {num_runs} | Average Duration: {avg_duration:.2f}s")
    
    # Extract baseline win rates from all runs
    baseline_rates = [result.get("baseline_win_rate", 0) for result in all_results]
    baseline_mean, baseline_lower, baseline_upper = calculate_confidence_interval(
        baseline_rates, confidence
    )
    
    confidence_label = f"{confidence * 100:g}%"
    print(
        f"Baseline Win Rate: {baseline_mean:.1f}% "
        f"[{confidence_label} CI: "
        f"{format_confidence_interval(baseline_lower, baseline_upper)}]"
    )
    change_pct = change_value * 100
    print(f"Testing {change_pct:+.1f}% improvement on {all_results[0]['total_parameters']} parameters ({points:,} points each)")
    print("=" * 140)
    
    # Collect all skill improvement data across runs
    skill_data = {}
    
    # Get all parameter names from first run
    first_run_params = all_results[0].get("parameter_improvements", {})
    
    for param_name in first_run_params.keys():
        improvements = []
        match_improvements = []
        
        # Collect improvement values from all runs for this parameter
        for result in all_results:
            params = result.get("parameter_improvements", {})
            if param_name in params:
                improvement = params[param_name].get("improvement", 0)
                improvements.append(improvement)
                match_improvements.append(
                    params[param_name].get("match_improvement", 0)
                )
        
        if improvements:
            mean, lower_ci, upper_ci = calculate_confidence_interval(
                improvements, confidence
            )
            
            # Calculate match impact statistics
            match_mean, match_lower, match_upper = calculate_confidence_interval(
                match_improvements, confidence
            )
            
            _, _, _, raw_p_value = paired_difference_statistics(
                [0.0] * len(improvements), improvements, confidence
            )
            
            skill_data[param_name] = {
                'parameter': param_name,
                'mean_improvement': mean,
                'lower_ci': lower_ci,
                'upper_ci': upper_ci,
                'match_mean': match_mean,
                'match_lower': match_lower,
                'match_upper': match_upper,
                'raw_p_value': raw_p_value,
                'adjusted_p_value': None,
                'is_significant': False,
                'num_runs': len(improvements)
            }

    comparable = [
        skill for skill in skill_data.values()
        if skill['raw_p_value'] is not None
    ]
    adjusted_values = holm_adjust(
        [skill['raw_p_value'] for skill in comparable]
    )
    alpha = 1.0 - confidence
    for skill, adjusted in zip(comparable, adjusted_values):
        skill['adjusted_p_value'] = adjusted
        skill['is_significant'] = adjusted < alpha
    
    # Sort by mean improvement (most positive impact first, then most negative)
    skill_comparisons = list(skill_data.values())
    skill_comparisons.sort(key=lambda x: x['mean_improvement'], reverse=True)
    
    # Print table header
    print(f"{Colors.BOLD}Skill Parameter                                    Point Impact  Match Impact  {confidence_label} Match CI              Holm Sig.{Colors.END}")
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
        
        match_ci = (
            f"[{match_lower:+6.2f}% - {match_upper:+6.2f}%]"
            if match_lower is not None and match_upper is not None
            else "N/A".ljust(19)
        )
        print(f"{color}{display_name:<50} {mean_imp:+6.2f}%     {match_mean:+6.2f}%     {match_ci}       {sig_text:<3}{Colors.END}")
    
    print("-" * 140)
    
    # Visual confidence interval chart
    print(f"\n{Colors.BOLD}MATCH WIN RATE CONFIDENCE INTERVAL CHART (All Skills):{Colors.END}")
    print("Match % |")
    
    # Use all skills, already sorted by mean improvement
    chart_skills = skill_comparisons
    
    # Calculate chart scale using match impact values
    all_values = []
    for skill in chart_skills:
        all_values.extend(
            value for value in [
                skill['match_lower'],
                skill['match_mean'],
                skill['match_upper'],
            ]
            if value is not None
        )
    
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
            match_lower = skill['match_lower'] if skill['match_lower'] is not None else match_mean
            match_upper = skill['match_upper'] if skill['match_upper'] is not None else match_mean
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
                line[i] = '-'
            
            # Draw zero line if visible
            if 0 <= zero_pos < chart_width:
                line[zero_pos] = '|'
            
            # Draw mean point (overwrites other symbols)
            if 0 <= mean_pos < chart_width:
                if is_sig:
                    line[mean_pos] = '*'  # Significant estimate
                else:
                    line[mean_pos] = 'o'  # Non-significant estimate
            
            # Color the entire line
            if is_sig:
                color = Colors.GREEN if mean_imp > 0 else Colors.RED
            else:
                color = Colors.YELLOW
            
            # Use full parameter name (no truncation)
            display_name = param_name
            
            print(f"         | {color}{''.join(line)}{Colors.END} {display_name}")
        
        # Add scale markers
        print(f"         |{'-' * chart_width}")
        scale_line = ' ' * 9 + '|'
        
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
        print(f"\nLegend: {Colors.GREEN}*{Colors.END} Holm-significant positive  {Colors.RED}*{Colors.END} Holm-significant negative  {Colors.YELLOW}o{Colors.END} Non-significant  | Zero line")
    
    # Summary statistics
    total_skills = len(skill_comparisons)
    significant_positive = len([s for s in significant_skills if s['mean_improvement'] > 0])
    significant_negative = len([s for s in significant_skills if s['mean_improvement'] < 0])
    high_impact_skills = len([s for s in significant_skills if abs(s['mean_improvement']) > 1.0])
    
    print(f"\n{Colors.BOLD}STATISTICAL SUMMARY:{Colors.END}")
    print(f"Total skills analyzed: {total_skills}")
    print(f"Holm-significant positive impacts: {significant_positive}")
    print(f"Holm-significant negative impacts: {significant_negative}")
    print(f"High-impact skills (>1% improvement): {high_impact_skills}")
    
    if skill_comparisons:
        top_skill = skill_comparisons[0]
        print(f"Top exploratory skill: {Colors.GREEN}{format_parameter_name(top_skill['parameter'])}{Colors.END}")
        point_ci = format_confidence_interval(
            top_skill['lower_ci'], top_skill['upper_ci'], 2
        )
        match_ci = format_confidence_interval(
            top_skill['match_lower'], top_skill['match_upper'], 2
        )
        print(f"Point Impact: {Colors.GREEN}{top_skill['mean_improvement']:+5.2f}% [{point_ci}]{Colors.END}")
        print(f"Match Impact: {Colors.GREEN}{top_skill['match_mean']:+5.2f}% [{match_ci}]{Colors.END}")
    
    # Show only statistically significant high-impact skills
    if significant_skills:
        print(f"\n{Colors.BOLD}HOLM-SIGNIFICANT MODEL EFFECTS (EXPLORATORY):{Colors.END}")
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
            point_ci = format_confidence_interval(lower_ci, upper_ci, 2)
            match_ci = format_confidence_interval(match_lower, match_upper, 2)
            print(f"    {color}Point: {mean_imp:+5.2f}% [{point_ci}] | Match: {match_mean:+5.2f}% [{match_ci}]{Colors.END}")


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
            if not validate_team_configuration(team):
                valid_teams.append(file)
        except (OSError, ValueError, TypeError):
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
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
            
    return valid_results


def get_team_or_default(team_arg: Optional[str], default_name: str = "Default Team") -> Team:
    """Get team from argument or create default"""
    if team_arg:
        if Path(team_arg + '.yaml').exists():
            team = Team.from_yaml_file(team_arg + '.yaml')
        elif Path(team_arg).exists():
            team = Team.from_yaml_file(team_arg)
        else:
            raise FileNotFoundError(f"Team file not found: {team_arg}")
    else:
        team = Team.from_dict(get_basic_template(default_name))

    errors = validate_team_configuration(team)
    if errors:
        raise ValueError(
            f"Invalid team configuration '{team.name}': " + "; ".join(errors)
        )
    return team


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

        for candidate in (team, opponent):
            errors = validate_team_configuration(candidate)
            if errors:
                raise ValueError(
                    f"Invalid team configuration '{candidate.name}': "
                    + "; ".join(errors)
                )
        
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
        if num_runs < 1:
            raise ValueError("runs must be at least 1")
        master_seed = (
            args.seed if args.seed is not None else secrets.randbits(64)
        )
        seed_stream = random.Random(master_seed)
        run_seeds = [seed_stream.getrandbits(64) for _ in range(num_runs)]
        holdout_run_seeds = [
            seed_stream.getrandbits(64) for _ in range(num_runs)
        ]
        
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
                        executor.submit(
                            run_single_custom_analysis, team, opponent,
                            custom_files, points, i + 1, run_seeds[i]
                        )
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
                        print(f"\r{Colors.GREEN}Analysis {completed_count} completed in {duration:.2f}s ({completed_count}/{num_runs}){Colors.END}", end="", flush=True)

                    print()  # Final newline after all analyses complete
                    all_results.sort(key=lambda result: result["run_number"])

                initial_statistics = aggregate_effect_statistics(
                    all_results, "file_results", args.confidence
                )
                file_by_stem = {
                    Path(file_name).stem: file_name
                    for file_name in custom_files
                }
                holdout_files = [
                    file_by_stem[row["name"]] for row in sorted(
                        initial_statistics,
                        key=lambda row: row["match_mean"],
                        reverse=True,
                    )[:3]
                ]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    holdout_futures = [
                        executor.submit(
                            run_single_custom_analysis, team, opponent,
                            holdout_files, points, i + 1,
                            holdout_run_seeds[i]
                        )
                        for i in range(num_runs)
                    ]
                    holdout_results = [
                        future.result()[0] for future in as_completed(
                            holdout_futures
                        )
                    ]
                holdout_results.sort(key=lambda result: result["run_number"])
                holdout_statistics = aggregate_effect_statistics(
                    holdout_results, "file_results", args.confidence
                )
                
                # Display statistical analysis
                if args.format == 'json':
                    # For JSON output, combine all results
                    combined_results = {
                        "custom_statistical_analysis": True,
                        "num_runs": num_runs,
                        "scenario_files": custom_files,
                        "points_per_test": points,
                        "master_seed": master_seed,
                        "effect_statistics": initial_statistics,
                        "holdout_statistics": holdout_statistics,
                        "holdout_seeds": holdout_run_seeds,
                        "individual_runs": all_results,
                        "execution_summary": {
                            "total_duration": time.time() - total_start_time,
                            "average_duration": statistics.mean(all_durations),
                            "runs_completed": num_runs
                        }
                    }
                    print(json.dumps(combined_results, indent=2))
                else:
                    print_custom_statistical_analysis(
                        all_results, all_durations, custom_files, points,
                        args.confidence
                    )
                    print_holdout_confirmation(
                        holdout_statistics, args.confidence
                    )
                    
                    total_duration = time.time() - total_start_time
                    avg_duration = statistics.mean(all_durations)
                    
                    print(f"\n{Colors.BOLD}EXECUTION SUMMARY:{Colors.END}")
                    print(f"Total script execution time: {Colors.GREEN}{total_duration:.2f} seconds{Colors.END}")
                    print(f"Average analysis time: {Colors.GREEN}{avg_duration:.2f} seconds{Colors.END}")
                    print(f"Number of runs completed: {Colors.GREEN}{num_runs}{Colors.END}")
                    print(f"Master seed: {Colors.GREEN}{master_seed}{Colors.END}")
                    
                    # Statistical note
                    print(f"\n{Colors.YELLOW}Statistical Analysis: Intervals quantify Monte Carlo uncertainty for these fixed model inputs.")
                    print(f"Scenarios marked 'YES' pass Holm correction across the tested scenario family.")
                    print(f"Rankings are exploratory and are not empirical training recommendations.{Colors.END}")
                
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
                        executor.submit(
                            run_single_skills_analysis, team, opponent,
                            change_value, points, not args.no_parallel,
                            i + 1, run_seeds[i]
                        )
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
                        print(f"\r{Colors.GREEN}Analysis {completed_count} completed in {duration:.2f}s ({completed_count}/{num_runs}){Colors.END}", end="", flush=True)

                    print()  # Final newline after all analyses complete
                    all_results.sort(key=lambda result: result["run_number"])

                initial_statistics = aggregate_effect_statistics(
                    all_results, "parameter_improvements", args.confidence
                )
                holdout_parameters = [
                    row["name"] for row in sorted(
                        initial_statistics,
                        key=lambda row: row["match_mean"],
                        reverse=True,
                    )[:3]
                ]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    holdout_futures = [
                        executor.submit(
                            run_single_skills_analysis, team, opponent,
                            change_value, points, not args.no_parallel,
                            i + 1, holdout_run_seeds[i],
                            holdout_parameters
                        )
                        for i in range(num_runs)
                    ]
                    holdout_results = [
                        future.result()[0] for future in as_completed(
                            holdout_futures
                        )
                    ]
                holdout_results.sort(key=lambda result: result["run_number"])
                holdout_statistics = aggregate_effect_statistics(
                    holdout_results, "parameter_improvements",
                    args.confidence
                )
                
                # Display statistical analysis
                if args.format == 'json':
                    # For JSON output, combine all results
                    combined_results = {
                        "statistical_analysis": True,
                        "num_runs": num_runs,
                        "change_value": change_value,
                        "points_per_test": points,
                        "master_seed": master_seed,
                        "effect_statistics": initial_statistics,
                        "holdout_statistics": holdout_statistics,
                        "holdout_seeds": holdout_run_seeds,
                        "individual_runs": all_results,
                        "execution_summary": {
                            "total_duration": time.time() - total_start_time,
                            "average_duration": statistics.mean(all_durations),
                            "runs_completed": num_runs
                        }
                    }
                    print(json.dumps(combined_results, indent=2))
                else:
                    print_skills_statistical_analysis(
                        all_results, all_durations, change_value, points,
                        args.confidence
                    )
                    print_holdout_confirmation(
                        holdout_statistics, args.confidence
                    )
                    
                    total_duration = time.time() - total_start_time
                    avg_duration = statistics.mean(all_durations)
                    
                    print(f"\n{Colors.BOLD}EXECUTION SUMMARY:{Colors.END}")
                    print(f"Total script execution time: {Colors.GREEN}{total_duration:.2f} seconds{Colors.END}")
                    print(f"Average analysis time: {Colors.GREEN}{avg_duration:.2f} seconds{Colors.END}")
                    print(f"Number of runs completed: {Colors.GREEN}{num_runs}{Colors.END}")
                    print(f"Master seed: {Colors.GREEN}{master_seed}{Colors.END}")
                    
                    # Statistical note
                    print(f"\n{Colors.YELLOW}Statistical Analysis: Intervals quantify Monte Carlo uncertainty for these fixed model inputs.")
                    print(f"Skills marked 'YES' pass Holm correction across the tested parameter family.")
                    print(f"Rankings are exploratory; the model has not been calibrated to real match data.{Colors.END}")
                
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

        for candidate in teams:
            errors = validate_team_configuration(candidate)
            if errors:
                raise ValueError(
                    f"Invalid team configuration '{candidate.name}': "
                    + "; ".join(errors)
                )
        
        # Determine points based on speed options
        if args.quick:
            points = 10000
        elif args.accurate:
            points = 200000
        else:
            points = args.points or 50000
        
        # Run comparisons using existing compare_teams functionality
        results = compare_teams(
            teams, points_per_matchup=points, seed=args.seed
        )
        
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

        for candidate in (team_a, team_b):
            errors = validate_team_configuration(candidate)
            if errors:
                raise ValueError(
                    f"Invalid team configuration '{candidate.name}': "
                    + "; ".join(errors)
                )
        
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
            points=point_results,
            seed=sim_data['seed'],
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
        print("Team validation successful")
        
        return 0
        
    except Exception as e:
        print("Error creating team", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_validate(args):
    """Handle 'bvsim validate' command"""
    try:
        team = Team.from_yaml_file(args.team)
        print(f"Team '{team.name}' is valid")
        
        if args.format == 'json':
            print(json.dumps({"valid": True, "team_name": team.name}, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"Team validation failed: {e}", file=sys.stderr)
        
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
        print("Format: [Winner] Team.Action(Quality)->Team.Action(Quality)... -> Point Type")
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
                    'stuff': 'stuff', 'deflection_to_attack': 'def->att',
                    'deflection_to_defense': 'def->def', 'no_touch': 'miss'
                }.get(state.quality, state.quality)
                
                state_parts.append(f"{state.team}.{action_abbrev}({quality_abbrev})")
            
            rally_str += "->".join(state_parts)
            rally_str += f" -> {point.point_type}"
            
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
    parser_skills.add_argument('--seed', type=int, help='Master random seed for reproducibility')
    parser_skills.set_defaults(func=cmd_skills)
    
    # bvsim compare - team comparisons
    parser_compare = subparsers.add_parser('compare', help='Compare team performance head-to-head')
    parser_compare.add_argument('teams', nargs='*', help='Team files to compare (auto-discover if none)')
    parser_compare.add_argument('--tournament', action='store_true', help='Show tournament rankings')
    parser_compare.add_argument('--quick', action='store_true', help='Fast comparison (10k points)')
    parser_compare.add_argument('--accurate', action='store_true', help='High precision comparison (200k points)')
    parser_compare.add_argument('--points', type=int, help='Points per matchup')
    parser_compare.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_compare.add_argument('--seed', type=int, help='Random seed for reproducibility')
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