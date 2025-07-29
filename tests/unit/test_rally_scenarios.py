#!/usr/bin/env python3
"""
Tests for complex rally scenarios including blocks, digs, and extended rallies.
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point


class TestRallyScenarios(unittest.TestCase):
    """Test complex rally scenarios"""
    
    def setUp(self):
        """Set up teams for rally testing"""
        
        # Standard set_probabilities for all teams
        standard_set_probs = {
            'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0},
            'good_reception': {'excellent': 0.0, 'good': 1.0, 'poor': 0.0},
            'poor_reception': {'excellent': 0.0, 'good': 0.0, 'poor': 1.0}
        }
        
        # Standard attack probabilities for all set qualities
        standard_attack_probs = {
            'excellent_set': {'kill': 0.0, 'error': 0.0, 'defended': 1.0},
            'good_set': {'kill': 0.0, 'error': 0.0, 'defended': 1.0},
            'poor_set': {'kill': 0.0, 'error': 0.0, 'defended': 1.0}
        }
        
        # Team that always gets defended attacks (leads to blocks)
        self.defended_team_data = {
            'name': 'Defended Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': standard_set_probs,
            'attack_probabilities': standard_attack_probs,
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection_to_attack': 0.0, 'deflection_to_defense': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        # Team that always stuffs blocks
        self.stuff_team_data = {
            'name': 'Stuff Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': standard_set_probs,
            'attack_probabilities': standard_attack_probs,
            'block_probabilities': {
                'power_attack': {'stuff': 1.0, 'deflection_to_attack': 0.0, 'deflection_to_defense': 0.0, 'no_touch': 0.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        # Team that always deflects blocks
        self.deflect_team_data = {
            'name': 'Deflect Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': standard_set_probs,
            'attack_probabilities': standard_attack_probs,
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection_to_attack': 1.0, 'deflection_to_defense': 0.0, 'no_touch': 0.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 0.0, 'good': 0.0, 'poor': 0.0, 'error': 1.0}
            }
        }
        
        # Team that successfully digs deflections
        self.dig_team_data = {
            'name': 'Dig Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': standard_set_probs,
            'attack_probabilities': standard_attack_probs,
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection_to_attack': 1.0, 'deflection_to_defense': 0.0, 'no_touch': 0.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        self.defended_team = Team.from_dict(self.defended_team_data)
        self.stuff_team = Team.from_dict(self.stuff_team_data)
        self.deflect_team = Team.from_dict(self.deflect_team_data)
        self.dig_team = Team.from_dict(self.dig_team_data)
    
    def test_stuff_block_scenario(self):
        """Test serve -> receive -> set -> attack -> stuff block sequence"""
        point = simulate_point(self.stuff_team, self.defended_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives, B sets, B attacks, A stuffs
        expected_sequence = [
            ("A", "serve", "in_play"),
            ("B", "receive", "excellent"),
            ("B", "set", "excellent"),
            ("B", "attack", "defended"),
            ("A", "block", "stuff")
        ]
        
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "A")  # Blocking team wins on stuff
        self.assertEqual(point.point_type, "stuff")
        self.assertEqual(len(point.states), 5)
        
        for i, (expected_team, expected_action, expected_quality) in enumerate(expected_sequence):
            self.assertEqual(point.states[i].team, expected_team, f"State {i}: expected {expected_team}, got {point.states[i].team}")
            self.assertEqual(point.states[i].action, expected_action, f"State {i}: expected {expected_action}, got {point.states[i].action}")
            self.assertEqual(point.states[i].quality, expected_quality, f"State {i}: expected {expected_quality}, got {point.states[i].quality}")
    
    def test_deflection_dig_error_scenario(self):
        """Test serve -> receive -> set -> attack -> deflection -> dig error sequence"""
        point = simulate_point(self.deflect_team, self.deflect_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives, B sets, B attacks, A deflects, B digs error
        expected_sequence = [
            ("A", "serve", "in_play"),
            ("B", "receive", "excellent"),
            ("B", "set", "excellent"),
            ("B", "attack", "defended"),
            ("A", "block", "deflection_to_attack"),
            ("B", "dig", "error")
        ]
        
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "A")  # Serving team wins on opponent's dig error
        self.assertEqual(point.point_type, "dig_error")
        self.assertEqual(len(point.states), 6)
        
        for i, (expected_team, expected_action, expected_quality) in enumerate(expected_sequence):
            self.assertEqual(point.states[i].team, expected_team, f"State {i}: expected {expected_team}, got {point.states[i].team}")
            self.assertEqual(point.states[i].action, expected_action, f"State {i}: expected {expected_action}, got {point.states[i].action}")
            self.assertEqual(point.states[i].quality, expected_quality, f"State {i}: expected {expected_quality}, got {point.states[i].quality}")
    
    def test_deflection_successful_dig_rally(self):
        """Test serve -> receive -> set -> attack -> deflection -> dig -> extended rally"""
        point = simulate_point(self.dig_team, self.dig_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives, B sets, B attacks, A deflects, B digs, then rally continues
        self.assertEqual(point.serving_team, "A")
        self.assertIn(point.winner, ["A", "B"])  # Either team can win the rally
        # Point type could be "rally" or specific outcome like "kill" depending on rally continuation
        self.assertGreaterEqual(len(point.states), 6)  # At least up to the dig
        
        # Check the sequence up to the dig
        expected_sequence = [
            ("A", "serve", "in_play"),
            ("B", "receive", "excellent"),
            ("B", "set", "excellent"),
            ("B", "attack", "defended"),
            ("A", "block", "deflection_to_attack"),
            ("B", "dig", "excellent")
        ]
        
        for i, (expected_team, expected_action, expected_quality) in enumerate(expected_sequence):
            self.assertEqual(point.states[i].team, expected_team, f"State {i}: expected {expected_team}, got {point.states[i].team}")
            self.assertEqual(point.states[i].action, expected_action, f"State {i}: expected {expected_action}, got {point.states[i].action}")
            self.assertEqual(point.states[i].quality, expected_quality, f"State {i}: expected {expected_quality}, got {point.states[i].quality}")
    
    def test_no_touch_block_rally(self):
        """Test serve -> receive -> set -> attack -> no touch block leads to rally"""
        point = simulate_point(self.defended_team, self.defended_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives, B sets, B attacks, A no-touch block, then rally
        self.assertEqual(point.serving_team, "A")
        self.assertIn(point.winner, ["A", "B"])  # Either team can win
        # Point type could be "rally" or specific outcome depending on what happens after no-touch
        self.assertGreaterEqual(len(point.states), 5)  # At least up to the block
        
        # Check sequence up to block
        expected_sequence = [
            ("A", "serve", "in_play"),
            ("B", "receive", "excellent"),
            ("B", "set", "excellent"),
            ("B", "attack", "defended"),
            ("A", "block", "no_touch")
        ]
        
        for i, (expected_team, expected_action, expected_quality) in enumerate(expected_sequence):
            self.assertEqual(point.states[i].team, expected_team, f"State {i}: expected {expected_team}, got {point.states[i].team}")
            self.assertEqual(point.states[i].action, expected_action, f"State {i}: expected {expected_action}, got {point.states[i].action}")
            self.assertEqual(point.states[i].quality, expected_quality, f"State {i}: expected {expected_quality}, got {point.states[i].quality}")
    
    def test_receive_error_ends_early(self):
        """Test that receive error ends point before attack"""
        receive_error_team_data = {
            'name': 'Receive Error Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 0.0, 'good': 0.0, 'poor': 0.0, 'error': 1.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0},
                'good_reception': {'excellent': 0.0, 'good': 1.0, 'poor': 0.0},
                'poor_reception': {'excellent': 0.0, 'good': 0.0, 'poor': 1.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0},
                'good_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0},
                'poor_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection_to_attack': 0.0, 'deflection_to_defense': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        receive_error_team = Team.from_dict(receive_error_team_data)
        point = simulate_point(self.defended_team, receive_error_team, serving_team="A", seed=12345)
        
        # Should end after receive error
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "A")  # Serving team wins
        self.assertEqual(point.point_type, "receive_error")
        self.assertEqual(len(point.states), 2)  # Only serve and receive
        
        self.assertEqual(point.states[1].action, "receive")
        self.assertEqual(point.states[1].quality, "error")
    
    def test_multiple_rally_outcomes_with_different_seeds(self):
        """Test that rally scenarios can have different outcomes"""
        # Use teams that create rallies with the dig team setup
        rally_outcomes = []
        
        for seed in range(100):
            point = simulate_point(self.defended_team, self.dig_team, serving_team="A", seed=seed)
            rally_outcomes.append((point.winner, point.point_type))
        
        # Should see variety in outcomes
        winners = set(outcome[0] for outcome in rally_outcomes)
        
        # Both teams should be able to win rallies
        self.assertEqual(len(winners), 2, "Both teams should win some rallies")
    
    def test_state_sequence_always_valid(self):
        """Test that state sequences always follow volleyball rules"""
        # Test many scenarios to ensure state machine doesn't break rules
        for seed in range(50):
            point = simulate_point(self.defended_team, self.dig_team, serving_team="A", seed=seed)
            
            # First state must always be a serve
            self.assertEqual(point.states[0].action, "serve")
            self.assertEqual(point.states[0].team, point.serving_team)
            
            # If point reaches second state, it should be receive by other team
            if len(point.states) >= 2:
                self.assertEqual(point.states[1].action, "receive")
                receiving_team = "B" if point.serving_team == "A" else "A"
                serving_team = point.serving_team
                self.assertEqual(point.states[1].team, receiving_team)
            
            # If point reaches third state, it should be set by receiving team
            if len(point.states) >= 3:
                self.assertEqual(point.states[2].action, "set")
                self.assertEqual(point.states[2].team, receiving_team)
                
            # If point reaches fourth state, it should be attack by receiving team
            if len(point.states) >= 4:
                self.assertEqual(point.states[3].action, "attack")
                self.assertEqual(point.states[3].team, receiving_team)
            
            # If point reaches fifth state, it should be block by serving team
            if len(point.states) >= 5:
                self.assertEqual(point.states[4].action, "block")
                self.assertEqual(point.states[4].team, serving_team)
            
            # If point reaches sixth state, it should be dig
            # The digging team depends on the block deflection direction
            if len(point.states) >= 6:
                self.assertEqual(point.states[5].action, "dig")
                
                # Check block quality to determine who should dig
                block_quality = point.states[4].quality
                if block_quality == "deflection_to_attack":
                    # Ball deflects to attacking team's side -> attacking team digs
                    expected_dig_team = receiving_team
                elif block_quality == "deflection_to_defense":
                    # Ball deflects to defending team's side -> defending team digs
                    expected_dig_team = serving_team
                elif block_quality == "no_touch":
                    # Block misses, ball continues to defending team's side -> defending team digs
                    expected_dig_team = serving_team
                else:
                    # For other block types (stuff shouldn't reach dig), assume attacking team
                    expected_dig_team = receiving_team
                
                self.assertEqual(point.states[5].team, expected_dig_team, 
                    f"Seed {seed}: Block quality '{block_quality}' should result in team {expected_dig_team} digging, but team {point.states[5].team} dug")


if __name__ == '__main__':
    unittest.main()
