#!/usr/bin/env python3
"""
Command-line interface for bvsim_stats library.
Implements CLI commands as defined in contracts/bvsim-stats-cli.md
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .models import SimulationResults
from .analysis import analyze_simulation_results, sensitivity_analysis, delta_skill_analysis, full_skill_analysis
from bvsim_core.team import Team


def cmd_analyze_results(args):
    """Handle analyze-results command"""
    try:
        # Load simulation results
        results = SimulationResults.from_json_file(args.simulation)
        
        # Perform analysis
        analysis = analyze_simulation_results(results, breakdown=args.breakdown)
        
        # Output results
        if args.format == 'json':
            output = analysis.to_dict()
            print(json.dumps(output, indent=2))
        else:
            # Text format
            text_output = analysis.to_text(results.team_a_name, results.team_b_name)
            print(text_output)
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print("Invalid simulation data", file=sys.stderr)
        print(f"JSON parsing error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print("Invalid simulation data", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_skill_analysis(args):
    """Handle skill-analysis command"""
    try:
        # Load teams with defaults
        if args.team:
            team = Team.from_yaml_file(args.team)
        else:
            # Default to basic template
            from bvsim_cli.templates import get_basic_template
            team = Team.from_dict(get_basic_template("Default Team"))
        
        if args.opponent:
            opponent = Team.from_yaml_file(args.opponent)
        else:
            # Default to same team as base team
            opponent = team
        
        # Choose analysis type based on --full parameter
        if hasattr(args, 'full') and args.full:
            # Parse change value (support both 0.05 and 5% formats)
            change_str = args.full
            if change_str.endswith('%'):
                change_value = float(change_str[:-1]) / 100.0
            else:
                change_value = float(change_str)
            
            # Perform full skill analysis
            results = full_skill_analysis(
                team=team,
                opponent=opponent,
                change_value=change_value,
                points_per_test=args.points
            )
            
            # Output results
            if args.format == 'json':
                print(json.dumps(results, indent=2))
            else:
                # Text format for full analysis
                change_pct = change_value * 100
                print(f"Full Skill Impact Analysis ({args.points} points each):")
                print(f"Testing {results['total_parameters']} parameters with {change_pct:+.1f}% change each")
                print(f"Baseline win rate: {results['baseline_win_rate']:.1f}%")
                print("")
                
                # Sort parameters by improvement impact
                sorted_params = sorted(
                    results['parameter_improvements'].items(),
                    key=lambda x: x[1]['improvement'],
                    reverse=True
                )
                
                # Print table header
                print(f"{'Rank':<4} {'Parameter':<50} {'Win Rate':<9} {'Improvement':<12} {'Current→New'}")
                print("-" * 90)
                
                for i, (parameter, data) in enumerate(sorted_params, 1):
                    improvement = data['improvement']
                    win_rate = data['win_rate']
                    current = data['current_value']
                    new_val = data['new_value']
                    
                    # Truncate long parameter names for better table formatting
                    display_param = parameter
                    display_param = display_param.replace("block_probabilities.power_attack.deflection_to_defense", "block_probabilities.power_attack.deflection_to_d")
                    display_param = display_param.replace("block_probabilities.power_attack.deflection_to_attack", "block_probabilities.power_attack.deflection_to_a")
                    
                    print(f"{i:<4} {display_param:<50} {win_rate:<8.1f}% {improvement:+8.1f}% "
                          f"{current:.3f}→{new_val:.3f}")
                
                print(f"\nAnalysis completed. Each test simulated {args.points} points.")
                
        else:
            # Perform delta skill analysis (original behavior)
            results = delta_skill_analysis(
                team=team,
                opponent=opponent,
                deltas_file=args.deltas,
                points_per_test=args.points
            )
            
            # Output results
            if args.format == 'json':
                print(json.dumps(results, indent=2))
            else:
                # Text format for delta analysis
                print(f"Skill Impact Analysis ({args.points} points each):")
                print(f"Baseline win rate: {results['baseline_win_rate']:.1f}%")
                print("")
                
                # Sort deltas by improvement impact
                sorted_deltas = sorted(
                    results['delta_improvements'].items(),
                    key=lambda x: x[1]['improvement'],
                    reverse=True
                )
                
                for i, (parameter, data) in enumerate(sorted_deltas, 1):
                    improvement = data['improvement']
                    win_rate = data['win_rate']
                    current = data['current_value']
                    delta = data['delta_value']
                    new_val = data['new_value']
                    print(f"{i}. {parameter}: {win_rate:.1f}% ({improvement:+.1f}% improvement)")
                    print(f"   Change: {current:.3f} + {delta:.3f} = {new_val:.3f}")
                
                print(f"\nAnalysis completed. Each test simulated {args.points} points.")
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("Invalid configuration or parameter", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print("Invalid configuration or parameter", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_sensitivity_analysis(args):
    """Handle sensitivity-analysis command"""
    try:
        # Load teams
        team = Team.from_yaml_file(args.team)
        opponent = Team.from_yaml_file(args.opponent)
        
        # Perform sensitivity analysis
        sensitivity = sensitivity_analysis(
            team=team,
            opponent=opponent,
            parameter=args.parameter,
            param_range=args.range,
            points_per_test=args.points
        )
        
        # Output results
        if args.format == 'json':
            output = sensitivity.to_dict()
            print(json.dumps(output, indent=2))
        else:
            # Text format
            text_output = sensitivity.to_text(team.name)
            print(text_output)
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("Invalid configuration or parameter", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print("Invalid configuration or parameter", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def main(argv=None):
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        prog='bvsim_stats',
        description='Beach volleyball simulation statistical analysis'
    )
    parser.add_argument('--version', action='version', version=f'bvsim_stats {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # analyze-results command
    parser_analyze = subparsers.add_parser('analyze-results', help='Analyze simulation results and generate statistics')
    parser_analyze.add_argument('--simulation', required=True, help='JSON file containing simulation results')
    parser_analyze.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_analyze.add_argument('--breakdown', action='store_true', help='Include detailed breakdown by point type')
    parser_analyze.set_defaults(func=cmd_analyze_results)
    
    # sensitivity-analysis command
    parser_sensitivity = subparsers.add_parser('sensitivity-analysis', help='Perform sensitivity analysis on team parameters')
    parser_sensitivity.add_argument('--team', required=True, help='Base team YAML configuration')
    parser_sensitivity.add_argument('--parameter', required=True, help='Parameter to vary (e.g., "attack_probabilities.excellent_set.kill")')
    parser_sensitivity.add_argument('--range', required=True, help='Range to test (e.g., "0.7,0.95,0.05")')
    parser_sensitivity.add_argument('--opponent', required=True, help='Opponent team YAML configuration')
    parser_sensitivity.add_argument('--points', type=int, default=1000, help='Points per test (default: 1000)')
    parser_sensitivity.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_sensitivity.set_defaults(func=cmd_sensitivity_analysis)
    
    # skill-analysis command
    parser_skill = subparsers.add_parser('skill-analysis', help='Analyze impact of specific skill improvements')
    parser_skill.add_argument('--team', help='Base team YAML configuration to improve (default: basic template)')
    parser_skill.add_argument('--opponent', help='Opponent team YAML configuration (default: same as --team)')
    
    # Create mutually exclusive group for deltas vs full analysis
    analysis_group = parser_skill.add_mutually_exclusive_group(required=True)
    analysis_group.add_argument('--deltas', help='YAML file with specific improvements (dot notation, e.g., serve_probabilities.ace: 0.05)')
    analysis_group.add_argument('--full', help='Test all parameters with fixed change (e.g., "0.05" or "5%%")')
    
    parser_skill.add_argument('--points', type=int, default=100000, help='Points per test (default: 100000)')
    parser_skill.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_skill.set_defaults(func=cmd_skill_analysis)
    
    # Parse arguments
    if not argv:
        parser.print_help()
        return 0
    
    args = parser.parse_args(argv)
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 0
    
    # Execute command
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