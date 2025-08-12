#!/usr/bin/env python3
"""Tests that the compare-teams command accepts Basic / Advanced as template identifiers."""

import json
import subprocess
import sys
from pathlib import Path


def run_cli(args):
    """Helper to run the bvsim_cli module as a subprocess and capture output."""
    cmd = [sys.executable, '-m', 'bvsim_cli'] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result


def test_compare_teams_basic_advanced_text():
    """Basic smoke test for text output using Basic,Advanced identifiers."""
    result = run_cli(['compare-teams', '--teams', 'Basic,Advanced', '--points', '10', '--format', 'text'])
    assert result.returncode == 0, f"Non-zero exit (stderr): {result.stderr}"
    assert 'Team Comparison Matrix' in result.stdout
    assert 'Basic' in result.stdout
    assert 'Advanced' in result.stdout


def test_compare_teams_basic_advanced_json():
    """Verify JSON output structure with template identifiers."""
    result = run_cli(['compare-teams', '--teams', 'basic,advanced', '--points', '5', '--format', 'json'])
    assert result.returncode == 0, f"Non-zero exit (stderr): {result.stderr}"
    data = json.loads(result.stdout)
    assert 'teams' in data and set(data['teams']) == {'Basic', 'Advanced'}
    assert 'results_matrix' in data
    assert 'Basic' in data['results_matrix'] and 'Advanced' in data['results_matrix']
    # Ensure matrix contains both directional win rates
    assert 'Advanced' in data['results_matrix']['Basic']
    assert 'Basic' in data['results_matrix']['Advanced']
