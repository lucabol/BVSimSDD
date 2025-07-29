#!/usr/bin/env python3
"""
Integration tests for library boundaries and inter-library contracts.
Tests that libraries work together correctly and maintain proper data flow.
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_stats.models import SimulationResults, PointResult
from bvsim_stats.analysis import analyze_simulation_results, sensitivity_analysis
from bvsim_cli.templates import create_team_template
from bvsim_cli.simulation import run_large_simulation
from bvsim_cli.comparison import compare_teams


class TestLibraryBoundaries(unittest.TestCase):
    """Test integration between different libraries"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create sample team data
        self.team_data = {
            'name': 'Integration Test Team',
            'serve_probabilities': {'ace': 0.1, 'in_play': 0.85, 'error': 0.05},
            'receive_probabilities': {
                'in_play_serve': {'excellent': 0.4, 'good': 0.4, 'poor': 0.15, 'error': 0.05}
            },
            'attack_probabilities': {
                'excellent_set': {'kill': 0.7, 'error': 0.15, 'defended': 0.15},
                'good_set': {'kill': 0.5, 'error': 0.25, 'defended': 0.25},
                'poor_set': {'kill': 0.3, 'error': 0.4, 'defended': 0.3}
            },
            'block_probabilities': {
                'power_attack': {'stuff': 0.2, 'deflection': 0.3, 'no_touch': 0.5}
            },
            'dig_probabilities': {
                'deflected_attack': {'excellent': 0.3, 'good': 0.4, 'poor': 0.25, 'error': 0.05}
            }
        }
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_core_to_stats_data_flow(self):
        """Test that bvsim-core point data flows correctly to bvsim-stats"""
        # Create teams using bvsim-core
        team_a = Team.from_dict(self.team_data.copy())
        team_b_data = self.team_data.copy()
        team_b_data['name'] = 'Team B'
        team_b = Team.from_dict(team_b_data)
        
        # Simulate points using bvsim-core
        points = []
        for i in range(100):
            serving_team = "A" if i % 2 == 0 else "B"
            point = simulate_point(team_a, team_b, serving_team=serving_team, seed=i)
            
            point_data = {
                'serving_team': point.serving_team,
                'winner': point.winner,
                'point_type': point.point_type,
                'duration': len(point.states),
                'states': [
                    {'team': s.team, 'action': s.action, 'quality': s.quality}
                    for s in point.states
                ]
            }
            points.append(point_data)
        
        # Create simulation results for bvsim-stats
        sim_results = SimulationResults(
            team_a_name=team_a.name,
            team_b_name=team_b.name,
            total_points=len(points),
            points=[
                PointResult(
                    serving_team=p['serving_team'],
                    winner=p['winner'],
                    point_type=p['point_type'],
                    duration=p['duration'],
                    states=p['states']
                ) for p in points
            ]
        )
        
        # Analyze using bvsim-stats
        analysis = analyze_simulation_results(sim_results)
        
        # Verify data integrity across library boundary
        self.assertEqual(analysis.total_points, 100)
        self.assertEqual(analysis.team_a_wins + analysis.team_b_wins, 100)
        self.assertGreater(len(analysis.point_type_breakdown), 0)
        self.assertAlmostEqual(analysis.team_a_win_rate + analysis.team_b_win_rate, 100.0, places=1)
    
    def test_cli_to_core_integration(self):
        """Test that bvsim-cli properly interfaces with bvsim-core"""
        # Create team using bvsim-cli
        team_file = os.path.join(self.test_dir, "test_team.yaml")
        created_file = create_team_template(
            team_name="CLI Test Team",
            template_type="basic",
            output_file=team_file
        )
        
        self.assertEqual(created_file, team_file)
        self.assertTrue(os.path.exists(team_file))
        
        # Load team using bvsim-core
        team = Team.from_yaml_file(team_file)
        
        # Verify team data integrity
        self.assertEqual(team.name, "CLI Test Team")
        self.assertIn('ace', team.serve_probabilities)
        self.assertIn('in_play_serve', team.receive_probabilities)
        
        # Verify probability distributions sum to 1.0
        serve_sum = sum(team.serve_probabilities.values())
        self.assertAlmostEqual(serve_sum, 1.0, places=3)
        
        for condition, probs in team.receive_probabilities.items():
            receive_sum = sum(probs.values())
            self.assertAlmostEqual(receive_sum, 1.0, places=3)
    
    def test_cli_simulation_to_stats_pipeline(self):
        """Test complete pipeline: bvsim-cli -> bvsim-core -> bvsim-stats"""
        # Create teams using bvsim-cli
        team_a_file = os.path.join(self.test_dir, "team_a.yaml")
        team_b_file = os.path.join(self.test_dir, "team_b.yaml")
        
        create_team_template("Pipeline Team A", "basic", team_a_file)
        create_team_template("Pipeline Team B", "basic", team_b_file)
        
        # Load teams
        team_a = Team.from_yaml_file(team_a_file)
        team_b = Team.from_yaml_file(team_b_file)
        
        # Run simulation using bvsim-cli functionality
        results = run_large_simulation(
            team_a=team_a,
            team_b=team_b,
            num_points=50,
            seed=12345,
            show_progress=False
        )
        
        # Create simulation results file
        results_file = os.path.join(self.test_dir, "results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f)
        
        # Load and analyze using bvsim-stats
        sim_results = SimulationResults.from_json_file(results_file)
        analysis = analyze_simulation_results(sim_results)
        
        # Verify end-to-end data integrity
        self.assertEqual(sim_results.total_points, 50)
        self.assertEqual(analysis.total_points, 50)
        self.assertEqual(sim_results.team_a_name, "Pipeline Team A")
        self.assertEqual(sim_results.team_b_name, "Pipeline Team B")
        
        # Verify statistics are consistent
        expected_a_wins = sum(1 for p in sim_results.points if p.winner == "A")
        self.assertEqual(analysis.team_a_wins, expected_a_wins)
    
    def test_sensitivity_analysis_integration(self):
        """Test sensitivity analysis integrates properly with core simulation"""
        # Create teams
        team_a = Team.from_dict(self.team_data.copy())
        team_b_data = self.team_data.copy()
        team_b_data['name'] = 'Opponent Team'
        team_b = Team.from_dict(team_b_data)
        
        # Run sensitivity analysis (uses bvsim-core internally)
        sensitivity = sensitivity_analysis(
            team=team_a,
            opponent=team_b,
            parameter="attack_probabilities.excellent_set.kill",
            param_range="0.6,0.8,0.1",
            points_per_test=20,  # Small number for fast test
            base_serving="A"
        )
        
        # Verify sensitivity analysis results
        self.assertEqual(len(sensitivity.data_points), 3)  # 0.6, 0.7, 0.8
        self.assertEqual(sensitivity.parameter_name, "attack_probabilities.excellent_set.kill")
        self.assertIsInstance(sensitivity.base_win_rate, float)
        self.assertIn(sensitivity.impact_factor, ["LOW", "MEDIUM", "HIGH"])
        
        # Verify data points have correct structure
        for point in sensitivity.data_points:
            self.assertIsInstance(point.parameter_value, float)
            self.assertIsInstance(point.win_rate, float)
            self.assertIsInstance(point.change_from_base, float)
            self.assertGreaterEqual(point.win_rate, 0)
            self.assertLessEqual(point.win_rate, 100)
    
    def test_team_comparison_integration(self):
        """Test team comparison integrates with core simulation"""
        # Create multiple teams
        teams = []
        for i in range(3):
            team_data = self.team_data.copy()
            team_data['name'] = f'Comparison Team {i+1}'
            # Slightly vary attack probabilities for different teams
            team_data['attack_probabilities']['excellent_set']['kill'] = 0.6 + (i * 0.1)
            team_data['attack_probabilities']['excellent_set']['error'] = 0.2 - (i * 0.05)
            team_data['attack_probabilities']['excellent_set']['defended'] = 0.2 - (i * 0.05)
            teams.append(Team.from_dict(team_data))
        
        # Run comparison
        comparison = compare_teams(teams, points_per_matchup=30)
        
        # Verify comparison structure
        self.assertEqual(len(comparison['teams']), 3)
        self.assertEqual(comparison['points_per_matchup'], 30)
        self.assertIn('results_matrix', comparison)
        self.assertIn('rankings', comparison)
        
        # Verify matrix completeness
        for team_name in comparison['teams']:
            self.assertIn(team_name, comparison['results_matrix'])
            for other_team in comparison['teams']:
                if team_name != other_team:
                    self.assertIn(other_team, comparison['results_matrix'][team_name])
                    win_rate = comparison['results_matrix'][team_name][other_team]
                    self.assertGreaterEqual(win_rate, 0)
                    self.assertLessEqual(win_rate, 100)
        
        # Verify rankings
        self.assertEqual(len(comparison['rankings']), 3)
        for ranking in comparison['rankings']:
            self.assertIn('name', ranking)
            self.assertIn('average_win_rate', ranking)
    
    def test_yaml_json_data_consistency(self):
        """Test that data remains consistent across YAML/JSON serialization"""
        # Create team via CLI template
        team_file = os.path.join(self.test_dir, "consistency_team.yaml")
        create_team_template("Consistency Team", "advanced", team_file)
        
        # Load team
        original_team = Team.from_yaml_file(team_file)
        
        # Convert to dict and back
        team_dict = original_team.to_dict()
        reconstructed_team = Team.from_dict(team_dict)
        
        # Verify consistency
        self.assertEqual(original_team.name, reconstructed_team.name)
        self.assertEqual(original_team.serve_probabilities, reconstructed_team.serve_probabilities)
        self.assertEqual(original_team.receive_probabilities, reconstructed_team.receive_probabilities)
        self.assertEqual(original_team.attack_probabilities, reconstructed_team.attack_probabilities)
        self.assertEqual(original_team.block_probabilities, reconstructed_team.block_probabilities)
        self.assertEqual(original_team.dig_probabilities, reconstructed_team.dig_probabilities)
        
        # Test YAML round-trip
        yaml_str = original_team.to_yaml()
        yaml_reconstructed = Team.from_yaml(yaml_str)
        
        self.assertEqual(original_team.name, yaml_reconstructed.name)
        self.assertEqual(original_team.serve_probabilities, yaml_reconstructed.serve_probabilities)
    
    def test_error_handling_across_boundaries(self):
        """Test that errors are properly handled across library boundaries"""
        # Test invalid team file handling
        invalid_file = os.path.join(self.test_dir, "nonexistent.yaml")
        
        with self.assertRaises(FileNotFoundError):
            Team.from_yaml_file(invalid_file)
        
        # Test invalid simulation data (invalid JSON file)
        invalid_json_file = os.path.join(self.test_dir, "invalid.json")
        with open(invalid_json_file, 'w') as f:
            f.write("invalid json content {")
        
        with self.assertRaises(json.JSONDecodeError):
            SimulationResults.from_json_file(invalid_json_file)
        
        # Test invalid sensitivity analysis parameter
        team = Team.from_dict(self.team_data)
        
        with self.assertRaises(ValueError):
            sensitivity_analysis(
                team=team,
                opponent=team,
                parameter="nonexistent.parameter",
                param_range="0.1,0.9,0.1",
                points_per_test=10
            )


if __name__ == '__main__':
    unittest.main()