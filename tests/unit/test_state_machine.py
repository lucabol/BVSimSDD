#!/usr/bin/env python3
"""
Unit tests for state machine logic.
Tests that volleyball simulation follows correct rules and probabilities.
"""

import unittest
from collections import Counter
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point, choose_outcome
from bvsim_core.point import Point, State


class TestStateMachine(unittest.TestCase):
    """Test state machine volleyball simulation logic"""
    
    def setUp(self):
        """Set up test teams with known probabilities"""
        # Team with deterministic serve ace
        self.ace_team_data = {
            'name': 'Ace Team',
            'serve_probabilities': {'ace': 1.0, 'in_play': 0.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        # Team with deterministic serve error
        self.error_team_data = {
            'name': 'Error Team', 
            'serve_probabilities': {'ace': 0.0, 'in_play': 0.0, 'error': 1.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        # Team with in-play serves leading to kills
        self.kill_team_data = {
            'name': 'Kill Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 1.0, 'error': 0.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        # Team with attack errors 
        self.attack_error_team_data = {
            'name': 'Attack Error Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 0.0, 'error': 1.0, 'defended': 0.0}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.0, 'deflection': 0.0, 'no_touch': 1.0}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0, 'error': 0.0}
            }
        }
        
        self.ace_team = Team.from_dict(self.ace_team_data)
        self.error_team = Team.from_dict(self.error_team_data)
        self.kill_team = Team.from_dict(self.kill_team_data)
        self.attack_error_team = Team.from_dict(self.attack_error_team_data)
    
    def test_choose_outcome_probability_distribution(self):
        """Test that choose_outcome respects probability distributions"""
        import random
        
        # Test with known seed for reproducibility
        rng = random.Random(12345)
        
        # Test 1000 outcomes with 50/50 distribution
        probs = {'A': 0.5, 'B': 0.5}
        outcomes = [choose_outcome(probs, rng) for _ in range(1000)]
        counter = Counter(outcomes)
        
        # Should be approximately 500 each (allow 10% variance)
        self.assertGreater(counter['A'], 400)
        self.assertLess(counter['A'], 600)
        self.assertGreater(counter['B'], 400)
        self.assertLess(counter['B'], 600)
    
    def test_serve_ace_ends_point_immediately(self):
        """Test that serve ace ends the point immediately"""
        point = simulate_point(self.ace_team, self.kill_team, serving_team="A", seed=12345)
        
        # Should end immediately with ace
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "A")
        self.assertEqual(point.point_type, "ace")
        self.assertEqual(len(point.states), 1)
        self.assertEqual(point.states[0].team, "A")
        self.assertEqual(point.states[0].action, "serve")
        self.assertEqual(point.states[0].quality, "ace")
    
    def test_serve_error_ends_point_immediately(self):
        """Test that serve error ends the point immediately"""
        point = simulate_point(self.error_team, self.kill_team, serving_team="A", seed=12345)
        
        # Should end immediately with serve error
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "B")  # Receiving team wins
        self.assertEqual(point.point_type, "serve_error")
        self.assertEqual(len(point.states), 1)
        self.assertEqual(point.states[0].team, "A")
        self.assertEqual(point.states[0].action, "serve")
        self.assertEqual(point.states[0].quality, "error")
    
    def test_successful_attack_sequence(self):
        """Test serve -> receive -> set -> attack -> kill sequence"""
        point = simulate_point(self.kill_team, self.kill_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives excellently, B sets excellently, B attacks for kill
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "B")  # Receiving team gets the kill
        self.assertEqual(point.point_type, "kill")
        self.assertEqual(len(point.states), 4)  # serve, receive, set, attack
        
        # Check state sequence
        self.assertEqual(point.states[0].team, "A")
        self.assertEqual(point.states[0].action, "serve")
        self.assertEqual(point.states[0].quality, "in_play")
        
        self.assertEqual(point.states[1].team, "B")
        self.assertEqual(point.states[1].action, "receive")
        self.assertEqual(point.states[1].quality, "excellent")
        
        self.assertEqual(point.states[2].team, "B")
        self.assertEqual(point.states[2].action, "set")
        self.assertEqual(point.states[2].quality, "excellent")
        
        self.assertEqual(point.states[3].team, "B")
        self.assertEqual(point.states[3].action, "attack")
        self.assertEqual(point.states[3].quality, "kill")
    
    def test_attack_error_sequence(self):
        """Test serve -> receive -> set -> attack error sequence"""
        point = simulate_point(self.kill_team, self.attack_error_team, serving_team="A", seed=12345)
        
        # Should be: A serves, B receives excellently, B sets excellently, B attacks into error
        self.assertEqual(point.serving_team, "A")
        self.assertEqual(point.winner, "A")  # Serving team wins on opponent's error
        self.assertEqual(point.point_type, "attack_error")
        self.assertEqual(len(point.states), 4)  # serve, receive, set, attack
        
        # Check attack error
        self.assertEqual(point.states[3].team, "B")
        self.assertEqual(point.states[3].action, "attack")
        self.assertEqual(point.states[3].quality, "error")
    
    def test_serving_team_alternation(self):
        """Test that serving team can be A or B"""
        point_a = simulate_point(self.ace_team, self.kill_team, serving_team="A", seed=12345)
        point_b = simulate_point(self.ace_team, self.kill_team, serving_team="B", seed=12345)
        
        self.assertEqual(point_a.serving_team, "A")
        self.assertEqual(point_a.states[0].team, "A")
        
        self.assertEqual(point_b.serving_team, "B") 
        self.assertEqual(point_b.states[0].team, "B")
    
    def test_reproducible_with_seed(self):
        """Test that same seed produces identical results"""
        point1 = simulate_point(self.kill_team, self.kill_team, serving_team="A", seed=12345)
        point2 = simulate_point(self.kill_team, self.kill_team, serving_team="A", seed=12345)
        
        # Should be identical
        self.assertEqual(point1.serving_team, point2.serving_team)
        self.assertEqual(point1.winner, point2.winner)
        self.assertEqual(point1.point_type, point2.point_type)
        self.assertEqual(len(point1.states), len(point2.states))
        
        for s1, s2 in zip(point1.states, point2.states):
            self.assertEqual(s1.team, s2.team)
            self.assertEqual(s1.action, s2.action)
            self.assertEqual(s1.quality, s2.quality)
    
    def test_different_seeds_produce_different_results(self):
        """Test that different seeds can produce different outcomes"""
        # Use teams with realistic probabilities for variation
        realistic_team_data = {
            'name': 'Realistic Team',
            'serve_probabilities': {'ace': 0.1, 'in_play': 0.8, 'error': 0.1},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 0.3, 'good': 0.4, 'poor': 0.2, 'error': 0.1}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 0.6, 'error': 0.2, 'defended': 0.2},
                'good_set': {'kill': 0.4, 'error': 0.3, 'defended': 0.3},
                'poor_set': {'kill': 0.2, 'error': 0.4, 'defended': 0.4}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.2, 'deflection': 0.3, 'no_touch': 0.5}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 0.3, 'good': 0.4, 'poor': 0.2, 'error': 0.1}
            }
        }
        
        realistic_team = Team.from_dict(realistic_team_data)
        
        # Simulate multiple points with different seeds
        points = []
        for seed in range(100):
            point = simulate_point(realistic_team, realistic_team, serving_team="A", seed=seed)
            points.append(point)
        
        # Should see variety in outcomes
        point_types = set(p.point_type for p in points)
        winners = set(p.winner for p in points)
        
        # Should have multiple point types and both teams winning
        self.assertGreater(len(point_types), 1, "Should see variety in point types")
        self.assertEqual(len(winners), 2, "Both teams should win some points")
    
    def test_conditional_probabilities_respected(self):
        """Test that attack success varies based on set quality"""
        # Team with varying attack success based on set quality
        conditional_team_data = {
            'name': 'Conditional Team',
            'serve_probabilities': {'ace': 0.0, 'in_play': 1.0, 'error': 0.0},
            'receive_probabilities': {
                'in_play_serve': {
                    'excellent': 0.33, 'good': 0.33, 'poor': 0.34, 'error': 0.0
                }
            },
            'set_probabilities': {
                'excellent_reception': {'excellent': 1.0, 'good': 0.0, 'poor': 0.0},
                'good_reception': {'excellent': 0.0, 'good': 1.0, 'poor': 0.0},
                'poor_reception': {'excellent': 0.0, 'good': 0.0, 'poor': 1.0}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 0.9, 'error': 0.05, 'defended': 0.05},
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
        
        conditional_team = Team.from_dict(conditional_team_data)
        
        # Simulate many points to see conditional effects
        excellent_kills = 0
        good_kills = 0
        poor_kills = 0
        
        for seed in range(1000):
            point = simulate_point(conditional_team, conditional_team, serving_team="A", seed=seed)
            
            # Only count points that reach attack phase (4 states: serve, receive, set, attack)
            if len(point.states) >= 4:
                set_quality = point.states[2].quality  # set quality determines attack success
                attack_outcome = point.states[3].quality
                
                if set_quality == "excellent" and attack_outcome == "kill":
                    excellent_kills += 1
                elif set_quality == "good" and attack_outcome == "kill":
                    good_kills += 1
                elif set_quality == "poor" and attack_outcome == "kill":
                    poor_kills += 1
        
        # Excellent sets should produce more kills than poor sets
        # (allowing for statistical variation)
        self.assertGreater(excellent_kills, poor_kills, 
                          "Excellent sets should produce more kills than poor sets")
    
    def test_invalid_serving_team_raises_error(self):
        """Test that invalid serving team raises error"""
        with self.assertRaises(ValueError):
            simulate_point(self.ace_team, self.kill_team, serving_team="C", seed=12345)
    
    def test_point_always_has_winner(self):
        """Test that every simulated point has a winner"""
        for seed in range(50):
            point = simulate_point(self.kill_team, self.kill_team, serving_team="A", seed=seed)
            self.assertIn(point.winner, ["A", "B"])
            self.assertIsNotNone(point.point_type)
            self.assertGreater(len(point.states), 0)


if __name__ == '__main__':
    unittest.main()