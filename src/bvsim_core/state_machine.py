#!/usr/bin/env python3
"""
Beach volleyball point simulation state machine.
Implements the core logic for simulating individual volleyball points using conditional probabilities.
"""

import random
from typing import Optional
from .team import Team
from .point import Point, State


def do_set(attacking_team_obj: Team, previous_quality: str, previous_action: str, rng: random.Random) -> str:
    """
    Execute a set action based on previous action quality.
    
    Args:
        attacking_team_obj: Team doing the setting
        previous_quality: Quality of previous action (reception/dig)
        previous_action: Previous action type ("reception" or "dig")
        rng: Random number generator
        
    Returns:
        Set quality outcome
    """
    # Use same probabilities for dig-based sets as reception-based sets
    condition = previous_quality + "_reception"  # treat dig same as reception
    set_probs = attacking_team_obj.set_probabilities.get(condition, {})
    if not set_probs:
        # Fallback if specific condition not found
        set_probs = {"excellent": 0.28, "good": 0.48, "poor": 0.22, "error": 0.02}
    
    return choose_outcome(set_probs, rng)


def do_attack(attacking_team_obj: Team, set_quality: str, rng: random.Random) -> str:
    """
    Execute an attack action based on set quality.
    
    Args:
        attacking_team_obj: Team doing the attacking
        set_quality: Quality of the set
        rng: Random number generator
        
    Returns:
        Attack quality outcome
    """
    attack_condition = set_quality + "_set"
    attack_probs = attacking_team_obj.attack_probabilities.get(attack_condition, {})
    if not attack_probs:
        # Fallback for missing conditions
        attack_probs = {"kill": 0.5, "error": 0.2, "defended": 0.3}
    
    return choose_outcome(attack_probs, rng)


def do_defense(defending_team_obj: Team, attack_quality: str, rng: random.Random) -> tuple[str, str]:
    """
    Execute defense (block + potential dig) based on attack quality.
    
    Args:
        defending_team_obj: Team doing the defending
        attack_quality: Quality of the attack
        rng: Random number generator
        
    Returns:
        Tuple of (block_outcome, dig_outcome_or_none)
        dig_outcome_or_none is None if no dig attempted
    """
    if attack_quality != "defended":
        # Only defended attacks can be blocked
        return ("no_block", None)
    
    # Block attempt
    block_probs = defending_team_obj.block_probabilities.get("power_attack", {})
    if not block_probs:
        # Updated fallback with new deflection types
        block_probs = {"stuff": 0.2, "deflection_to_attack": 0.15, "deflection_to_defense": 0.15, "no_touch": 0.5}
    
    block_outcome = choose_outcome(block_probs, rng)
    
    if block_outcome == "stuff":
        return (block_outcome, None)  # Point ends
    elif block_outcome == "deflection_to_attack":
        # Ball deflects to attacking team's side - attacking team must dig
        dig_probs = defending_team_obj.dig_probabilities.get("deflected_attack", {})
        if not dig_probs:
            dig_probs = {"excellent": 0.3, "good": 0.4, "poor": 0.25, "error": 0.05}
        
        dig_outcome = choose_outcome(dig_probs, rng)
        return (block_outcome, dig_outcome)
    elif block_outcome == "deflection_to_defense":
        # Ball deflects to defending team's side - defending team has only 2 touches
        # No dig phase - goes directly to set
        return (block_outcome, None)
    else:  # no_touch
        # 80% chance of dig attempt after no_touch block
        if rng.random() < 0.80:
            dig_probs = defending_team_obj.dig_probabilities.get("deflected_attack", {})
            if not dig_probs:
                dig_probs = {"excellent": 0.25, "good": 0.35, "poor": 0.30, "error": 0.10}
            
            dig_outcome = choose_outcome(dig_probs, rng)
            return (block_outcome, dig_outcome)
        else:
            return (block_outcome, None)  # Attack lands untouched


def continue_rally(states: list, attacking_team: str, defending_team: str, 
                  teams: dict, serving_team: str, dig_quality: str, rng: random.Random, 
                  max_actions: int = 100) -> Point:
    """
    Continue rally after successful dig until definitive outcome.
    
    Args:
        states: Current point states
        attacking_team: Team that successfully dug (now attacking)
        defending_team: Team that was attacking (now defending)  
        teams: Dict mapping team names to Team objects
        serving_team: Original serving team
        dig_quality: Quality of the dig that continues the rally
        rng: Random number generator
        max_actions: Maximum actions to prevent infinite rallies
        
    Returns:
        Complete Point object
    """
    action_count = len(states)
    
    while action_count < max_actions:
        # 1. Set (attacking team sets based on dig quality)
        attacking_team_obj = teams[attacking_team]
        set_quality = do_set(attacking_team_obj, dig_quality, "dig", rng)
        states.append(State(team=attacking_team, action="set", quality=set_quality))
        action_count += 1
        
        # Check for set error
        if set_quality == "error":
            return Point(
                serving_team=serving_team,
                winner=defending_team,  # Defending team wins when attacking team makes set error
                point_type="set_error",
                states=states
            )
        
        if action_count >= max_actions:
            break
            
        # 2. Attack (attacking team attacks based on set quality)
        attack_quality = do_attack(attacking_team_obj, set_quality, rng)
        states.append(State(team=attacking_team, action="attack", quality=attack_quality))
        action_count += 1
        
        # Check for definitive attack outcomes
        if attack_quality == "kill":
            return Point(
                serving_team=serving_team,
                winner=attacking_team,
                point_type="kill",
                states=states
            )
        elif attack_quality == "error":
            return Point(
                serving_team=serving_team,
                winner=defending_team,
                point_type="attack_error",
                states=states
            )
        elif attack_quality == "defended":
            if action_count >= max_actions:
                break
                
            # 3. Defense (defending team attempts block + dig)
            defending_team_obj = teams[defending_team]
            block_outcome, dig_outcome = do_defense(defending_team_obj, attack_quality, rng)
            
            if block_outcome != "no_block":
                states.append(State(team=defending_team, action="block", quality=block_outcome))
                action_count += 1
                
                if block_outcome == "stuff":
                    return Point(
                        serving_team=serving_team,
                        winner=defending_team,
                        point_type="stuff",
                        states=states
                    )
                elif block_outcome == "deflection_to_attack":
                    # Ball deflected to attacking team - they must dig
                    if dig_outcome is not None:
                        if action_count >= max_actions:
                            break
                            
                        states.append(State(team=attacking_team, action="dig", quality=dig_outcome))
                        action_count += 1
                        
                        if dig_outcome == "error":
                            return Point(
                                serving_team=serving_team,
                                winner=defending_team,
                                point_type="dig_error",
                                states=states
                            )
                        else:
                            # Rally continues - attacking team keeps attacking after dig
                            dig_quality = dig_outcome
                            continue
                elif block_outcome == "deflection_to_defense":
                    # Ball deflected to defending team - only 2 touches, skip dig, go to set
                    if action_count >= max_actions:
                        break
                        
                    defending_team_obj = teams[defending_team]
                    set_quality = do_set(defending_team_obj, "excellent", "block_deflection", rng)
                    states.append(State(team=defending_team, action="set", quality=set_quality))
                    action_count += 1
                    
                    # Check for set error
                    if set_quality == "error":
                        return Point(
                            serving_team=serving_team,
                            winner=attacking_team,  # Attacking team wins when defending team makes set error
                            point_type="set_error",
                            states=states
                        )
                    
                    if action_count >= max_actions:
                        break
                        
                    # Immediate attack (final touch)
                    attack_quality = do_attack(defending_team_obj, set_quality, rng)
                    states.append(State(team=defending_team, action="attack", quality=attack_quality))
                    action_count += 1
                    
                    # Check attack outcomes
                    if attack_quality == "kill":
                        return Point(
                            serving_team=serving_team,
                            winner=defending_team,
                            point_type="kill",
                            states=states
                        )
                    elif attack_quality == "error":
                        return Point(
                            serving_team=serving_team,
                            winner=attacking_team,
                            point_type="attack_error",
                            states=states
                        )
                    elif attack_quality == "defended":
                        # Rally continues - teams switch roles
                        attacking_team, defending_team = defending_team, attacking_team
                        dig_quality = "excellent"  # New rally cycle
                        continue
                else:
                    # Handle other block outcomes (no_touch, etc.)
                    if dig_outcome is not None:
                        if action_count >= max_actions:
                            break
                            
                        states.append(State(team=defending_team, action="dig", quality=dig_outcome))
                        action_count += 1
                        
                        if dig_outcome == "error":
                            return Point(
                                serving_team=serving_team,
                                winner=attacking_team,
                                point_type="dig_error",
                                states=states
                            )
                        else:
                            # Rally continues - switch team roles
                            attacking_team, defending_team = defending_team, attacking_team
                            dig_quality = dig_outcome
                            continue
                    else:
                        # No dig - attack landed
                        return Point(
                            serving_team=serving_team,
                            winner=attacking_team,
                            point_type="kill",
                            states=states
                        )
        else:
            # Undefended attack - should be kill but being safe
            return Point(
                serving_team=serving_team,
                winner=attacking_team,
                point_type="kill",
                states=states
            )
    
    # Rally hit max actions - end with rally type
    winner = rng.choice([attacking_team, defending_team])
    return Point(
        serving_team=serving_team,
        winner=winner,
        point_type="rally",
        states=states
    )


def choose_outcome(probabilities: dict, rng: random.Random) -> str:
    """
    Choose an outcome based on probability distribution.
    
    Args:
        probabilities: Dictionary of outcome -> probability
        rng: Random number generator
        
    Returns:
        Selected outcome
    """
    if not probabilities:
        raise ValueError("Empty probability distribution")
    
    r = rng.random()
    cumulative = 0.0
    
    for outcome, prob in probabilities.items():
        cumulative += prob
        if r <= cumulative:
            return outcome
    
    # Fallback to last outcome if rounding errors
    return list(probabilities.keys())[-1]


def simulate_point(team_a: Team, team_b: Team, serving_team: str = "A", seed: Optional[int] = None) -> Point:
    """
    Simulate a complete volleyball point between two teams.
    
    Args:
        team_a: Team A configuration
        team_b: Team B configuration  
        serving_team: Which team serves ("A" or "B")
        seed: Random seed for reproducible results
        
    Returns:
        Point object with complete state progression
    """
    if serving_team not in ["A", "B"]:
        raise ValueError(f"Invalid serving_team: {serving_team}")
    
    rng = random.Random(seed)
    states = []
    current_team = serving_team
    receiving_team = "B" if serving_team == "A" else "A"
    
    # Get team objects
    teams = {"A": team_a, "B": team_b}
    current_team_obj = teams[current_team]
    receiving_team_obj = teams[receiving_team]
    
    # 1. Serve
    serve_outcome = choose_outcome(current_team_obj.serve_probabilities, rng)
    states.append(State(team=current_team, action="serve", quality=serve_outcome))
    
    # Check for immediate point endings
    if serve_outcome == "ace":
        return Point(
            serving_team=serving_team,
            winner=current_team,
            point_type="ace",
            states=states
        )
    elif serve_outcome == "error":
        return Point(
            serving_team=serving_team, 
            winner=receiving_team,
            point_type="serve_error",
            states=states
        )
    
    # 2. Receive (if serve was in play)
    if serve_outcome == "in_play":
        # Use in_play_serve condition for receive
        receive_probs = receiving_team_obj.receive_probabilities.get("in_play_serve", {})
        if not receive_probs:
            # Fallback if condition not found
            receive_probs = {"excellent": 0.4, "good": 0.4, "poor": 0.15, "error": 0.05}
        
        receive_outcome = choose_outcome(receive_probs, rng)
        states.append(State(team=receiving_team, action="receive", quality=receive_outcome))
        
        # Check for receive error
        if receive_outcome == "error":
            return Point(
                serving_team=serving_team,
                winner=current_team,
                point_type="receive_error", 
                states=states
            )
        
        # 3. Set (conditional on reception quality)
        set_probs = receiving_team_obj.set_probabilities.get(receive_outcome + "_reception", {})
        if not set_probs:
            # Fallback if specific reception condition not found
            set_probs = {"excellent": 0.28, "good": 0.48, "poor": 0.22, "error": 0.02}
        
        set_outcome = choose_outcome(set_probs, rng)
        states.append(State(team=receiving_team, action="set", quality=set_outcome))
        
        # Check for set error
        if set_outcome == "error":
            return Point(
                serving_team=serving_team,
                winner=current_team,  # Serving team wins when receiving team makes set error
                point_type="set_error",
                states=states
            )
        
        # Determine attack probabilities based on actual set quality
        set_quality = set_outcome + "_set"  # e.g., "excellent_set"
        
        # 4. Attack
        attack_probs = receiving_team_obj.attack_probabilities.get(set_quality, {})
        if not attack_probs:
            # Fallback for missing conditions
            attack_probs = {"kill": 0.5, "error": 0.2, "defended": 0.3}
        
        attack_outcome = choose_outcome(attack_probs, rng)
        states.append(State(team=receiving_team, action="attack", quality=attack_outcome))
        
        # Check attack outcomes
        if attack_outcome == "kill":
            return Point(
                serving_team=serving_team,
                winner=receiving_team,
                point_type="kill",
                states=states
            )
        elif attack_outcome == "error":
            return Point(
                serving_team=serving_team,
                winner=current_team,
                point_type="attack_error",
                states=states
            )
        elif attack_outcome == "defended":
            # 5. Block attempt
            block_probs = current_team_obj.block_probabilities.get("power_attack", {})
            if not block_probs:
                block_probs = {"stuff": 0.2, "deflection_to_attack": 0.15, "deflection_to_defense": 0.15, "no_touch": 0.5}
            
            block_outcome = choose_outcome(block_probs, rng)
            states.append(State(team=current_team, action="block", quality=block_outcome))
            
            if block_outcome == "stuff":
                return Point(
                    serving_team=serving_team,
                    winner=current_team,
                    point_type="stuff",
                    states=states
                )
            elif block_outcome == "deflection_to_attack":
                # Ball deflects to attacking team's side - attacking team must dig
                dig_probs = receiving_team_obj.dig_probabilities.get("deflected_attack", {})
                if not dig_probs:
                    dig_probs = {"excellent": 0.3, "good": 0.4, "poor": 0.25, "error": 0.05}
                
                dig_outcome = choose_outcome(dig_probs, rng)
                states.append(State(team=receiving_team, action="dig", quality=dig_outcome))
                
                if dig_outcome == "error":
                    return Point(
                        serving_team=serving_team,
                        winner=current_team,
                        point_type="dig_error",
                        states=states
                    )
                else:
                    # Rally continues after successful dig - switch team roles
                    return continue_rally(
                        states=states,
                        attacking_team=receiving_team,  # receiving team dug, now attacks
                        defending_team=current_team,    # current team was defending, still defends
                        teams=teams,
                        serving_team=serving_team,
                        dig_quality=dig_outcome,
                        rng=rng
                    )
            elif block_outcome == "deflection_to_defense":
                # Ball deflects to defending team's side - defending team has only 2 touches
                # Skip dig phase, go directly to set
                set_quality = do_set(current_team_obj, "excellent", "block_deflection", rng)
                states.append(State(team=current_team, action="set", quality=set_quality))
                
                # Then attack (their final touch)
                attack_quality = do_attack(current_team_obj, set_quality, rng)
                states.append(State(team=current_team, action="attack", quality=attack_quality))
                
                # Check attack outcomes
                if attack_quality == "kill":
                    return Point(
                        serving_team=serving_team,
                        winner=current_team,
                        point_type="kill",
                        states=states
                    )
                elif attack_quality == "error":
                    return Point(
                        serving_team=serving_team,
                        winner=receiving_team,
                        point_type="attack_error", 
                        states=states
                    )
                elif attack_quality == "defended":
                    # Rally continues - now receiving team defends the counter-attack
                    return continue_rally(
                        states=states,
                        attacking_team=receiving_team,  # receiving team now attacks
                        defending_team=current_team,    # current team now defends
                        teams=teams,
                        serving_team=serving_team,
                        dig_quality="excellent",  # Start new rally cycle
                        rng=rng
                    )
            else:  # no_touch
                # Block didn't touch ball - attack continues to floor defense
                # Since attack was "defended" (slow/high), it should be diggable
                # 80% chance of dig attempt, 20% lands untouched
                if rng.random() < 0.80:
                    # Defending team attempts dig
                    dig_probs = current_team_obj.dig_probabilities.get("deflected_attack", {})
                    if not dig_probs:
                        dig_probs = {"excellent": 0.25, "good": 0.35, "poor": 0.30, "error": 0.10}
                    
                    dig_outcome = choose_outcome(dig_probs, rng)
                    states.append(State(team=current_team, action="dig", quality=dig_outcome))
                    
                    if dig_outcome == "error":
                        return Point(
                            serving_team=serving_team,
                            winner=receiving_team,
                            point_type="dig_error",
                            states=states
                        )
                    else:
                        # Rally continues after successful dig - switch team roles
                        return continue_rally(
                            states=states,
                            attacking_team=current_team,    # current team dug, now attacks
                            defending_team=receiving_team,  # receiving team was attacking, now defends
                            teams=teams,
                            serving_team=serving_team,
                            dig_quality=dig_outcome,
                            rng=rng
                        )
                else:
                    # Attack lands untouched (defending team was out of position)
                    return Point(
                        serving_team=serving_team,
                        winner=receiving_team,
                        point_type="kill",
                        states=states
                    )
    
    # Fallback - should not reach here with proper implementation
    winner = rng.choice([current_team, receiving_team])
    return Point(
        serving_team=serving_team,
        winner=winner,
        point_type="rally",
        states=states
    )