#!/usr/bin/env python3
"""
Team configuration validation for beach volleyball simulation.
Validates that probability distributions are properly formed and sum to 1.0.
"""

from typing import List, Dict, Any
from .team import Team


def validate_probability_distribution(name: str, probs: Dict[str, float], expected_sum: float = 1.0, tolerance: float = 0.001) -> List[str]:
    """
    Validate that a probability distribution sums to expected value.
    
    Args:
        name: Name of the distribution for error messages
        probs: Dictionary of outcome -> probability
        expected_sum: Expected sum (default 1.0)
        tolerance: Acceptable deviation from expected sum
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not probs:
        errors.append(f"{name}: Empty probability distribution")
        return errors
    
    # Check individual probabilities are valid
    for outcome, prob in probs.items():
        if not isinstance(prob, (int, float)):
            errors.append(f"{name}.{outcome}: Probability must be a number, got {type(prob)}")
        elif prob < 0:
            errors.append(f"{name}.{outcome}: Probability cannot be negative ({prob})")
        elif prob > 1:
            errors.append(f"{name}.{outcome}: Probability cannot exceed 1.0 ({prob})")
    
    # Check sum
    total = sum(probs.values())
    if abs(total - expected_sum) > tolerance:
        errors.append(f"{name}: Probabilities must sum to {expected_sum}, got {total:.4f}")
    
    return errors


def validate_conditional_distribution(name: str, cond_probs: Dict[str, Dict[str, float]]) -> List[str]:
    """
    Validate conditional probability distributions.
    
    Args:
        name: Name of the distribution for error messages
        cond_probs: Dictionary of condition -> {outcome -> probability}
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not cond_probs:
        errors.append(f"{name}: Empty conditional probability distribution")
        return errors
    
    for condition, probs in cond_probs.items():
        if not isinstance(probs, dict):
            errors.append(f"{name}.{condition}: Must be a dictionary, got {type(probs)}")
            continue
            
        condition_errors = validate_probability_distribution(f"{name}.{condition}", probs)
        errors.extend(condition_errors)
    
    return errors


def validate_team_configuration(team: Team) -> List[str]:
    """
    Validate a complete team configuration.
    
    Args:
        team: Team object to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Validate team name
    if not team.name or not isinstance(team.name, str):
        errors.append("Team name must be a non-empty string")
    
    # Validate serve probabilities (simple distribution)
    serve_errors = validate_probability_distribution("serve_probabilities", team.serve_probabilities)
    errors.extend(serve_errors)
    
    # Validate conditional distributions
    conditional_distributions = [
        ("receive_probabilities", team.receive_probabilities),
        ("set_probabilities", team.set_probabilities),
        ("attack_probabilities", team.attack_probabilities), 
        ("block_probabilities", team.block_probabilities),
        ("dig_probabilities", team.dig_probabilities)
    ]
    
    for dist_name, dist_data in conditional_distributions:
        cond_errors = validate_conditional_distribution(dist_name, dist_data)
        errors.extend(cond_errors)
    
    return errors