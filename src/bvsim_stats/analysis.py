#!/usr/bin/env python3
"""
Statistical analysis functions for volleyball simulation results.
"""

import sys
import os
from collections import Counter
from typing import List, Dict, Any
import copy
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing

# Add bvsim_core to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from .models import SimulationResults, AnalysisResults, SensitivityResults, SensitivityDataPoint


def analyze_simulation_results(results: SimulationResults, breakdown: bool = False) -> AnalysisResults:
    """
    Analyze simulation results and generate statistics.
    
    Args:
        results: Simulation results to analyze
        breakdown: Include detailed breakdown by point type
        
    Returns:
        Analysis results with win rates and breakdowns
    """
    total_points = len(results.points)
    
    # Count wins by team
    team_a_wins = sum(1 for p in results.points if p.winner == "A")
    team_b_wins = sum(1 for p in results.points if p.winner == "B")
    
    # Calculate win rates
    team_a_win_rate = (team_a_wins / total_points) * 100 if total_points > 0 else 0
    team_b_win_rate = (team_b_wins / total_points) * 100 if total_points > 0 else 0
    
    # Point type breakdown
    point_type_counter = Counter(p.point_type for p in results.points)
    point_type_breakdown = dict(point_type_counter)
    
    # Point type percentages
    point_type_percentages = {
        point_type: (count / total_points) * 100
        for point_type, count in point_type_breakdown.items()
    } if total_points > 0 else {}
    
    # Average duration
    total_duration = sum(p.duration for p in results.points)
    average_duration = total_duration / total_points if total_points > 0 else 0
    
    # Additional breakdown data if requested
    breakdown_data = {}
    if breakdown:
        # Point type breakdown by team
        team_a_point_types = Counter(p.point_type for p in results.points if p.winner == "A")
        team_b_point_types = Counter(p.point_type for p in results.points if p.winner == "B")
        
        breakdown_data["team_a_point_types"] = dict(team_a_point_types)
        breakdown_data["team_b_point_types"] = dict(team_b_point_types)
        
        # Duration breakdown by point type
        duration_by_type = {}
        for point_type in point_type_breakdown.keys():
            durations = [p.duration for p in results.points if p.point_type == point_type]
            duration_by_type[point_type] = {
                "count": len(durations),
                "average": sum(durations) / len(durations) if durations else 0,
                "min": min(durations) if durations else 0,
                "max": max(durations) if durations else 0
            }
        breakdown_data["duration_by_type"] = duration_by_type
        
        # Serving team advantage
        serving_wins = {"A": 0, "B": 0}
        serving_total = {"A": 0, "B": 0}
        for p in results.points:
            serving_total[p.serving_team] += 1
            if p.winner == p.serving_team:
                serving_wins[p.serving_team] += 1
        
        breakdown_data["serving_advantage"] = {
            "team_a_serve_win_rate": (serving_wins["A"] / serving_total["A"] * 100) if serving_total["A"] > 0 else 0,
            "team_b_serve_win_rate": (serving_wins["B"] / serving_total["B"] * 100) if serving_total["B"] > 0 else 0,
            "team_a_serves": serving_total["A"],
            "team_b_serves": serving_total["B"]
        }
    
    analysis = AnalysisResults(
        total_points=total_points,
        team_a_wins=team_a_wins,
        team_b_wins=team_b_wins,
        team_a_win_rate=team_a_win_rate,
        team_b_win_rate=team_b_win_rate,
        point_type_breakdown=point_type_breakdown,
        point_type_percentages=point_type_percentages,
        average_duration=average_duration
    )
    
    # Add breakdown data to the analysis object for access
    if breakdown_data:
        analysis.breakdown_data = breakdown_data
    
    return analysis



def delta_skill_analysis(team: Team, opponent: Team, deltas_file: str, points_per_test: int = 100000,
                        base_serving: str = "A") -> dict:
    """
    Analyze impact of specific skill improvements defined in deltas file.
    
    Args:
        team: Base team configuration to improve
        opponent: Opponent team configuration
        deltas_file: YAML file with dot-notation improvements (e.g., "serve_probabilities.ace: 0.05")
        points_per_test: Number of points to simulate per test (default: 100000)
        base_serving: Which team serves ("A" or "B")
        
    Returns:
        Dictionary with baseline and delta skill results
    """
    import yaml
    from pathlib import Path
    
    # Load deltas file
    deltas_path = Path(deltas_file)
    if not deltas_path.exists():
        raise FileNotFoundError(f"Deltas file not found: {deltas_file}")
    
    with open(deltas_path, 'r') as f:
        deltas_data = yaml.safe_load(f)
    
    if not deltas_data:
        raise ValueError(f"Empty or invalid deltas file: {deltas_file}")
    
    # Calculate baseline win rate
    baseline_win_rate = _calculate_win_rate(team, opponent, points_per_test, base_serving)
    
    results = {
        "baseline_win_rate": baseline_win_rate,
        "delta_improvements": {}
    }
    
    # Test each delta improvement
    for parameter, delta_value in deltas_data.items():
        try:
            # Get current value
            current_value = get_nested_value(team.to_dict(), parameter)
            if not isinstance(current_value, (int, float)):
                print(f"Warning: Skipping non-numeric parameter '{parameter}'")
                continue
            
            # Calculate new value (additive)
            new_value = current_value + delta_value
            
            # Create modified team
            modified_team_data = copy.deepcopy(team.to_dict())
            
            # Apply delta improvement with probability adjustment
            modified_team_data = _adjust_probability_distribution(
                modified_team_data, 
                parameter, 
                new_value
            )
            modified_team = Team.from_dict(modified_team_data)
            
            # Calculate win rate with delta improvement
            delta_win_rate = _calculate_win_rate(modified_team, opponent, points_per_test, base_serving)
            improvement = delta_win_rate - baseline_win_rate
            
            results["delta_improvements"][parameter] = {
                "win_rate": delta_win_rate,
                "improvement": improvement,
                "current_value": current_value,
                "delta_value": delta_value,
                "new_value": new_value
            }
            
        except KeyError:
            print(f"Warning: Parameter '{parameter}' not found in team configuration")
            continue
        except Exception as e:
            print(f"Warning: Error processing parameter '{parameter}': {e}")
            continue
    
    return results


def _test_single_deltas_file(args_tuple):
    """Helper function to test a single deltas file - designed for parallel execution"""
    (deltas_file, team_dict, opponent_dict, points_per_test, base_serving, baseline_win_rate) = args_tuple
    
    import yaml
    from pathlib import Path
    
    # Load deltas file
    deltas_path = Path(deltas_file)
    if not deltas_path.exists():
        return deltas_file, None, f"Deltas file not found: {deltas_file}"
    
    try:
        with open(deltas_path, 'r') as f:
            deltas_data = yaml.safe_load(f)
        
        if not deltas_data:
            return deltas_file, None, f"Empty or invalid deltas file: {deltas_file}"
        
        # Recreate team objects from dictionaries (needed for multiprocessing)
        team = Team.from_dict(team_dict)
        opponent = Team.from_dict(opponent_dict)
        
        # Create modified team with ALL deltas applied together
        modified_team_data = copy.deepcopy(team_dict)
        
        # Apply all deltas from this file
        for parameter, delta_value in deltas_data.items():
            try:
                # Get current value
                current_value = get_nested_value(modified_team_data, parameter)
                if not isinstance(current_value, (int, float)):
                    print(f"Warning: Skipping non-numeric parameter '{parameter}' in {deltas_file}")
                    continue
                
                # Calculate new value (additive)
                new_value = current_value + delta_value
                
                # Apply delta improvement with probability adjustment
                modified_team_data = _adjust_probability_distribution(
                    modified_team_data, 
                    parameter, 
                    new_value
                )
                
            except KeyError:
                print(f"Warning: Parameter '{parameter}' not found in team configuration (file: {deltas_file})")
                continue
            except Exception as e:
                print(f"Warning: Error processing parameter '{parameter}' in {deltas_file}: {e}")
                continue
        
        # Create the modified team and calculate win rate
        modified_team = Team.from_dict(modified_team_data)
        file_win_rate = _calculate_win_rate(modified_team, opponent, points_per_test, base_serving)
        improvement = file_win_rate - baseline_win_rate
        
        # Use filename without extension as display name
        file_display_name = deltas_path.stem
        
        result = {
            "win_rate": file_win_rate,
            "improvement": improvement,
            "file_path": deltas_file,
            "deltas_count": len(deltas_data)
        }
        
        return deltas_file, result, None
        
    except Exception as e:
        return deltas_file, None, f"Error processing file {deltas_file}: {e}"


def multi_delta_skill_analysis(team: Team, opponent: Team, deltas_files: list, points_per_test: int = 100000,
                               base_serving: str = "A", parallel: bool = True) -> dict:
    """
    Analyze impact of applying all deltas from multiple files (each file applied as a complete set).
    
    Args:
        team: Base team configuration to improve
        opponent: Opponent team configuration
        deltas_files: List of YAML files with dot-notation improvements
        points_per_test: Number of points to simulate per test (default: 100000)
        base_serving: Which team serves ("A" or "B")
        parallel: Use parallel processing for file testing (default: True)
        
    Returns:
        Dictionary with baseline and results for each delta file
    """
    from pathlib import Path
    
    # Calculate baseline win rate
    baseline_win_rate = _calculate_win_rate(team, opponent, points_per_test, base_serving)
    
    results = {
        "baseline_win_rate": baseline_win_rate,
        "file_results": {}
    }
    
    # Only use parallel processing for larger workloads where the overhead is worth it
    if parallel and len(deltas_files) > 1 and points_per_test >= 50000:
        # Parallel processing using ProcessPoolExecutor for CPU-bound simulation work
        team_dict = team.to_dict()
        opponent_dict = opponent.to_dict()
        
        # Prepare arguments for parallel execution
        file_args = [
            (deltas_file, team_dict, opponent_dict, points_per_test, base_serving, baseline_win_rate)
            for deltas_file in deltas_files
        ]
        
        # Use number of CPU cores, but cap at reasonable maximum
        max_workers = min(multiprocessing.cpu_count(), len(deltas_files), 8)
        
        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all file tests
                future_to_file = {
                    executor.submit(_test_single_deltas_file, args): args[0]
                    for args in file_args
                }
                
                # Collect results as they complete
                completed_count = 0
                total_files = len(deltas_files)
                
                for future in as_completed(future_to_file):
                    completed_count += 1
                    deltas_file, result, error = future.result()
                    
                    if error:
                        print(f"Warning: {error}")
                    elif result is not None:
                        file_display_name = Path(deltas_file).stem
                        results["file_results"][file_display_name] = result
                    
                    # Progress indicator - only show if not formatting as JSON
                    import sys
                    if sys.stdout.isatty():
                        print(f"Progress: {completed_count}/{total_files} files tested")
        
        except (OSError, RuntimeError) as e:
            # ProcessPoolExecutor failed, fall back to sequential processing
            print(f"Warning: Parallel processing failed ({e}), falling back to sequential")
            parallel = False
    
    if not parallel or len(deltas_files) <= 1 or points_per_test < 50000:
        # Sequential processing (fallback or when parallel=False/not applicable)
        for deltas_file in deltas_files:
            deltas_file, result, error = _test_single_deltas_file((
                deltas_file, team.to_dict(), opponent.to_dict(), 
                points_per_test, base_serving, baseline_win_rate
            ))
            
            if error:
                print(f"Warning: {error}")
            elif result is not None:
                file_display_name = Path(deltas_file).stem
                results["file_results"][file_display_name] = result
    
    return results


def _test_single_parameter(args_tuple):
    """Helper function to test a single parameter - designed for parallel execution"""
    (parameter, current_value, team_dict, opponent_dict, change_value, 
     points_per_test, base_serving, baseline_win_rate) = args_tuple
    
    try:
        # Recreate team objects from dictionaries (needed for multiprocessing)
        team = Team.from_dict(team_dict)
        opponent = Team.from_dict(opponent_dict)
        
        # Calculate new value (additive)
        new_value = current_value + change_value
        
        # Create modified team
        modified_team_data = copy.deepcopy(team_dict)
        
        # Apply parameter improvement with probability adjustment
        modified_team_data = _adjust_probability_distribution(
            modified_team_data, 
            parameter, 
            new_value
        )
        modified_team = Team.from_dict(modified_team_data)
        
        # Calculate win rate with parameter improvement
        new_win_rate = _calculate_win_rate(modified_team, opponent, points_per_test, base_serving)
        improvement = new_win_rate - baseline_win_rate
        
        return parameter, {
            "win_rate": new_win_rate,
            "improvement": improvement,
            "current_value": current_value,
            "change_value": change_value,
            "new_value": new_value
        }
        
    except Exception as e:
        print(f"Warning: Error processing parameter '{parameter}': {e}")
        return parameter, None


def full_skill_analysis(team: Team, opponent: Team, change_value: float, points_per_test: int = 100000,
                       base_serving: str = "A", parallel: bool = True) -> dict:
    """
    Analyze impact of changing every probability parameter by a fixed amount.
    
    Args:
        team: Base team configuration to improve
        opponent: Opponent team configuration
        change_value: Amount to add to each probability (e.g., 0.05 for 5%)
        points_per_test: Number of points to simulate per test (default: 100000)
        base_serving: Which team serves ("A" or "B")
        parallel: Use parallel processing for parameter testing (default: True)
        
    Returns:
        Dictionary with baseline and all parameter results
    """
    # Calculate baseline win rate
    baseline_win_rate = _calculate_win_rate(team, opponent, points_per_test, base_serving)
    
    # Get all numeric probability parameters
    team_dict = team.to_dict()
    opponent_dict = opponent.to_dict()
    
    def extract_probability_params(d, prefix=''):
        """Extract all numeric probability parameters with dot notation paths"""
        params = {}
        for key, value in d.items():
            current_path = f'{prefix}.{key}' if prefix else key
            if isinstance(value, dict):
                params.update(extract_probability_params(value, current_path))
            elif isinstance(value, (int, float)) and 'probabilities' in prefix:
                params[current_path] = value
        return params
    
    all_params = extract_probability_params(team_dict)
    
    results = {
        "baseline_win_rate": baseline_win_rate,
        "change_value": change_value,
        "parameter_improvements": {},
        "total_parameters": len(all_params)
    }
    
    # Only use parallel processing for larger workloads where the overhead is worth it
    if parallel and len(all_params) > 1 and points_per_test >= 50000:
        # Parallel processing using ProcessPoolExecutor for CPU-bound simulation work
        # Prepare arguments for parallel execution
        param_args = [
            (parameter, current_value, team_dict, opponent_dict, change_value,
             points_per_test, base_serving, baseline_win_rate)
            for parameter, current_value in all_params.items()
        ]
        
        # Use number of CPU cores, but cap at reasonable maximum
        max_workers = min(multiprocessing.cpu_count(), len(all_params), 8)
        
        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all parameter tests
                future_to_param = {
                    executor.submit(_test_single_parameter, args): args[0]
                    for args in param_args
                }
                
                # Collect results as they complete
                completed_count = 0
                total_params = len(all_params)
                
                for future in as_completed(future_to_param):
                    completed_count += 1
                    parameter_name, result = future.result()
                    
                    if result is not None:
                        results["parameter_improvements"][parameter_name] = result
                    
                    # Optional progress indicator (every 10 parameters) - only show if not formatting as JSON
                    if completed_count % 10 == 0 or completed_count == total_params:
                        import sys
                        # Only print progress if stdout is a terminal (not being captured)
                        if sys.stdout.isatty():
                            print(f"Progress: {completed_count}/{total_params} parameters tested")
        
        except (OSError, RuntimeError) as e:
            # ProcessPoolExecutor failed, fall back to sequential processing
            print(f"Warning: Parallel processing failed ({e}), falling back to sequential")
            parallel = False
    
    if not parallel or len(all_params) <= 1 or points_per_test < 50000:
        # Sequential processing (fallback or when parallel=False/not applicable)
        for parameter, current_value in all_params.items():
            try:
                # Calculate new value (additive)
                new_value = current_value + change_value
                
                # Create modified team
                modified_team_data = copy.deepcopy(team.to_dict())
                
                # Apply parameter improvement with probability adjustment
                modified_team_data = _adjust_probability_distribution(
                    modified_team_data, 
                    parameter, 
                    new_value
                )
                modified_team = Team.from_dict(modified_team_data)
                
                # Calculate win rate with parameter improvement
                new_win_rate = _calculate_win_rate(modified_team, opponent, points_per_test, base_serving)
                improvement = new_win_rate - baseline_win_rate
                
                results["parameter_improvements"][parameter] = {
                    "win_rate": new_win_rate,
                    "improvement": improvement,
                    "current_value": current_value,
                    "change_value": change_value,
                    "new_value": new_value
                }
                
            except Exception as e:
                print(f"Warning: Error processing parameter '{parameter}': {e}")
                continue
    
    return results


def get_nested_value(data: dict, path: str) -> Any:
    """Get value from nested dictionary using dot notation"""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise KeyError(f"Path '{path}' not found in data")
    return value


def set_nested_value(data: dict, path: str, value: Any) -> dict:
    """Set value in nested dictionary using dot notation"""
    keys = path.split('.')
    current = data
    
    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the final value
    current[keys[-1]] = value
    return data


def sensitivity_analysis(team: Team, opponent: Team, parameter: str, 
                        param_range: str, points_per_test: int = 1000,
                        base_serving: str = "A") -> SensitivityResults:
    """
    Perform sensitivity analysis on a team parameter.
    
    Args:
        team: Base team configuration
        opponent: Opponent team configuration
        parameter: Parameter path to vary (e.g., "attack_probabilities.excellent_set.kill")
        param_range: Range specification "min,max,step" (e.g., "0.7,0.95,0.05")
        points_per_test: Number of points to simulate per parameter value
        base_serving: Which team serves ("A" or "B")
        
    Returns:
        Sensitivity analysis results
    """
    # Parse range
    try:
        min_val, max_val, step = map(float, param_range.split(','))
    except ValueError:
        raise ValueError(f"Invalid range format: {param_range}. Expected 'min,max,step'")
    
    # Get base value and validate parameter exists
    try:
        base_value = get_nested_value(team.to_dict(), parameter)
    except KeyError:
        raise ValueError(f"Parameter '{parameter}' not found in team configuration")
    
    if not isinstance(base_value, (int, float)):
        raise ValueError(f"Parameter '{parameter}' must be numeric, got {type(base_value)}")
    
    # Calculate base win rate
    base_win_rate = _calculate_win_rate(team, opponent, points_per_test, base_serving)
    
    # Generate parameter values to test
    param_values = []
    current = min_val
    while current <= max_val + (step / 2):  # Add small epsilon for floating point comparison
        param_values.append(round(current, 3))  # Round to avoid floating point issues
        current += step
    
    # Ensure base value is included
    if base_value not in [round(v, 3) for v in param_values]:
        param_values.append(round(base_value, 3))
        param_values.sort()
    
    # Test each parameter value
    data_points = []
    for param_value in param_values:
        # Create modified team
        modified_team_data = copy.deepcopy(team.to_dict())
        
        # Adjust probabilities to maintain valid distribution
        modified_team_data = _adjust_probability_distribution(modified_team_data, parameter, param_value)
        modified_team = Team.from_dict(modified_team_data)
        
        # Calculate win rate
        win_rate = _calculate_win_rate(modified_team, opponent, points_per_test, base_serving)
        change_from_base = win_rate - base_win_rate
        
        data_points.append(SensitivityDataPoint(
            parameter_value=param_value,
            win_rate=win_rate,
            change_from_base=change_from_base
        ))
    
    # Calculate impact factor
    changes = [abs(p.change_from_base) for p in data_points]
    max_change = max(changes) if changes else 0
    
    if max_change < 2.0:
        impact_factor = "LOW"
    elif max_change < 5.0:
        impact_factor = "MEDIUM"
    else:
        impact_factor = "HIGH"
    
    return SensitivityResults(
        parameter_name=parameter,
        base_win_rate=base_win_rate,
        data_points=data_points,
        impact_factor=impact_factor
    )


def _calculate_win_rate(team_a: Team, team_b: Team, num_points: int, base_serving: str) -> float:
    """Calculate win rate for team A over specified number of points"""
    wins = 0
    
    for i in range(num_points):
        # Alternate serving
        serving_team = base_serving if i % 2 == 0 else ("B" if base_serving == "A" else "A")
        point = simulate_point(team_a, team_b, serving_team=serving_team, seed=None)
        if point.winner == "A":
            wins += 1
    
    return (wins / num_points) * 100 if num_points > 0 else 0


def _adjust_probability_distribution(team_data: dict, parameter: str, new_value: float) -> dict:
    """
    Adjust probability distribution to maintain sum = 1.0 when changing one parameter.
    This implements a simple proportional adjustment strategy.
    """
    # Get the parent path and key
    path_parts = parameter.split('.')
    parent_path = '.'.join(path_parts[:-1])
    target_key = path_parts[-1]
    
    try:
        # Get the parent distribution
        parent_dist = get_nested_value(team_data, parent_path)
        
        if not isinstance(parent_dist, dict):
            # If it's not a distribution, just set the value
            set_nested_value(team_data, parameter, new_value)
            return team_data
        
        # Get current values
        old_value = parent_dist.get(target_key, 0)
        
        # Calculate adjustment needed
        adjustment = new_value - old_value
        
        # If no adjustment needed, return as-is
        if abs(adjustment) < 0.001:
            return team_data
        
        # Get other keys to adjust
        other_keys = [k for k in parent_dist.keys() if k != target_key]
        
        if not other_keys:
            # Only one key, just set it
            set_nested_value(team_data, parameter, new_value)
            return team_data
        
        # Calculate current sum of other values
        other_sum = sum(parent_dist[k] for k in other_keys)
        
        if other_sum <= 0:
            # Can't adjust other values, just set the target
            set_nested_value(team_data, parameter, new_value)
            return team_data
        
        # Proportionally adjust other values
        remaining_probability = 1.0 - new_value
        
        if remaining_probability < 0:
            remaining_probability = 0
        
        # Scale other values proportionally
        for key in other_keys:
            old_other_value = parent_dist[key]
            new_other_value = (old_other_value / other_sum) * remaining_probability
            set_nested_value(team_data, f"{parent_path}.{key}", max(0, new_other_value))
        
        # Set the target value
        set_nested_value(team_data, parameter, new_value)
        
        return team_data
        
    except KeyError:
        # If path doesn't exist, just set the value
        set_nested_value(team_data, parameter, new_value)
        return team_data