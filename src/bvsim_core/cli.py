#!/usr/bin/env python3
"""
Command-line interface for bvsim_core library.
Implements CLI commands as defined in contracts/bvsim-core-cli.md
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .team import Team
from .state_machine import simulate_point
from .validation import validate_team_configuration


def cmd_simulate_point(args):
    """Handle simulate-point command"""
    try:
        # Load teams from YAML files
        team_a = Team.from_yaml_file(args.team_a)
        team_b = Team.from_yaml_file(args.team_b)
        
        # Validate teams
        errors_a = validate_team_configuration(team_a)
        errors_b = validate_team_configuration(team_b)
        
        if errors_a or errors_b:
            print("Invalid team configuration", file=sys.stderr)
            if errors_a:
                print(f"Team A errors: {'; '.join(errors_a)}", file=sys.stderr)
            if errors_b:
                print(f"Team B errors: {'; '.join(errors_b)}", file=sys.stderr)
            return 1
        
        # Simulate point
        point = simulate_point(
            team_a=team_a,
            team_b=team_b, 
            serving_team=args.serving,
            seed=args.seed
        )
        
        # Output results
        if args.format == 'json':
            output = {
                "serving_team": point.serving_team,
                "winner": point.winner,
                "point_type": point.point_type,
                "duration": len(point.states),
                "states": [
                    {"team": s.team, "action": s.action, "quality": s.quality}
                    for s in point.states
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            # Text format
            states_str = " -> ".join([f"{s.team}:{s.action}({s.quality})" for s in point.states])
            print("Point Result:")
            print(f"Serving Team: {point.serving_team}")
            print(f"Winner: {point.winner}")
            print(f"Point Type: {point.point_type}")
            print(f"Duration: {len(point.states)} states")
            print(f"States: {states_str}")
        
        return 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Invalid team configuration", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def cmd_validate_team(args):
    """Handle validate-team command"""
    try:
        # Load team from YAML file
        team = Team.from_yaml_file(args.team)
        
        # Validate team
        errors = validate_team_configuration(team)
        
        if args.format == 'json':
            output = {
                "valid": len(errors) == 0,
                "team_name": team.name,
                "errors": errors
            }
            print(json.dumps(output, indent=2))
        else:
            # Text format
            if errors:
                print("Team validation: FAILED")
                print(f"Team: {team.name}")
                print("Errors:")
                for error in errors:
                    print(f"- {error}")
            else:
                print("Team validation: PASSED")
                print(f"Team: {team.name}")
                print("All probability distributions valid")
        
        # Return appropriate exit code
        return 1 if errors else 0
        
    except FileNotFoundError as e:
        print("File not found", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print("Invalid team configuration", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


def main(argv=None):
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        prog='bvsim_core',
        description='Beach volleyball point simulation core library'
    )
    parser.add_argument('--version', action='version', version=f'bvsim_core {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # simulate-point command
    parser_simulate = subparsers.add_parser('simulate-point', help='Simulate a single volleyball point')
    parser_simulate.add_argument('--team-a', required=True, help='YAML file containing Team A configuration')
    parser_simulate.add_argument('--team-b', required=True, help='YAML file containing Team B configuration')
    parser_simulate.add_argument('--serving', choices=['A', 'B'], default='A', help='Which team serves (default: A)')
    parser_simulate.add_argument('--seed', type=int, help='Random seed for reproducible results')
    parser_simulate.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_simulate.add_argument('--verbose', action='store_true', help='Include detailed state progression')
    parser_simulate.set_defaults(func=cmd_simulate_point)
    
    # validate-team command  
    parser_validate = subparsers.add_parser('validate-team', help='Validate team probability configuration')
    parser_validate.add_argument('--team', required=True, help='YAML file containing team configuration')
    parser_validate.add_argument('--format', choices=['json', 'text'], default='text', help='Output format')
    parser_validate.set_defaults(func=cmd_validate_team)
    
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