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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

# ANSI color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
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

def print_skills_comparison(run1: Dict[str, Any], run2: Dict[str, Any], duration1: float, duration2: float):
    """Print a detailed comparison table of skill impacts with colored differences."""
    
    print(f"\n{Colors.BOLD}{Colors.UNDERLINE}BVSIM SKILLS ANALYSIS COMPARISON{Colors.END}")
    print(f"Run 1 Duration: {duration1:.2f}s | Run 2 Duration: {duration2:.2f}s")
    
    # Extract baseline win rates
    baseline1 = run1.get("baseline_win_rate", 0)
    baseline2 = run2.get("baseline_win_rate", 0)
    
    print(f"Run 1 Baseline Win Rate: {baseline1:.1f}% | Run 2 Baseline Win Rate: {baseline2:.1f}%")
    print("=" * 100)
    
    # Extract parameter improvements from both runs
    params1 = run1.get("parameter_improvements", {})
    params2 = run2.get("parameter_improvements", {})
    
    # Create combined dataset for comparison
    skill_comparisons = []
    
    for param_name in params1.keys():
        if param_name in params2:
            data1 = params1[param_name]
            data2 = params2[param_name]
            
            # Extract win rates and improvements
            win_rate1 = data1.get("win_rate", 0)
            win_rate2 = data2.get("win_rate", 0)
            improvement1 = data1.get("improvement", 0)
            improvement2 = data2.get("improvement", 0)
            
            # Calculate differences
            win_rate_abs_diff, win_rate_pct_diff = calculate_difference(win_rate1, win_rate2)
            improvement_abs_diff, improvement_pct_diff = calculate_difference(improvement1, improvement2)
            
            # Use average improvement for ordering (most impactful skills first)
            avg_improvement = (improvement1 + improvement2) / 2
            
            skill_comparisons.append({
                'parameter': param_name,
                'win_rate1': win_rate1,
                'win_rate2': win_rate2,
                'improvement1': improvement1,
                'improvement2': improvement2,
                'win_rate_diff': win_rate_abs_diff,
                'win_rate_pct_diff': win_rate_pct_diff,
                'improvement_diff': improvement_abs_diff,
                'improvement_pct_diff': improvement_pct_diff,
                'avg_improvement': avg_improvement
            })
    
    # Sort by average improvement (most impactful first)
    skill_comparisons.sort(key=lambda x: x['avg_improvement'], reverse=True)
    
    # Print table header
    print(f"{Colors.BOLD}{'Skill Parameter':<50} {'Run 1':<12} {'Run 2':<12} {'Diff':<8} {'% Diff':<8} {'Impact':<8}{Colors.END}")
    print(f"{Colors.BOLD}{'':<50} {'Improv':<12} {'Improv':<12} {'(pp)':<8} {'(%)':<8} {'Rank':<8}{Colors.END}")
    print("-" * 100)
    
    # Track largest differences for summary
    largest_diffs = []
    
    for i, skill in enumerate(skill_comparisons):
        param_name = format_parameter_name(skill['parameter'])
        improvement1 = skill['improvement1']
        improvement2 = skill['improvement2']
        improvement_diff = skill['improvement_diff']
        improvement_pct_diff = skill['improvement_pct_diff']
        avg_improvement = skill['avg_improvement']
        
        # Color based on percentage difference in improvement values
        color = get_color_for_difference(improvement_pct_diff)
        
        # Format improvement values as percentages with + sign
        imp1_str = f"{improvement1:+6.2f}%"
        imp2_str = f"{improvement2:+6.2f}%"
        diff_str = f"{improvement_diff:+5.2f}pp"
        pct_diff_str = f"{improvement_pct_diff:6.1f}%"
        rank_str = f"#{i+1:2d}"
        
        # Print row with appropriate coloring
        print(f"{color}{param_name:<50} {imp1_str:<12} {imp2_str:<12} {diff_str:<8} {pct_diff_str:<8} {rank_str:<8}{Colors.END}")
        
        # Track for summary (only meaningful differences)
        if improvement_pct_diff > 1.0:
            largest_diffs.append((param_name, improvement_pct_diff, improvement_diff, avg_improvement))
    
    print("-" * 100)
    
    # Summary of largest differences
    if largest_diffs:
        largest_diffs.sort(key=lambda x: x[1], reverse=True)  # Sort by percentage difference
        print(f"\n{Colors.BOLD}LARGEST DIFFERENCES IN SKILL IMPACT:{Colors.END}")
        for i, (param, pct_diff, abs_diff, avg_impact) in enumerate(largest_diffs[:10]):
            color = get_color_for_difference(pct_diff)
            print(f"{i+1:2d}. {color}{param}: {pct_diff:.1f}% difference (avg impact: {avg_impact:+5.2f}%){Colors.END}")
    else:
        print(f"\n{Colors.GREEN}All skill impacts are very consistent between runs (< 1% difference){Colors.END}")
    
    # Statistical summary
    total_skills = len(skill_comparisons)
    high_impact_skills = len([s for s in skill_comparisons if s['avg_improvement'] > 2.0])
    
    print(f"\n{Colors.BOLD}ANALYSIS SUMMARY:{Colors.END}")
    print(f"Total skills analyzed: {total_skills}")
    print(f"High-impact skills (>2% improvement): {high_impact_skills}")
    print(f"Most impactful skill: {Colors.GREEN}{format_parameter_name(skill_comparisons[0]['parameter'])}{Colors.END}")
    print(f"Average impact of top skill: {Colors.GREEN}{skill_comparisons[0]['avg_improvement']:+5.2f}%{Colors.END}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Compare two bvsim skills analyses')
    parser.add_argument('--quick', action='store_true', help='Use quick analysis (10k points)')
    parser.add_argument('--accurate', action='store_true', help='Use accurate analysis (200k points)')
    parser.add_argument('--points', type=int, help='Specify custom number of points per analysis')
    args = parser.parse_args()
    
    # Determine analysis parameters
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
    
    print(f"{Colors.BOLD}BVSim Skills Analysis Comparison Tool{Colors.END}")
    print(f"Running two skills analyses ({points_desc}) for comparison...")
    
    total_start_time = time.time()
    
    # Run two skills analyses in parallel
    try:
        print(f"{Colors.CYAN}Starting both analyses in parallel...{Colors.END}")
        
        # Create a thread pool to run both analyses concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            future1 = executor.submit(run_skills_analysis, 1, points, speed_flag)
            future2 = executor.submit(run_skills_analysis, 2, points, speed_flag)
            
            # Wait for both to complete and get results
            results = {}
            completed_count = 0
            
            for future in as_completed([future1, future2]):
                completed_count += 1
                
                if future == future1:
                    run1_data, duration1 = future.result()
                    results['run1'] = (run1_data, duration1)
                    print(f"{Colors.GREEN}✓ Analysis 1 completed in {duration1:.2f}s ({completed_count}/2){Colors.END}")
                else:
                    run2_data, duration2 = future.result()
                    results['run2'] = (run2_data, duration2)
                    print(f"{Colors.GREEN}✓ Analysis 2 completed in {duration2:.2f}s ({completed_count}/2){Colors.END}")
            
            # Extract results
            run1_data, duration1 = results['run1']
            run2_data, duration2 = results['run2']
        
        # Display comparison
        print_skills_comparison(run1_data, run2_data, duration1, duration2)
        
        total_duration = time.time() - total_start_time
        
        print(f"\n{Colors.BOLD}EXECUTION SUMMARY:{Colors.END}")
        print(f"Total script execution time: {Colors.GREEN}{total_duration:.2f} seconds{Colors.END}")
        print(f"Average analysis time: {Colors.GREEN}{(duration1 + duration2) / 2:.2f} seconds{Colors.END}")
        
        # Statistical note
        print(f"\n{Colors.YELLOW}Note: Small differences between runs are normal due to randomization.")
        print(f"Large differences (>10%) may indicate statistical variance or insufficient sample size.")
        print(f"Skills are ordered by average impact (most important training targets first).{Colors.END}")
        print(f"\n{Colors.BOLD}Usage:{Colors.END}")
        print(f"  python3 compare_skills.py --quick      # Fast comparison (10k points, ~4 seconds parallel)")
        print(f"  python3 compare_skills.py --accurate   # Full comparison (200k points, ~2 minutes parallel)")
        print(f"  python3 compare_skills.py --points 50000 # Custom comparison (50k points, ~30 seconds parallel)")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Script interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()