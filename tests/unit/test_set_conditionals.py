#!/usr/bin/env python3
"""
Unit tests for set probabilities conditional on reception quality.
"""

import unittest
import sys
import os
from collections import Counter

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point


class TestSetConditionals(unittest.TestCase):
    """Test that set quality depends on reception quality"""
    
    def setUp(self):
        """Set up test team with known set probabilities"""
        self.team_data = {
            'name': 'Set Test Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 0.33, 'good': 0.33, 'poor': 0.34, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0},
                'good_reception': {'excellent': 0.0, 'good': 1.0, 'poor': 0.0},
                'poor_reception': {'excellent': 0.0, 'good': 0.0, 'poor': 1.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0},
                'good_set': {'kill': 0.5, 'error': 0.5, 'defended': 0.0},
                'poor_set': {'kill': 0.0, 'error': 1.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        self.team = Team.from_dict(self.team_data)
    
    def test_set_action_included_in_states(self):
        """Test that set action is explicitly included in point states"""
        point = simulate_point(self.team, self.team, serving_team="A", seed=12345)
        
        # Should have at least 3 states: serve, receive, set
        self.assertGreaterEqual(len(point.states), 3)
        
        # Check the state sequence
        self.assertEqual(point.states[0].action, "serve")
        self.assertEqual(point.states[1].action, "receive")
        
        # Third state should be set (if reception wasn't an error)
        if point.states[1].quality != "error":
            self.assertEqual(point.states[2].action, "set")
    
    def test_excellent_reception_produces_excellent_set(self):
        """Test that excellent reception always produces excellent set"""
        # Test many points to catch any that have excellent reception
        excellent_set_found = False
        
        for seed in range(100):
            point = simulate_point(self.team, self.team, serving_team="A", seed=seed)
            
            if (len(point.states) >= 3 and 
                point.states[1].quality == "excellent" and
                point.states[2].action == "set"):
                
                # With our test team, excellent reception should ALWAYS produce excellent set
                self.assertEqual(point.states[2].quality, "excellent",
                               f"Excellent reception produced {point.states[2].quality} set")
                excellent_set_found = True
        
        self.assertTrue(excellent_set_found, "No excellent receptions found in 100 samples")
    
    def test_poor_reception_produces_poor_set(self):
        """Test that poor reception always produces poor set"""
        poor_set_found = False
        
        for seed in range(100):
            point = simulate_point(self.team, self.team, serving_team="A", seed=seed)
            
            if (len(point.states) >= 3 and 
                point.states[1].quality == "poor" and
                point.states[2].action == "set"):
                
                # With our test team, poor reception should ALWAYS produce poor set
                self.assertEqual(point.states[2].quality, "poor",
                               f"Poor reception produced {point.states[2].quality} set")
                poor_set_found = True
        
        self.assertTrue(poor_set_found, "No poor receptions found in 100 samples")
    
    def test_set_quality_affects_attack_outcome(self):
        """Test that attack success varies based on actual set quality"""
        attack_outcomes = {'excellent_set': [], 'good_set': [], 'poor_set': []}
        
        for seed in range(200):
            point = simulate_point(self.team, self.team, serving_team="A", seed=seed)
            
            # Find points that reach attack
            if (len(point.states) >= 4 and 
                point.states[2].action == "set" and
                point.states[3].action == "attack"):
                
                set_quality = point.states[2].quality
                attack_outcome = point.states[3].quality
                
                if set_quality + "_set" in attack_outcomes:
                    attack_outcomes[set_quality + "_set"].append(attack_outcome)
        
        # Verify our deterministic attack probabilities work
        if attack_outcomes['excellent_set']:
            # All excellent sets should produce kills (100% in our test team)
            self.assertTrue(all(outcome == "kill" for outcome in attack_outcomes['excellent_set']),
                           "Not all excellent sets produced kills")
        
        if attack_outcomes['poor_set']:
            # All poor sets should produce errors (100% in our test team)
            self.assertTrue(all(outcome == "error" for outcome in attack_outcomes['poor_set']),
                           "Not all poor sets produced errors")
    
    def test_realistic_conditional_probabilities(self):
        """Test with realistic (non-deterministic) probabilities"""
        realistic_team_data = {
            'name': 'Realistic Test Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 0.4, 'good': 0.4, 'poor': 0.2, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 0.7, 'good': 0.25, 'poor': 0.05},
                'good_reception': {'excellent': 0.3, 'good': 0.6, 'poor': 0.1},
                'poor_reception': {'excellent': 0.05, 'good': 0.25, 'poor': 0.7}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 0.8, 'error': 0.1, 'defended': 0.1},
                'good_set': {'kill': 0.6, 'error': 0.2, 'defended': 0.2},
                'poor_set': {'kill': 0.3, 'error': 0.4, 'defended': 0.3}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        realistic_team = Team.from_dict(realistic_team_data)
        
        # Collect statistics
        patterns = []
        for seed in range(300):
            point = simulate_point(realistic_team, realistic_team, serving_team="A", seed=seed)
            
            if len(point.states) >= 3:
                receive_quality = point.states[1].quality
                set_quality = point.states[2].quality
                patterns.append((receive_quality, set_quality))
        
        # Analyze that excellent receptions lead to better sets than poor receptions
        excellent_sets_from_excellent = sum(1 for r, s in patterns 
                                          if r == "excellent" and s == "excellent")
        poor_sets_from_poor = sum(1 for r, s in patterns 
                                if r == "poor" and s == "poor")
        
        excellent_receptions = sum(1 for r, s in patterns if r == "excellent")
        poor_receptions = sum(1 for r, s in patterns if r == "poor")
        
        if excellent_receptions > 0 and poor_receptions > 0:
            excellent_to_excellent_rate = excellent_sets_from_excellent / excellent_receptions
            poor_to_poor_rate = poor_sets_from_poor / poor_receptions
            
            # Excellent receptions should produce excellent sets more often than 
            # poor receptions produce poor sets (given our probabilities)
            self.assertGreater(excellent_to_excellent_rate, 0.5,
                             "Excellent receptions should often produce excellent sets")
            self.assertGreater(poor_to_poor_rate, 0.5,
                             "Poor receptions should often produce poor sets")
    
    def test_team_validation_includes_set_probabilities(self):
        """Test that team validation checks set probabilities"""
        from bvsim_core.validation import validate_team_configuration
        
        # Valid team should pass
        errors = validate_team_configuration(self.team)
        self.assertEqual(len(errors), 0, "Valid team should have no errors")
        
        # Team with invalid set probabilities should fail
        invalid_team_data = self.team_data.copy()
        invalid_team_data['set_probabilities'] = {
            'excellent_reception': {'excellent': 0.5, 'good': 0.6, 'poor': 0.0}  # Sum = 1.1
        }
        
        invalid_team = Team.from_dict(invalid_team_data)
        errors = validate_team_configuration(invalid_team)
        
        self.assertGreater(len(errors), 0, "Invalid team should have errors")
        self.assertTrue(any("set_probabilities" in error for error in errors),
                       "Should have set_probabilities error")


if __name__ == '__main__':
    unittest.main()