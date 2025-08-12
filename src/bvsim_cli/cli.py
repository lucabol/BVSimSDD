#!/usr/bin/env python3
"""
Command-line interface for bvsim_cli library.
Implements CLI commands as defined in contracts/bvsim-cli.md
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .templates import create_team_template
from . import templates as templates_module
from .simulation import run_large_simulation, format_simulation_summary
from .comparison import compare_teams, format_comparison_text
from bvsim_core.team import Team


def cmd_create_team(args):
    """Handle create-team command"""
    try:
        output_file = create_team_template(
            team_name=args.name,
            template_type=args.template,
            output_file=args.output,
            interactive=args.interactive
        )
        
        print(f"Team configuration created: {output_file}")
        print(f"Template type: {args.template}")
        print(f"Team name: {args.name}")
        
        return 0
        
    except ValueError as e:
        print("Invalid arguments or template", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except IOError as e:
        print("File write error", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Invalid arguments", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 3


def cmd_run_simulation(args):
    """Handle run-simulation command"""
    try:
        # Load teams
        team_a = Team.from_yaml_file(args.team_a)
        team_b = Team.from_yaml_file(args.team_b)
        
        # Display simulation info
        if args.format == "text":
            print(f"Running simulation: {args.points} points")
            print(f"Team A: {team_a.name}")
            print(f"Team B: {team_b.name}")
        
        # Run simulation
        results = run_large_simulation(
            team_a=team_a,
            team_b=team_b,
            num_points=args.points,
            seed=args.seed,
            show_progress=args.progress and args.format == "text"
        )
        
        # Handle output
        if args.output:
            # Write JSON results to file
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            
            if args.format == "text":
                print()
                print(format_simulation_summary(results))
                print(f"Results saved to: {args.output}")
        else:
            # Output to stdout
            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                print()
                print(format_simulation_summary(results))
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found or write error", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Invalid team configuration", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_compare_teams(args):
    """Handle compare-teams command"""
    try:
        # Parse team identifiers (file paths or template keywords)
        team_items = [f.strip() for f in args.teams.split(',')]
        
        if len(team_items) < 2:
            raise ValueError("Need at least 2 teams for comparison")
        
        # Load teams (support special values Basic / Advanced referencing templates)
        teams = []
        for item in team_items:
            lowered = item.lower()
            if lowered in ("basic", "advanced"):
                # Use template to build a team object without writing a file
                if lowered == "basic":
                    data = templates_module.get_basic_template(team_name=item.capitalize())
                else:
                    data = templates_module.get_advanced_template(team_name=item.capitalize())
                team = Team.from_dict(data)
            else:
                # Treat as file path
                team = Team.from_yaml_file(item)
            teams.append(team)
        
        # Run comparison
        comparison_results = compare_teams(teams, args.points)
        
        # Output results
        if args.format == "json":
            print(json.dumps(comparison_results, indent=2))
        else:
            print(format_comparison_text(comparison_results))
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("Invalid team configuration", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print("Invalid arguments", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 3


def main(argv=None):
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        prog='bvsim_cli',
        description='Beach volleyball simulation command-line interface'
    )
    parser.add_argument('--version', action='version', version=f'bvsim_cli {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # create-team command
    parser_create = subparsers.add_parser('create-team', help='Interactive team configuration creation')
    parser_create.add_argument('--name', required=True, help='Team name')
    parser_create.add_argument('--output', help='Output file (default: <name>.yaml)')
    parser_create.add_argument('--template', choices=['basic', 'advanced'], default='basic', 
                              help='Configuration template (default: basic)')
    parser_create.add_argument('--interactive', action='store_true', help='Interactive mode with prompts')
    parser_create.set_defaults(func=cmd_create_team)
    
    # run-simulation command
    parser_sim = subparsers.add_parser('run-simulation', help='Run large-scale point simulation')
    parser_sim.add_argument('--team-a', required=True, help='Team A YAML configuration')
    parser_sim.add_argument('--team-b', required=True, help='Team B YAML configuration')
    parser_sim.add_argument('--points', type=int, required=True, help='Number of points to simulate')
    parser_sim.add_argument('--output', help='Output file for results (default: stdout)')
    parser_sim.add_argument('--progress', action='store_true', help='Show progress bar')
    parser_sim.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser_sim.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_sim.set_defaults(func=cmd_run_simulation)
    
    # compare-teams command
    parser_compare = subparsers.add_parser('compare-teams', help='Compare multiple team configurations')
    parser_compare.add_argument('--teams', required=True, help='Comma-separated team YAML configuration files')
    parser_compare.add_argument('--points', type=int, default=1000, help='Points per matchup (default: 1000)')
    parser_compare.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_compare.add_argument('--matrix', action='store_true', help='Show full comparison matrix')
    parser_compare.set_defaults(func=cmd_compare_teams)
    
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