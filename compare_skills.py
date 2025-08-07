#!/usr/bin/env python3
"""
Script to run 'bvsim skills --accurate' twice and compare results
showing skill impact differences ordered by most impactful skills.
"""

import subprocess
import json
import time
import sys
import argparse
import statistics
import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

# ANSI color codes - using standard codes
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

def run_skills_analysis(run_number: int, points: int = None, speed_flag: str = "--accurate") -> Tuple[Dict[str, Any], float]:
    """Run a single skills analysis and return the results and duration."""
    if points:
        points_desc = f"{points//1000}k" if points >= 1000 else str(points)
    else:
        points_desc = {"--quick": "10k", "--accurate": "200k"}.get(speed_flag, "100k")
    print(f"{Colors.CYAN}Running skills analysis {run_number} ({points_desc} points)...{Colors.END}")
    
    start_time = time.time()
    
    # Run the skills analysis with JSON output
    if points:
        cmd = ["./bvsim", "skills", "--points", str(points), "--format", "json"]
    else:
        cmd = ["./bvsim", "skills", speed_flag, "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"{Colors.RED}Error running skills analysis {run_number}:{Colors.END}")
        print(result.stderr)
        sys.exit(1)
    
    duration = time.time() - start_time
    
    return json.loads(result.stdout), duration

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

def calculate_difference(val1: float, val2: float) -> Tuple[float, float]:
    """Calculate absolute and percentage difference between two values."""
    abs_diff = abs(val1 - val2)
    avg_val = (abs(val1) + abs(val2)) / 2
    if avg_val > 0.001:  # Avoid division by very small numbers
        pct_diff = abs_diff / avg_val * 100
    else:
        pct_diff = 0.0
    
    # Cap extreme percentage differences for readability
    pct_diff = min(pct_diff, 9999.9)
    return abs_diff, pct_diff

def get_color_for_difference(pct_diff: float) -> str:
    """Return color code based on percentage difference magnitude."""
    if pct_diff >= 10.0:
        return Colors.RED + Colors.BOLD
    elif pct_diff >= 5.0:
        return Colors.YELLOW + Colors.BOLD
    elif pct_diff >= 2.0:
        return Colors.CYAN + Colors.BOLD
    elif pct_diff >= 0.5:
        return Colors.BLUE
    else:
        return Colors.WHITE

def format_parameter_name(param_name: str) -> str:
    """Format parameter names for better readability."""
    # Apply the same abbreviations as in the CLI
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_defense", "block_probabilities.power_attack.deflection_to_d")
    param_name = param_name.replace("block_probabilities.power_attack.deflection_to_attack", "block_probabilities.power_attack.deflection_to_a")
    
    # Truncate if too long
    if len(param_name) > 50:
        return param_name[:47] + "..."
    return param_name

def print_skills_statistical_analysis(all_results: List[Dict[str, Any]], all_durations: List[float]):
    """Print a statistical analysis of skill impacts across multiple runs with confidence intervals."""
    
    num_runs = len(all_results)
    avg_duration = statistics.mean(all_durations)
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}BVSIM SKILLS STATISTICAL ANALYSIS{Colors.END}")
    print(f"Number of Runs: {num_runs} | Average Duration: {avg_duration:.2f}s")
    
    # Extract baseline win rates from all runs
    baseline_rates = [result.get("baseline_win_rate", 0) for result in all_results]
    baseline_mean, baseline_lower, baseline_upper = calculate_confidence_interval(baseline_rates)
    
    print(f"Baseline Win Rate: {baseline_mean:.1f}% [95% CI: {baseline_lower:.1f}% - {baseline_upper:.1f}%]")
    print("=" * 140)
    
    # Collect all skill improvement data across runs
    skill_data = {}
    
    # Get all parameter names from first run
    first_run_params = all_results[0].get("parameter_improvements", {})
    
    # Show progress during match impact calculation
    total_skills = len(first_run_params)
    print(f"Calculating match win rate impacts for {total_skills} skills...")
    
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

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Run multiple bvsim skills analyses and show statistical comparison')
    parser.add_argument('--quick', action='store_true', help='Use quick analysis (10k points)')
    parser.add_argument('--accurate', action='store_true', help='Use accurate analysis (200k points)')
    parser.add_argument('--points', type=int, help='Specify custom number of points per analysis')
    parser.add_argument('--runs', type=int, default=5, help='Number of analysis runs (default: 5)')
    args = parser.parse_args()
    
    # Determine analysis parameters
    num_runs = args.runs
    
    if args.points:
        speed_flag = None
        points = args.points
        points_desc = f"{points//1000}k points each" if points >= 1000 else f"{points} points each"
    elif args.quick:
        speed_flag = "--quick"
        points = None
        points_desc = "10k points each"
    elif args.accurate:
        speed_flag = "--accurate"
        points = None
        points_desc = "200k points each"
    else:
        speed_flag = "--accurate"  # Default to accurate
        points = None
        points_desc = "200k points each"
    
    print(f"{Colors.BOLD}BVSim Skills Statistical Analysis Tool{Colors.END}")
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
                executor.submit(run_skills_analysis, i+1, points, speed_flag)
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
                print(f"{Colors.GREEN}✓ Analysis {completed_count} completed in {duration:.2f}s ({completed_count}/{num_runs}){Colors.END}")
        
        # Display statistical analysis
        print_skills_statistical_analysis(all_results, all_durations)
        
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
        print(f"\n{Colors.BOLD}Usage:{Colors.END}")
        print(f"  python3 compare_skills.py --quick --runs 3        # Fast analysis (10k points, 3 runs)")
        print(f"  python3 compare_skills.py --accurate --runs 5     # Full analysis (200k points, 5 runs)")
        print(f"  python3 compare_skills.py --points 50000 --runs 8 # Custom analysis (50k points, 8 runs)")
        print(f"  python3 compare_skills.py --points 20000          # Custom analysis (20k points, default 5 runs)")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Script interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()