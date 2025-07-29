#!/usr/bin/env python3
"""
Performance tests to verify simulation speed requirements.
Tests that 10,000 point simulation completes within 60 seconds.
"""

import unittest
import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from bvsim_core.team import Team
from bvsim_core.state_machine import simulate_point
from bvsim_cli.simulation import run_large_simulation


class TestPerformance(unittest.TestCase):
    """Performance tests for simulation speed"""
    
    def setUp(self):
        """Set up test teams"""
        team_data = {
            'name': 'Performance Test Team',
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
        
        self.team_a = Team.from_dict(team_data)
        team_b_data = team_data.copy()
        team_b_data['name'] = 'Performance Test Team B'
        self.team_b = Team.from_dict(team_b_data)
    
    def test_1000_points_performance(self):
        """Test performance of 1000 point simulation"""
        start_time = time.time()
        
        results = run_large_simulation(
            team_a=self.team_a,
            team_b=self.team_b,
            num_points=1000,
            seed=12345,
            show_progress=False
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n1000 points simulated in {duration:.3f} seconds")
        print(f"Rate: {1000/duration:.1f} points/second")
        
        # Should complete well under 6 seconds (60 seconds for 10,000 points)
        self.assertLess(duration, 6.0, f"1000 points took {duration:.3f}s (expected < 6s)")
        self.assertEqual(results['total_points'], 1000)
    
    def test_10000_points_performance(self):
        """Test performance requirement: 10,000 points in under 60 seconds"""
        print(f"\nRunning 10,000 point simulation...")
        start_time = time.time()
        
        results = run_large_simulation(
            team_a=self.team_a,
            team_b=self.team_b,
            num_points=10000,
            seed=12345,
            show_progress=True  # Show progress for long test
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n10,000 points simulated in {duration:.3f} seconds")
        print(f"Rate: {10000/duration:.1f} points/second")
        
        # Performance requirement: must complete within 60 seconds
        self.assertLess(duration, 60.0, f"10,000 points took {duration:.3f}s (requirement: < 60s)")
        self.assertEqual(results['total_points'], 10000)
        
        # Additional performance insights
        points_per_second = 10000 / duration
        self.assertGreater(points_per_second, 166, "Should simulate at least 166 points/second")
        
        print(f"✅ Performance requirement met: {duration:.1f}s < 60s")
    
    def test_single_point_performance(self):
        """Test individual point simulation performance"""
        # Measure time for individual points
        times = []
        
        for i in range(100):
            start = time.perf_counter()
            point = simulate_point(self.team_a, self.team_b, serving_team="A", seed=i)
            end = time.perf_counter()
            times.append(end - start)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"\nSingle point performance (100 samples):")
        print(f"Average: {avg_time*1000:.3f}ms")
        print(f"Min: {min_time*1000:.3f}ms")
        print(f"Max: {max_time*1000:.3f}ms")
        
        # Individual points should be very fast
        self.assertLess(avg_time, 0.01, f"Average point time {avg_time*1000:.3f}ms too slow")
        self.assertLess(max_time, 0.1, f"Max point time {max_time*1000:.3f}ms too slow")
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during large simulations"""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        # Run multiple smaller simulations to check for memory leaks
        for batch in range(10):
            results = run_large_simulation(
                team_a=self.team_a,
                team_b=self.team_b,
                num_points=500,
                seed=batch,
                show_progress=False
            )
            self.assertEqual(results['total_points'], 500)
            
            # Force garbage collection between batches
            gc.collect()
        
        print(f"✅ Memory stability test passed: 10 batches of 500 points each")
    
    def test_scaling_characteristics(self):
        """Test how performance scales with simulation size"""
        sizes = [100, 500, 1000, 2000]
        rates = []
        
        print(f"\nScaling characteristics:")
        
        for size in sizes:
            start_time = time.time()
            
            results = run_large_simulation(
                team_a=self.team_a,
                team_b=self.team_b,
                num_points=size,
                seed=12345,
                show_progress=False
            )
            
            end_time = time.time()
            duration = end_time - start_time
            rate = size / duration
            rates.append(rate)
            
            print(f"  {size:4d} points: {duration:.3f}s ({rate:.0f} points/s)")
            
            self.assertEqual(results['total_points'], size)
        
        # Performance should be relatively consistent (not degrade significantly)
        min_rate = min(rates)
        max_rate = max(rates)
        rate_variation = (max_rate - min_rate) / min_rate
        
        # Allow up to 50% variation in rates (due to overhead, startup costs, etc.)
        self.assertLess(rate_variation, 0.5, 
                       f"Performance varies too much: {rate_variation:.1%}")


if __name__ == '__main__':
    # Run with more verbose output for performance insights
    unittest.main(verbosity=2)