#!/usr/bin/env python3
"""
Comprehensive test runner for BVSim
Runs all tests in the proper order following constitutional testing principles:
Contract → Integration → Performance → Unit
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_command(cmd, description, timeout=120):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
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
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ PASSED in {duration:.1f}s")
            return True
        else:
            print(f"❌ FAILED (exit code {result.returncode}) in {duration:.1f}s")
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


def run_unittest_module(module_path, description, timeout=120):
    """Run a unittest module"""
    cmd = ['python3', '-m', 'unittest', '-v', module_path]
    return run_command(cmd, description, timeout)


def run_custom_test(script_path, description):
    """Run a custom test script"""
    cmd = ['python3', str(script_path)]
    return run_command(cmd, description)


def main():
    """Run all tests in constitutional order"""
    print("🏐 BVSim Comprehensive Test Suite")
    print("Following constitutional testing order: Contract → Integration → Performance → Unit")
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    results = []
    total_start = time.time()
    
    # Phase 1: Contract Tests (CLI behavior contracts)
    print(f"\n{'🏛️  CONTRACT TESTS':<60}")
    contract_tests = [
        ('tests.contract.test_bvsim_core_cli', 'Contract Tests - BVSim Core CLI'),
    ]
    
    for test_module, description in contract_tests:
        success = run_unittest_module(test_module, description)
        results.append((description, success))
    
    # Phase 2: Integration Tests (libraries working together)
    print(f"\n{'🔗 INTEGRATION TESTS':<60}")
    integration_tests = [
        ('tests.integration.test_library_boundaries', 'Integration Tests - Library Boundaries'),
        ('tests/integration/test_unified_cli.py', 'Integration Tests - Unified CLI'),
    ]
    
    for test_item, description in integration_tests:
        if test_item.endswith('.py'):
            # Custom test script
            success = run_custom_test(Path(test_item), description)
        else:
            # Unittest module
            success = run_unittest_module(test_item, description)
        results.append((description, success))
    
    # Phase 3: Performance Tests (speed requirements)
    print(f"\n{'⚡ PERFORMANCE TESTS':<60}")
    performance_tests = [
        ('tests.performance.test_performance', 'Performance Tests - Speed Requirements'),
    ]
    
    for test_module, description in performance_tests:
        success = run_unittest_module(test_module, description, timeout=300)  # 5 min timeout
        results.append((description, success))
    
    # Phase 4: Unit Tests (complex algorithms only)
    print(f"\n{'🔬 UNIT TESTS':<60}")
    unit_tests = [
        ('tests.unit.test_state_machine', 'Unit Tests - State Machine Logic'),
        ('tests.unit.test_rally_scenarios', 'Unit Tests - Rally Scenarios'),
        ('tests.unit.test_set_conditionals', 'Unit Tests - Set Conditionals'),
    ]
    
    for test_module, description in unit_tests:
        success = run_unittest_module(test_module, description)
        results.append((description, success))
    
    # Summary
    total_duration = time.time() - total_start
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n{'='*80}")
    print(f"🏐 TEST SUITE SUMMARY")
    print(f"{'='*80}")
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    print(f"⏱️  Total time: {total_duration:.1f}s")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! BVSim is ready for production.")
        return 0
    else:
        print(f"\n💥 {total - passed} TEST(S) FAILED! Please fix before deployment.")
        return 1


def show_help():
    """Show help message"""
    print("""
BVSim Test Runner

Usage:
    python3 run_tests.py              # Run all tests
    python3 run_tests.py --help       # Show this help

Test Categories (run in constitutional order):
    Contract Tests     - Verify CLI behavior matches contracts
    Integration Tests  - Test library boundaries and unified CLI  
    Performance Tests  - Verify speed requirements (10k points < 60s)
    Unit Tests        - Test complex algorithms (state machine, etc.)

Examples:
    python3 run_tests.py                    # Run full test suite
    python3 -m unittest tests.unit.test_state_machine  # Run specific test
    python3 tests/integration/test_unified_cli.py       # Run unified CLI tests
    """)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        show_help()
        sys.exit(0)
    
    sys.exit(main())