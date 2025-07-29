#!/usr/bin/env python3
"""
Contract tests for bvsim-core CLI commands.
These tests verify CLI behavior matches the contracts defined in contracts/bvsim-core-cli.md

IMPORTANT: These tests MUST fail initially before implementation begins (TDD requirement).
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestBVSimCoreCLI(unittest.TestCase):
    """Contract tests for bvsim-core CLI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.valid_team_a_yaml = """
name: "Elite Attackers"
serve_probabilities:
  ace: 0.12
  in_play: 0.83
  error: 0.05

receive_probabilities:
  in_play_serve:
    excellent: 0.35
    good: 0.45
    poor: 0.15
    error: 0.05

set_probabilities:
  excellent_reception:
    excellent: 0.70
    good: 0.25
    poor: 0.05
  good_reception:
    excellent: 0.30
    good: 0.60
    poor: 0.10
  poor_reception:
    excellent: 0.05
    good: 0.25
    poor: 0.70

attack_probabilities:
  excellent_set:
    kill: 0.85
    error: 0.05
    defended: 0.10
  good_set:
    kill: 0.70
    error: 0.10
    defended: 0.20
  poor_set:
    kill: 0.45
    error: 0.25
    defended: 0.30

block_probabilities:
  power_attack:
    stuff: 0.20
    deflection_to_attack: 0.15
    deflection_to_defense: 0.15
    no_touch: 0.50

dig_probabilities:
  deflected_attack:
    excellent: 0.25
    good: 0.45
    poor: 0.25
    error: 0.05
"""

        self.valid_team_b_yaml = """
name: "Strong Defense"
serve_probabilities:
  ace: 0.08
  in_play: 0.87
  error: 0.05

receive_probabilities:
  in_play_serve:
    excellent: 0.40
    good: 0.40
    poor: 0.15
    error: 0.05

set_probabilities:
  excellent_reception:
    excellent: 0.75
    good: 0.20
    poor: 0.05
  good_reception:
    excellent: 0.35
    good: 0.55
    poor: 0.10
  poor_reception:
    excellent: 0.05
    good: 0.20
    poor: 0.75

attack_probabilities:
  excellent_set:
    kill: 0.75
    error: 0.10
    defended: 0.15
  good_set:
    kill: 0.60
    error: 0.15
    defended: 0.25
  poor_set:
    kill: 0.35
    error: 0.30
    defended: 0.35

block_probabilities:
  power_attack:
    stuff: 0.25
    deflection_to_attack: 0.175
    deflection_to_defense: 0.175
    no_touch: 0.40

dig_probabilities:
  deflected_attack:
    excellent: 0.35
    good: 0.40
    poor: 0.20
    error: 0.05
"""

        self.invalid_team_yaml = """
name: "Invalid Team"
serve_probabilities:
  ace: 0.5
  in_play: 0.6  # Sum = 1.1, should be 1.0
  error: 0.0
"""

        # Create test files
        self.team_a_file = os.path.join(self.test_dir, "team_a.yaml")
        self.team_b_file = os.path.join(self.test_dir, "team_b.yaml")
        self.invalid_team_file = os.path.join(self.test_dir, "invalid_team.yaml")
        
        with open(self.team_a_file, 'w') as f:
            f.write(self.valid_team_a_yaml)
        with open(self.team_b_file, 'w') as f:
            f.write(self.valid_team_b_yaml)
        with open(self.invalid_team_file, 'w') as f:
            f.write(self.invalid_team_yaml)

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)

    def run_command(self, cmd):
        """Run a command and return result"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            return result
        except Exception as e:
            self.fail(f"Failed to run command {cmd}: {e}")

    def test_simulate_point_valid_teams(self):
        """Test simulate-point with valid team configurations"""
        cmd = [
            "python3", "-m", "bvsim_core", "simulate-point",
            "--team-a", self.team_a_file,
            "--team-b", self.team_b_file,
            "--seed", "12345"
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 0 for valid inputs
        self.assertEqual(result.returncode, 0, 
                        f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr}")
        
        # Contract: Text output must contain required fields
        self.assertIn("Point Result:", result.stdout)
        self.assertIn("Serving Team:", result.stdout)
        self.assertIn("Winner:", result.stdout)
        self.assertIn("Point Type:", result.stdout)
        self.assertIn("States:", result.stdout)

    def test_simulate_point_json_output(self):
        """Test simulate-point JSON output format"""
        cmd = [
            "python3", "-m", "bvsim_core", "simulate-point",
            "--team-a", self.team_a_file,
            "--team-b", self.team_b_file,
            "--format", "json",
            "--seed", "12345"
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 0
        self.assertEqual(result.returncode, 0)
        
        # Contract: Must be valid JSON
        try:
            point_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
        
        # Contract: JSON must contain required fields
        required_fields = ["serving_team", "winner", "point_type", "states"]
        for field in required_fields:
            self.assertIn(field, point_data, f"Missing required field: {field}")
        
        # Contract: serving_team and winner must be "A" or "B"
        self.assertIn(point_data["serving_team"], ["A", "B"])
        self.assertIn(point_data["winner"], ["A", "B"])
        
        # Contract: states must be a non-empty list
        self.assertIsInstance(point_data["states"], list)
        self.assertGreater(len(point_data["states"]), 0)

    def test_simulate_point_invalid_team(self):
        """Test simulate-point with invalid team configuration"""
        cmd = [
            "python3", "-m", "bvsim_core", "simulate-point",
            "--team-a", self.invalid_team_file,
            "--team-b", self.team_b_file
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 1 for invalid team configuration
        self.assertEqual(result.returncode, 1)
        
        # Contract: Must show error message about invalid configuration
        self.assertIn("Invalid team configuration", result.stderr)

    def test_simulate_point_missing_file(self):
        """Test simulate-point with missing file"""
        cmd = [
            "python3", "-m", "bvsim_core", "simulate-point",
            "--team-a", "nonexistent.yaml",
            "--team-b", self.team_b_file
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 2 for file not found
        self.assertEqual(result.returncode, 2)
        
        # Contract: Must show file not found error
        self.assertIn("File not found", result.stderr)

    def test_simulate_point_reproducible_seed(self):
        """Test simulate-point reproducibility with same seed"""
        cmd_base = [
            "python3", "-m", "bvsim_core", "simulate-point",
            "--team-a", self.team_a_file,
            "--team-b", self.team_b_file,
            "--format", "json",
            "--seed", "12345"
        ]
        
        result1 = self.run_command(cmd_base)
        result2 = self.run_command(cmd_base)
        
        # Contract: Same seed must produce identical results
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)
        self.assertEqual(result1.stdout, result2.stdout, "Results should be identical with same seed")

    def test_validate_team_valid(self):
        """Test validate-team with valid configuration"""
        cmd = [
            "python3", "-m", "bvsim_core", "validate-team",
            "--team", self.team_a_file
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 0 for valid team
        self.assertEqual(result.returncode, 0)
        
        # Contract: Must show validation passed message
        self.assertIn("Team validation: PASSED", result.stdout)
        self.assertIn("All probability distributions valid", result.stdout)

    def test_validate_team_invalid(self):
        """Test validate-team with invalid configuration"""
        cmd = [
            "python3", "-m", "bvsim_core", "validate-team",
            "--team", self.invalid_team_file
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 1 for invalid team
        self.assertEqual(result.returncode, 1)
        
        # Contract: Must show validation failed message with specific errors
        self.assertIn("Team validation: FAILED", result.stdout)
        self.assertIn("sum to", result.stdout)  # Should mention probability sum error

    def test_validate_team_json_output(self):
        """Test validate-team JSON output format"""
        cmd = [
            "python3", "-m", "bvsim_core", "validate-team",
            "--team", self.team_a_file,
            "--format", "json"
        ]
        
        result = self.run_command(cmd)
        
        # Contract: Must return exit code 0
        self.assertEqual(result.returncode, 0)
        
        # Contract: Must be valid JSON
        try:
            validation_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
        
        # Contract: JSON must contain required fields
        required_fields = ["valid", "team_name", "errors"]
        for field in required_fields:
            self.assertIn(field, validation_data, f"Missing required field: {field}")
        
        # Contract: valid field must be boolean
        self.assertIsInstance(validation_data["valid"], bool)
        
        # Contract: errors must be a list
        self.assertIsInstance(validation_data["errors"], list)

    def test_help_flags(self):
        """Test that all commands support --help flag"""
        commands = [
            ["python3", "-m", "bvsim_core", "simulate-point", "--help"],
            ["python3", "-m", "bvsim_core", "validate-team", "--help"],
            ["python3", "-m", "bvsim_core", "--help"]
        ]
        
        for cmd in commands:
            result = self.run_command(cmd)
            
            # Contract: --help must return exit code 0
            self.assertEqual(result.returncode, 0, f"Command {cmd} --help failed")
            
            # Contract: --help must show usage information
            self.assertIn("usage:", result.stdout, f"Command {cmd} missing usage info")

    def test_version_flag(self):
        """Test that bvsim-core supports --version flag"""
        cmd = ["python3", "-m", "bvsim_core", "--version"]
        result = self.run_command(cmd)
        
        # Contract: --version must return exit code 0
        self.assertEqual(result.returncode, 0)
        
        # Contract: --version must show version in format x.y.z
        import re
        version_pattern = r'\d+\.\d+\.\d+'
        self.assertTrue(re.search(version_pattern, result.stdout),
                       f"Invalid version format: {result.stdout}")


if __name__ == '__main__':
    unittest.main()