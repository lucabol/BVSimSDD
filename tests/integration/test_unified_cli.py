#!/usr/bin/env python3
"""
Integration tests for unified bvsim CLI
"""

import subprocess
import tempfile
import os
import json
from pathlib import Path


def run_bvsim(args, timeout=30):
    """Run bvsim command and return result"""
    cmd = ['python3', '-m', 'bvsim'] + args
    env = os.environ.copy()
    # Use absolute path for PYTHONPATH - go up two levels from tests/integration/
    current_dir = Path(__file__).parent.parent.parent.resolve()
    env['PYTHONPATH'] = str(current_dir / 'src')
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env
    )
    return result


def test_version():
    """Test --version command"""
    result = run_bvsim(['--version'])
    assert result.returncode == 0
    assert 'bvsim 1.0.0' in result.stdout
    print("✓ Version command works")


def test_help():
    """Test --help command"""
    result = run_bvsim(['--help'])
    assert result.returncode == 0
    assert 'Beach Volleyball Point Simulator' in result.stdout
    assert 'skills' in result.stdout
    assert 'compare' in result.stdout
    assert 'simulate' in result.stdout
    print("✓ Help command works")


def test_skills_quick():
    """Test skills command with quick analysis"""
    result = run_bvsim(['skills', '--quick'])
    assert result.returncode == 0
    assert 'Skill Impact Analysis' in result.stdout
    assert 'serve_probabilities.ace' in result.stdout
    print("✓ Skills quick analysis works")


def test_create_team():
    """Test create-team command"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            result = run_bvsim(['create-team', 'Test Team'])
            assert result.returncode == 0, f"Command failed: {result.stderr}"
            
            # Check that team file was created
            team_file = Path('test_team.yaml')
            assert team_file.exists(), f"Team file not created in {tmpdir}"
            print("✓ Create team works")
        finally:
            os.chdir(original_dir)


def test_compare_quick():
    """Test compare command with quick analysis"""
    result = run_bvsim(['compare', '--quick'])
    assert result.returncode == 0
    assert 'Team Comparison Matrix' in result.stdout
    print("✓ Compare command works")


def test_simulate_and_analyze():
    """Test simulate then analyze workflow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Run simulation
            result = run_bvsim(['simulate', '--points', '100', '--output', 'test.json'])
            assert result.returncode == 0, f"Simulate failed: {result.stderr}"
            assert Path('test.json').exists()
            
            # Analyze results
            result = run_bvsim(['analyze', 'test.json'])
            assert result.returncode == 0, f"Analyze failed: {result.stderr}"
            assert 'Simulation Analysis' in result.stdout
            
            print("✓ Simulate and analyze workflow works")
        finally:
            os.chdir(original_dir)


def test_skills_with_team():
    """Test skills command with custom team"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Create a team
            result = run_bvsim(['create-team', 'My Team'])
            assert result.returncode == 0, f"Create team failed: {result.stderr}"
            
            # Analyze skills for that team
            result = run_bvsim(['skills', 'my_team', '--quick'])
            assert result.returncode == 0, f"Skills analysis failed: {result.stderr}"
            assert 'Skill Impact Analysis' in result.stdout
            
            print("✓ Skills with custom team works")
        finally:
            os.chdir(original_dir)


def test_skills_custom_multi_file():
    """Test skills command with multiple custom delta files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Create test delta files
            delta1_content = """# Test delta 1
serve_probabilities.ace: 0.05
attack_probabilities.excellent_set.kill: 0.08"""
            
            delta2_content = """# Test delta 2
receive_probabilities.in_play_serve.excellent: 0.10
block_probabilities.power_attack.stuff: 0.06"""
            
            with open('scenario1.yaml', 'w') as f:
                f.write(delta1_content)
            with open('scenario2.yaml', 'w') as f:
                f.write(delta2_content)
            
            # Test multi-file custom analysis
            result = run_bvsim(['skills', '--custom', 'scenario1.yaml', 'scenario2.yaml', '--quick'])
            assert result.returncode == 0, f"Multi-file custom failed: {result.stderr}"
            assert 'Multi-File Skill Impact Analysis' in result.stdout
            assert 'scenario1' in result.stdout
            assert 'scenario2' in result.stdout
            assert 'Configuration' in result.stdout
            
            print("✓ Multi-file custom skills analysis works")
        finally:
            os.chdir(original_dir)


def main():
    """Run all tests"""
    print("Testing unified bvsim CLI...")
    
    try:
        test_version()
        test_help()
        test_skills_quick()
        test_create_team()
        test_compare_quick()
        test_simulate_and_analyze()
        test_skills_with_team()
        test_skills_custom_multi_file()
        
        print("\n🎉 All tests passed! Unified CLI is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())