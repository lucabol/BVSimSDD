#!/usr/bin/env python3
"""
Unified CLI for BVSim - Beach Volleyball Point Simulator
Consolidates functionality from bvsim_core, bvsim_stats, and bvsim_cli
"""

import argparse
import json
import sys
import glob
from pathlib import Path
from typing import List, Optional

from . import __version__
from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_stats.models import SimulationResults
from bvsim_stats.analysis import analyze_simulation_results, delta_skill_analysis, full_skill_analysis, sensitivity_analysis, multi_delta_skill_analysis
from bvsim_cli.templates import get_basic_template, get_advanced_template, create_team_template
from bvsim_cli.comparison import compare_teams


def auto_discover_teams() -> List[str]:
    """Auto-discover team YAML files in current directory"""
    team_files = []
    patterns = ['team_*.yaml', 'team_*.yml', '*.yaml', '*.yml']
    
    for pattern in patterns:
        files = glob.glob(pattern)
        team_files.extend([f for f in files if f not in team_files])
    
    # Filter to only valid team files
    valid_teams = []
    for file in team_files:
        try:
            Team.from_yaml_file(file)
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
        
        # Determine points based on speed option
        if args.quick:
            points = 10000
        elif args.accurate:
            points = 200000
        else:
            points = args.points or 100000
        
        # Determine analysis type
        if args.custom:
            # Multi-file custom deltas analysis
            results = multi_delta_skill_analysis(
                team=team,
                opponent=opponent,
                deltas_files=args.custom,
                points_per_test=points
            )
            
            # Output results
            if args.format == 'json':
                print(json.dumps(results, indent=2))
            else:
                file_count = len(results['file_results'])
                file_names = ', '.join(args.custom)
                print(f"Multi-File Skill Impact Analysis ({points:,} points each):")
                print(f"Testing {file_count} custom improvement files: {file_names}")
                print(f"Baseline win rate: {results['baseline_win_rate']:.1f}%")
                print("")
                
                # Sort files by improvement (descending)
                sorted_files = sorted(
                    results['file_results'].items(),
                    key=lambda x: x[1]['improvement'],
                    reverse=True
                )
                
                # Calculate max file name width for proper table formatting
                if sorted_files:
                    max_name_width = max(len(file_name) for file_name, _ in sorted_files)
                    name_width = max(15, min(max_name_width, 40))  # Min 15, max 40 chars
                else:
                    name_width = 15
                
                # Calculate total table width
                total_width = 4 + 1 + name_width + 1 + 9 + 1 + 12  # rank + space + name + space + win_rate + space + improvement
                
                print(f"{'Rank':<4} {'Configuration':<{name_width}} {'Win Rate':<9} {'Improvement'}")
                print("-" * total_width)
                
                for i, (file_name, data) in enumerate(sorted_files, 1):
                    improvement = data['improvement']
                    win_rate = data['win_rate']
                    
                    print(f"{i:<4} {file_name:<{name_width}} {win_rate:<8.1f}% {improvement:+8.1f}%")
                
                print(f"\nAnalysis completed. Each test simulated {points:,} points.")
                print(f"Each configuration applies all deltas from its file together.")
        else:
            # Full parameter analysis
            change_value = args.improve or 0.05
            if isinstance(change_value, str):
                if change_value.endswith('%'):
                    change_value = float(change_value[:-1]) / 100.0
                else:
                    change_value = float(change_value)
            
            results = full_skill_analysis(
                team=team,
                opponent=opponent,
                change_value=change_value,
                points_per_test=points,
                parallel=not args.no_parallel
            )
            
            # Output results
            if args.format == 'json':
                print(json.dumps(results, indent=2))
            else:
                change_pct = change_value * 100
                print(f"Skill Impact Analysis ({points:,} points each):")
                print(f"Testing {results['total_parameters']} parameters with {change_pct:+.1f}% improvement")
                print(f"Baseline win rate: {results['baseline_win_rate']:.1f}%")
                print("")
                
                sorted_params = sorted(
                    results['parameter_improvements'].items(),
                    key=lambda x: x[1]['improvement'],
                    reverse=True
                )
                
                # Process parameter names and calculate max width
                display_params = []
                for parameter, data in sorted_params:
                    display_param = parameter
                    display_param = display_param.replace("block_probabilities.power_attack.deflection_to_defense", "block_probabilities.power_attack.deflection_to_d")
                    display_param = display_param.replace("block_probabilities.power_attack.deflection_to_attack", "block_probabilities.power_attack.deflection_to_a")
                    display_params.append((display_param, data))
                
                # Calculate the maximum parameter name width
                max_param_width = max(len(param) for param, _ in display_params)
                # Ensure minimum width and reasonable maximum
                param_width = max(30, min(max_param_width, 60))
                
                # Calculate total table width
                total_width = 4 + 1 + param_width + 1 + 9 + 1 + 12  # rank + space + param + space + win_rate + space + improvement
                
                print(f"{'Rank':<4} {'Parameter':<{param_width}} {'Win Rate':<9} {'Improvement'}")
                print("-" * total_width)
                
                for i, (display_param, data) in enumerate(display_params, 1):
                    improvement = data['improvement']
                    win_rate = data['win_rate']
                    
                    print(f"{i:<4} {display_param:<{param_width}} {win_rate:<8.1f}% {improvement:+8.1f}%")
                
                print(f"\nAnalysis completed. Each test simulated {points:,} points.")
                print(f"Focus training on top-ranked skills for maximum impact.")
        
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
        print(f"Format: [Winner] Server→Action(Quality)→Action(Quality)... → Point Type")
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
                
                state_parts.append(f"{state.team}→{action_abbrev}({quality_abbrev})")
            
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
    parser_skills.add_argument('--custom', nargs='+', help='YAML files with custom improvements (multiple files supported)')
    parser_skills.add_argument('--quick', action='store_true', help='Fast analysis (10k points)')
    parser_skills.add_argument('--accurate', action='store_true', help='High precision (200k points)')
    parser_skills.add_argument('--points', type=int, help='Custom points per test')
    parser_skills.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_skills.add_argument('--no-parallel', action='store_true', help='Disable parallel processing (for testing)')
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