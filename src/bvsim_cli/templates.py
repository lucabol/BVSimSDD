#!/usr/bin/env python3
"""
Team configuration templates for creating new teams.
"""

import yaml
from pathlib import Path


def get_basic_template(team_name: str) -> dict:
    """Get basic team template with standard probabilities"""
    return {
        'name': team_name,
        'serve_probabilities': {
            'ace': 0.10,
            'in_play': 0.85,
            'error': 0.05
        },
        'receive_probabilities': {
            'in_play_serve': {
                'excellent': 0.35,
                'good': 0.40,
                'poor': 0.20,
                'error': 0.05
            }
        },
        'set_probabilities': {
            'excellent_reception': {
                'excellent': 0.69,
                'good': 0.25,
                'poor': 0.05,
                'error': 0.01
            },
            'good_reception': {
                'excellent': 0.28,
                'good': 0.60,
                'poor': 0.10,
                'error': 0.02
            },
            'poor_reception': {
                'excellent': 0.05,
                'good': 0.25,
                'poor': 0.67,
                'error': 0.03
            }
        },
        'attack_probabilities': {
            'excellent_set': {
                'kill': 0.70,
                'error': 0.15,
                'defended': 0.15
            },
            'good_set': {
                'kill': 0.55,
                'error': 0.20,
                'defended': 0.25
            },
            'poor_set': {
                'kill': 0.30,
                'error': 0.35,
                'defended': 0.35
            }
        },
        'block_probabilities': {
            'power_attack': {
                'stuff': 0.20,
                'deflection_to_attack': 0.15,
                'deflection_to_defense': 0.15,
                'no_touch': 0.50
            }
        },
        'dig_probabilities': {
            'deflected_attack': {
                'excellent': 0.30,
                'good': 0.40,
                'poor': 0.25,
                'error': 0.05
            }
        }
    }


def get_advanced_template(team_name: str) -> dict:
    """Get advanced team template with detailed probability matrices"""
    return {
        'name': team_name,
        'serve_probabilities': {
            'ace': 0.10,
            'in_play': 0.85,
            'error': 0.05
        },
        'receive_probabilities': {
            'in_play_serve': {
                'excellent': 0.35,
                'good': 0.40,
                'poor': 0.20,
                'error': 0.05
            }
        },
        'set_probabilities': {
            'excellent_reception': {
                'excellent': 0.74,
                'good': 0.20,
                'poor': 0.05,
                'error': 0.01
            },
            'good_reception': {
                'excellent': 0.33,
                'good': 0.55,
                'poor': 0.10,
                'error': 0.02
            },
            'poor_reception': {
                'excellent': 0.05,
                'good': 0.20,
                'poor': 0.72,
                'error': 0.03
            }
        },
        'attack_probabilities': {
            'excellent_set': {
                'kill': 0.80,
                'error': 0.10,
                'defended': 0.10
            },
            'good_set': {
                'kill': 0.60,
                'error': 0.15,
                'defended': 0.25
            },
            'poor_set': {
                'kill': 0.35,
                'error': 0.30,
                'defended': 0.35
            }
        },
        'block_probabilities': {
            'power_attack': {
                'stuff': 0.25,
                'deflection_to_attack': 0.175,
                'deflection_to_defense': 0.175,
                'no_touch': 0.40
            }
        },
        'dig_probabilities': {
            'deflected_attack': {
                'excellent': 0.35,
                'good': 0.40,
                'poor': 0.20,
                'error': 0.05
            }
        }
    }


def create_team_template(team_name: str, template_type: str = "basic", 
                        output_file: str = None, interactive: bool = False) -> str:
    """
    Create a team configuration file from template.
    
    Args:
        team_name: Name of the team
        template_type: "basic" or "advanced"
        output_file: Output file path (default: {name}.yaml)
        interactive: Whether to use interactive mode
        
    Returns:
        Path to created file
        
    Raises:
        ValueError: If invalid template type
        IOError: If file write fails
    """
    if template_type not in ["basic", "advanced"]:
        raise ValueError(f"Invalid template type: {template_type}. Must be 'basic' or 'advanced'")
    
    # Get template data
    if template_type == "basic":
        team_data = get_basic_template(team_name)
    else:
        team_data = get_advanced_template(team_name)
    
    # Interactive mode modifications
    if interactive:
        team_data = _interactive_team_creation(team_data)
    
    # Determine output file
    if output_file is None:
        # Sanitize team name for filename
        safe_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        output_file = f"{safe_name}.yaml"
    
    # Write to file
    try:
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            yaml.dump(team_data, f, default_flow_style=False, indent=2, sort_keys=False)
        
        return str(output_path)
        
    except IOError as e:
        raise IOError(f"Failed to write team configuration: {e}")


def _interactive_team_creation(team_data: dict) -> dict:
    """
    Interactive team creation (basic implementation).
    In a full implementation, this would prompt for key probability adjustments.
    """
    print(f"Creating team: {team_data['name']}")
    print("Interactive mode is a basic implementation - using template defaults.")
    print("To customize probabilities, edit the generated YAML file manually.")
    
    # For now, just return the template as-is
    # In a full implementation, we might prompt for key probabilities
    return team_data