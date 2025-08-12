#!/usr/bin/env python3
"""Contract tests for bvsim-core CLI commands."""

import json
import os
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path


class TestBVSimCoreCLI(unittest.TestCase):
    def setUp(self):
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
  in_play: 0.6
  error: 0.0
"""
        # Write files
        self.team_a_file = os.path.join(self.test_dir, "team_a.yaml")
        self.team_b_file = os.path.join(self.test_dir, "team_b.yaml")
        self.invalid_team_file = os.path.join(self.test_dir, "invalid_team.yaml")
        for path, content in [
            (self.team_a_file, self.valid_team_a_yaml),
            (self.team_b_file, self.valid_team_b_yaml),
            (self.invalid_team_file, self.invalid_team_yaml)
        ]:
            with open(path, 'w') as f:
                f.write(content)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def run_command(self, cmd):
        env = os.environ.copy()
        # Ensure src is on PYTHONPATH for module discovery when using system python
        src_path = str(Path(__file__).parent.parent.parent / 'src')
        env['PYTHONPATH'] = src_path + os.pathsep + env.get('PYTHONPATH', '')
        return subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent, env=env)

    def test_simulate_point_valid_teams(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'simulate-point', '--team-a', self.team_a_file, '--team-b', self.team_b_file, '--seed', '12345']
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        for token in ["Point Result:", "Serving Team:", "Winner:", "Point Type:", "States:"]:
            self.assertIn(token, result.stdout)

    def test_simulate_point_json_output(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'simulate-point', '--team-a', self.team_a_file, '--team-b', self.team_b_file, '--format', 'json', '--seed', '12345']
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        for field in ["serving_team", "winner", "point_type", "states"]:
            self.assertIn(field, data)
        self.assertIn(data['serving_team'], ['A', 'B'])
        self.assertIn(data['winner'], ['A', 'B'])
        self.assertIsInstance(data['states'], list)
        self.assertGreater(len(data['states']), 0)

    def test_simulate_point_invalid_team(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'simulate-point', '--team-a', self.invalid_team_file, '--team-b', self.team_b_file]
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid team configuration', result.stderr)

    def test_simulate_point_missing_file(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'simulate-point', '--team-a', 'missing.yaml', '--team-b', self.team_b_file]
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 2)
        self.assertIn('File not found', result.stderr)

    def test_simulate_point_reproducible_seed(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'simulate-point', '--team-a', self.team_a_file, '--team-b', self.team_b_file, '--format', 'json', '--seed', '12345']
        r1 = self.run_command(cmd)
        r2 = self.run_command(cmd)
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r1.stdout, r2.stdout)

    def test_validate_team_valid(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'validate-team', '--team', self.team_a_file]
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Team validation: PASSED', result.stdout)

    def test_validate_team_invalid(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'validate-team', '--team', self.invalid_team_file]
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Team validation: FAILED', result.stdout)

    def test_validate_team_json_output(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', 'validate-team', '--team', self.team_a_file, '--format', 'json']
        result = self.run_command(cmd)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        for f in ['valid', 'team_name', 'errors']:
            self.assertIn(f, data)
        self.assertIsInstance(data['errors'], list)

    def test_help_flags(self):
        py = sys.executable
        commands = [
            [py, '-m', 'bvsim_core', 'simulate-point', '--help'],
            [py, '-m', 'bvsim_core', 'validate-team', '--help'],
            [py, '-m', 'bvsim_core', '--help']
        ]
        for c in commands:
            r = self.run_command(c)
            self.assertEqual(r.returncode, 0)
            self.assertIn('usage:', r.stdout)

    def test_version_flag(self):
        py = sys.executable
        cmd = [py, '-m', 'bvsim_core', '--version']
        r = self.run_command(cmd)
        self.assertEqual(r.returncode, 0)
        import re
        self.assertRegex(r.stdout.strip(), r"\d+\.\d+\.\d+")


if __name__ == '__main__':
    unittest.main()