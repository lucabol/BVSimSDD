#!/usr/bin/env python3
"""
Tests for extreme statistical behavior in volleyball simulation
These tests verify that the simulation handles edge cases correctly
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_cli.templates import get_basic_template


class TestExtremeStatistics(unittest.TestCase):
    """Test extreme statistical scenarios"""

    def setUp(self):
        """Set up basic teams for testing"""
        self.team_a_template = get_basic_template("Team A")
        self.team_b_template = get_basic_template("Team B") 
        
    def test_100_percent_ace_team_a_serving(self):
        """Test: If Team A has 100% ace rate and starts serving, should win 100% of points"""
        # Create team with 100% ace rate
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 1.0
        team_a_data['serve_probabilities']['in_play'] = 0.0
        team_a_data['serve_probabilities']['error'] = 0.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Simulate multiple points with Team A serving
        wins_a = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            if result.winner == "A":
                wins_a += 1
                
        win_rate = wins_a / total_points
        self.assertGreaterEqual(win_rate, 0.99, f"Expected ~100% win rate for 100% ace, got {win_rate:.2%}")
        
    def test_100_percent_ace_team_b_serving(self):
        """Test: If Team B has 100% ace rate and starts serving, should win 100% of points"""
        # Create team with 100% ace rate
        team_b_data = self.team_b_template.copy()
        team_b_data['serve_probabilities']['ace'] = 1.0
        team_b_data['serve_probabilities']['in_play'] = 0.0
        team_b_data['serve_probabilities']['error'] = 0.0
        
        team_a = Team.from_dict(self.team_a_template)
        team_b = Team.from_dict(team_b_data)
        
        # Simulate multiple points with Team B serving
        wins_b = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=42 + i)
            if result.winner == "B":
                wins_b += 1
                
        win_rate = wins_b / total_points
        self.assertGreaterEqual(win_rate, 0.99, f"Expected ~100% win rate for 100% ace, got {win_rate:.2%}")

    def test_100_percent_serve_error_team_a_serving(self):
        """Test: If Team A has 100% serve error rate, should lose 100% of points when serving"""
        # Create team with 100% serve error rate
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.0
        team_a_data['serve_probabilities']['in_play'] = 0.0
        team_a_data['serve_probabilities']['error'] = 1.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Simulate multiple points with Team A serving
        wins_b = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            if result.winner == "B":
                wins_b += 1
                
        win_rate = wins_b / total_points
        self.assertGreaterEqual(win_rate, 0.99, f"Expected ~100% win rate for opponent when 100% serve error, got {win_rate:.2%}")

    def test_100_percent_reception_error_vs_in_play_serve(self):
        """Test: If Team A serves 100% in play and Team B has 100% reception error, Team A should win 100%"""
        # Team A: 100% in-play serves
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.0
        team_a_data['serve_probabilities']['in_play'] = 1.0
        team_a_data['serve_probabilities']['error'] = 0.0
        
        # Team B: 100% reception errors
        team_b_data = self.team_b_template.copy()
        team_b_data['receive_probabilities']['in_play_serve']['excellent'] = 0.0
        team_b_data['receive_probabilities']['in_play_serve']['good'] = 0.0
        team_b_data['receive_probabilities']['in_play_serve']['poor'] = 0.0
        team_b_data['receive_probabilities']['in_play_serve']['error'] = 1.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(team_b_data)
        
        # Simulate multiple points with Team A serving
        wins_a = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            if result.winner == "A":
                wins_a += 1
                
        win_rate = wins_a / total_points
        self.assertGreaterEqual(win_rate, 0.99, f"Expected ~100% win rate when opponent has 100% reception error, got {win_rate:.2%}")

    def test_100_percent_kill_rate_from_excellent_set(self):
        """Test: If team has 100% kill rate from excellent sets and always gets excellent sets"""
        # Team A: Perfect setting and attacking
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.0
        team_a_data['serve_probabilities']['in_play'] = 1.0
        team_a_data['serve_probabilities']['error'] = 0.0
        
        # Perfect reception
        team_a_data['receive_probabilities']['in_play_serve']['excellent'] = 1.0
        team_a_data['receive_probabilities']['in_play_serve']['good'] = 0.0
        team_a_data['receive_probabilities']['in_play_serve']['poor'] = 0.0
        team_a_data['receive_probabilities']['in_play_serve']['error'] = 0.0
        
        # Perfect setting from excellent reception
        team_a_data['set_probabilities']['excellent_reception']['excellent'] = 1.0
        team_a_data['set_probabilities']['excellent_reception']['good'] = 0.0
        team_a_data['set_probabilities']['excellent_reception']['poor'] = 0.0
        team_a_data['set_probabilities']['excellent_reception']['error'] = 0.0
        
        # Perfect kill from excellent set
        team_a_data['attack_probabilities']['excellent_set']['kill'] = 1.0
        team_a_data['attack_probabilities']['excellent_set']['defended'] = 0.0
        team_a_data['attack_probabilities']['excellent_set']['error'] = 0.0
        
        # Team B: Normal stats
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Simulate multiple points with Team B serving (so Team A receives)
        wins_a = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=42 + i)
            if result.winner == "A":
                wins_a += 1
                
        win_rate = wins_a / total_points
        # Should win most points when receiving due to perfect sideout
        self.assertGreaterEqual(win_rate, 0.85, f"Expected high win rate with perfect sideout chain, got {win_rate:.2%}")

    def test_100_percent_block_stuff(self):
        """Test: If team has 100% block stuff rate against power attacks"""
        # Team A: Normal team (will attack and get blocked)
        team_a_data = self.team_a_template.copy()
        
        # Team B: 100% stuff blocks (Team B will block Team A's attacks)
        team_b_data = self.team_b_template.copy()
        team_b_data['block_probabilities']['power_attack']['stuff'] = 1.0
        team_b_data['block_probabilities']['power_attack']['deflection_to_defense'] = 0.0
        team_b_data['block_probabilities']['power_attack']['deflection_to_attack'] = 0.0
        team_b_data['block_probabilities']['power_attack']['no_touch'] = 0.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(team_b_data)
        
        # Team B serves, so Team A receives and attacks (getting blocked by Team B)
        total_points = 50
        team_b_wins = 0
        stuff_blocks = 0
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=42 + i)
            if result.winner == "B":
                team_b_wins += 1
            if result.point_type == "stuff":
                stuff_blocks += 1
        
        # Team B should win some points due to perfect blocking when Team A attacks
        win_rate = team_b_wins / total_points
        self.assertGreater(win_rate, 0.1, f"Expected some wins from perfect blocking, got {win_rate:.2%}")
        
        # Should see some stuff blocks in the results
        if stuff_blocks == 0:
            print(f"Warning: No stuff blocks recorded in {total_points} points")

    def test_alternating_serve_advantage(self):
        """Test: Verify that serving advantage works correctly"""
        # Team A: 50% ace rate
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.5
        team_a_data['serve_probabilities']['in_play'] = 0.5
        team_a_data['serve_probabilities']['error'] = 0.0
        
        # Team B: 50% ace rate
        team_b_data = self.team_b_template.copy()
        team_b_data['serve_probabilities']['ace'] = 0.5
        team_b_data['serve_probabilities']['in_play'] = 0.5
        team_b_data['serve_probabilities']['error'] = 0.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(team_b_data)
        
        # Test with Team A serving
        wins_a_serving = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            if result.winner == "A":
                wins_a_serving += 1
        
        # Test with Team B serving  
        wins_a_receiving = 0
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=1000 + i)
            if result.winner == "A":
                wins_a_receiving += 1
                
        win_rate_serving = wins_a_serving / total_points
        win_rate_receiving = wins_a_receiving / total_points
        
        # Team A should win more when serving than when receiving
        self.assertGreater(win_rate_serving, win_rate_receiving + 0.05, 
                          f"Serving advantage not evident: serving {win_rate_serving:.2%} vs receiving {win_rate_receiving:.2%}")

    def test_zero_probability_edge_case(self):
        """Test: Ensure zero probabilities are handled correctly"""
        # Team with some zero probabilities
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.0
        team_a_data['serve_probabilities']['in_play'] = 1.0
        team_a_data['serve_probabilities']['error'] = 0.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Should not crash and should produce valid results
        results = []
        for i in range(10):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            results.append(result)
            
        # Verify all results are valid
        for result in results:
            self.assertIn(result.winner, ["A", "B"])
            self.assertGreater(len(result.states), 0)
            self.assertIn(result.point_type, ["ace", "error", "kill", "block", "stuff", "attack_error", "dig_error", "set_error"])

    def test_perfect_dig_chain(self):
        """Test: Perfect dig and counterattack sequence"""
        # Team A: Normal serving
        team_a = Team.from_dict(self.team_a_template)
        
        # Team B: Perfect digging and counterattack
        team_b_data = self.team_b_template.copy()
        team_b_data['dig_probabilities']['deflected_attack']['excellent'] = 1.0
        team_b_data['dig_probabilities']['deflected_attack']['good'] = 0.0
        team_b_data['dig_probabilities']['deflected_attack']['poor'] = 0.0
        team_b_data['dig_probabilities']['deflected_attack']['error'] = 0.0
        
        # Perfect transition setting and attacking
        team_b_data['set_probabilities']['excellent_reception']['excellent'] = 1.0
        team_b_data['set_probabilities']['excellent_reception']['good'] = 0.0
        team_b_data['set_probabilities']['excellent_reception']['poor'] = 0.0
        team_b_data['set_probabilities']['excellent_reception']['error'] = 0.0
        
        team_b = Team.from_dict(team_b_data)
        
        # This test verifies the dig-to-counterattack chain works
        total_points = 50
        valid_results = 0
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="A", seed=42 + i)
            if result.winner in ["A", "B"]:
                valid_results += 1
        
        # All simulations should produce valid results
        self.assertEqual(valid_results, total_points, "All point simulations should produce valid winners")

    def test_100_percent_set_error(self):
        """Test: 100% setting errors should prevent attacks"""
        # Team with perfect reception but terrible setting
        team_a_data = self.team_a_template.copy()
        team_a_data['serve_probabilities']['ace'] = 0.0
        team_a_data['serve_probabilities']['in_play'] = 1.0
        team_a_data['serve_probabilities']['error'] = 0.0
        
        team_a_data['receive_probabilities']['in_play_serve']['excellent'] = 1.0
        team_a_data['receive_probabilities']['in_play_serve']['good'] = 0.0
        team_a_data['receive_probabilities']['in_play_serve']['poor'] = 0.0
        team_a_data['receive_probabilities']['in_play_serve']['error'] = 0.0
        
        # 100% setting errors
        team_a_data['set_probabilities']['excellent_reception']['excellent'] = 0.0
        team_a_data['set_probabilities']['excellent_reception']['good'] = 0.0
        team_a_data['set_probabilities']['excellent_reception']['poor'] = 0.0
        team_a_data['set_probabilities']['excellent_reception']['error'] = 1.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Team A should lose most points when receiving due to set errors
        wins_a = 0
        total_points = 100
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=42 + i)
            if result.winner == "A":
                wins_a += 1
                
        win_rate = wins_a / total_points
        # Should lose most points due to setting errors
        self.assertLess(win_rate, 0.15, f"Expected low win rate with 100% set errors, got {win_rate:.2%}")

    def test_extreme_attack_error_rate(self):
        """Test: 100% attack errors should result in point loss"""
        # Team with good buildup but terrible attacking
        team_a_data = self.team_a_template.copy()
        
        # Perfect attack opportunities
        team_a_data['attack_probabilities']['excellent_set']['kill'] = 0.0
        team_a_data['attack_probabilities']['excellent_set']['defended'] = 0.0
        team_a_data['attack_probabilities']['excellent_set']['error'] = 1.0
        
        team_a_data['attack_probabilities']['good_set']['kill'] = 0.0
        team_a_data['attack_probabilities']['good_set']['defended'] = 0.0
        team_a_data['attack_probabilities']['good_set']['error'] = 1.0
        
        team_a_data['attack_probabilities']['poor_set']['kill'] = 0.0
        team_a_data['attack_probabilities']['poor_set']['defended'] = 0.0
        team_a_data['attack_probabilities']['poor_set']['error'] = 1.0
        
        team_a = Team.from_dict(team_a_data)
        team_b = Team.from_dict(self.team_b_template)
        
        # Simulate points - Team A should lose when it gets to attack
        total_points = 50
        team_b_wins = 0
        
        for i in range(total_points):
            result = simulate_point(team_a, team_b, serving_team="B", seed=42 + i)
            if result.winner == "B":
                team_b_wins += 1
        
        win_rate_b = team_b_wins / total_points
        # Team B should win more due to Team A's attack errors
        self.assertGreater(win_rate_b, 0.4, f"Expected higher win rate for opponent with 100% attack errors, got {win_rate_b:.2%}")

    def test_probability_normalization(self):
        """Test: Verify probabilities are properly normalized"""
        # This is more of a unit test for the Team class
        team_data = self.team_a_template.copy()
        
        # Verify that probabilities sum to 1.0 (within floating point precision)
        serve_probs = team_data['serve_probabilities']
        serve_sum = serve_probs['ace'] + serve_probs['in_play'] + serve_probs['error']
        self.assertAlmostEqual(serve_sum, 1.0, places=6, 
                              msg=f"Serve probabilities should sum to 1.0, got {serve_sum}")
        
        # Check reception probabilities
        for serve_type in team_data['receive_probabilities']:
            recv_probs = team_data['receive_probabilities'][serve_type]
            recv_sum = recv_probs['excellent'] + recv_probs['good'] + recv_probs['poor'] + recv_probs['error']
            self.assertAlmostEqual(recv_sum, 1.0, places=6,
                                  msg=f"Reception probabilities for {serve_type} should sum to 1.0, got {recv_sum}")


def run_extreme_tests():
    """Run all extreme statistics tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    print("Running Extreme Statistics Tests...")
    print("=" * 50)
    run_extreme_tests()