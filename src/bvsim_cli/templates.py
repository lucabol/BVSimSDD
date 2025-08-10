#!/usr/bin/env python3
"""
Team configuration templates for creating new teams.
"""

import yaml
from pathlib import Path


# Cache for loaded templates
_template_cache = {}


def _get_template_path(template_name: str) -> Path:
    """Get path to template file"""
    # Look for templates directory relative to this file
    current_file = Path(__file__).parent
    
    # Try multiple possible locations for templates directory
    possible_paths = [
        current_file / ".." / ".." / ".." / "templates" / f"{template_name}_team_template.yaml",  # From src/bvsim_cli/
        current_file / ".." / ".." / "templates" / f"{template_name}_team_template.yaml",        # From src/
        Path.cwd() / "templates" / f"{template_name}_team_template.yaml",                       # From current directory
    ]
    
    for template_path in possible_paths:
        template_path = template_path.resolve()
        if template_path.exists():
            return template_path
    
    # If no template found, raise an error
    raise FileNotFoundError(f"Could not find {template_name}_team_template.yaml in any of these locations: {[str(p) for p in possible_paths]}")


def _load_template(template_name: str) -> dict:
    """Load template from YAML file with caching"""
    if template_name not in _template_cache:
        template_path = _get_template_path(template_name)
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        _template_cache[template_name] = template_data
    
    return _template_cache[template_name].copy()


def get_basic_template(team_name: str) -> dict:
    """Get basic team template with standard probabilities"""
    template = _load_template("basic")
    template['name'] = team_name
    return template


def get_advanced_template(team_name: str) -> dict:
    """Get advanced team template with detailed probability matrices"""
    template = _load_template("advanced")
    template['name'] = team_name
    return template


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