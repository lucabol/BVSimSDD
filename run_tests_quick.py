#!/usr/bin/env python3
"""
Quick test runner for BVSim - excludes performance tests for faster development cycles
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_command(cmd, description, timeout=60):
    """Run a command and return success status"""
    print(f"Running: {description}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=get_test_env()
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ PASSED in {duration:.1f}s")
            return True
        else:
            print(f"❌ FAILED (exit code {result.returncode}) in {duration:.1f}s")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False


def get_test_env():
    """Get environment with proper PYTHONPATH"""
    env = os.environ.copy()
    current_dir = Path(__file__).parent.resolve()
    env['PYTHONPATH'] = str(current_dir / 'src')
    return env


def main():
    """Run essential tests quickly"""
    print("🏐 BVSim Quick Test Suite (excluding performance tests)")
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    results = []
    total_start = time.time()
    
    # Essential tests for development
    tests = [
        (['python3', 'tests/integration/test_unified_cli.py'], 'Unified CLI Integration'),
        (['python3', '-m', 'unittest', '-v', 'tests.unit.test_state_machine'], 'State Machine Unit Tests'),
        (['python3', '-m', 'unittest', '-v', 'tests.integration.test_library_boundaries'], 'Library Boundaries'),
    ]
    
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Summary
    total_duration = time.time() - total_start
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n📊 Quick Test Results: {passed}/{total} tests passed")
    print(f"⏱️  Total time: {total_duration:.1f}s")
    
    if passed == total:
        print("🎉 Essential tests passed! Ready for development.")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())