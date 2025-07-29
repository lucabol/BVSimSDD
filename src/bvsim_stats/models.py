#!/usr/bin/env python3
"""
Data models for statistical analysis results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import json


@dataclass
class PointResult:
    """Individual point result from simulation"""
    serving_team: str
    winner: str
    point_type: str
    duration: int
    states: List[Dict[str, str]]


@dataclass 
class SimulationResults:
    """Complete simulation results with multiple points"""
    team_a_name: str
    team_b_name: str
    total_points: int
    points: List[PointResult]
    
    @classmethod
    def from_json_file(cls, file_path: str) -> 'SimulationResults':
        """Load simulation results from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        points = []
        for point_data in data['points']:
            point = PointResult(
                serving_team=point_data['serving_team'],
                winner=point_data['winner'],
                point_type=point_data['point_type'],
                duration=point_data['duration'],
                states=point_data['states']
            )
            points.append(point)
        
        return cls(
            team_a_name=data['team_a_name'],
            team_b_name=data['team_b_name'],
            total_points=data['total_points'],
            points=points
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'team_a_name': self.team_a_name,
            'team_b_name': self.team_b_name,
            'total_points': self.total_points,
            'points': [
                {
                    'serving_team': p.serving_team,
                    'winner': p.winner,
                    'point_type': p.point_type,
                    'duration': p.duration,
                    'states': p.states
                }
                for p in self.points
            ]
        }


@dataclass
class AnalysisResults:
    """Statistical analysis results"""
    total_points: int
    team_a_wins: int
    team_b_wins: int
    team_a_win_rate: float
    team_b_win_rate: float
    point_type_breakdown: Dict[str, int]
    point_type_percentages: Dict[str, float]
    average_duration: float
    
    def to_text(self, team_a_name: str = "Team A", team_b_name: str = "Team B") -> str:
        """Format as text output"""
        lines = [
            "Simulation Analysis:",
            f"Total Points: {self.total_points}",
            f"{team_a_name} Wins: {self.team_a_wins} ({self.team_a_win_rate:.2f}%)",
            f"{team_b_name} Wins: {self.team_b_wins} ({self.team_b_win_rate:.2f}%)",
            "",
            "Point Types:"
        ]
        
        for point_type, count in self.point_type_breakdown.items():
            percentage = self.point_type_percentages[point_type]
            lines.append(f"- {point_type.title()}: {count} ({percentage:.2f}%)")
        
        lines.append(f"\nAverage Point Duration: {self.average_duration:.1f} states")
        
        # Add breakdown data if available
        if hasattr(self, 'breakdown_data') and self.breakdown_data:
            lines.append("\n--- Detailed Breakdown ---")
            
            # Point types by team
            lines.append(f"\n{team_a_name} Point Types:")
            team_a_types = self.breakdown_data.get("team_a_point_types", {})
            for point_type, count in team_a_types.items():
                percentage = (count / self.team_a_wins) * 100 if self.team_a_wins > 0 else 0
                lines.append(f"  - {point_type.title()}: {count} ({percentage:.1f}%)")
            
            lines.append(f"\n{team_b_name} Point Types:")
            team_b_types = self.breakdown_data.get("team_b_point_types", {})
            for point_type, count in team_b_types.items():
                percentage = (count / self.team_b_wins) * 100 if self.team_b_wins > 0 else 0
                lines.append(f"  - {point_type.title()}: {count} ({percentage:.1f}%)")
            
            # Duration breakdown
            lines.append("\nDuration by Point Type:")
            duration_data = self.breakdown_data.get("duration_by_type", {})
            for point_type, stats in duration_data.items():
                lines.append(f"  - {point_type.title()}: avg={stats['average']:.1f}, min={stats['min']}, max={stats['max']}")
            
            # Serving advantage
            serving_data = self.breakdown_data.get("serving_advantage", {})
            if serving_data:
                lines.append("\nServing Advantage:")
                lines.append(f"  - {team_a_name} when serving: {serving_data['team_a_serve_win_rate']:.1f}% ({serving_data['team_a_serves']} serves)")
                lines.append(f"  - {team_b_name} when serving: {serving_data['team_b_serve_win_rate']:.1f}% ({serving_data['team_b_serves']} serves)")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output"""
        result = {
            'total_points': self.total_points,
            'team_a_wins': self.team_a_wins,
            'team_b_wins': self.team_b_wins,
            'team_a_win_rate': self.team_a_win_rate,
            'team_b_win_rate': self.team_b_win_rate,
            'point_type_breakdown': self.point_type_breakdown,
            'point_type_percentages': self.point_type_percentages,
            'average_duration': self.average_duration
        }
        
        # Include breakdown data if available
        if hasattr(self, 'breakdown_data') and self.breakdown_data:
            result['breakdown_data'] = self.breakdown_data
        
        return result


@dataclass
class SensitivityDataPoint:
    """Single data point in sensitivity analysis"""
    parameter_value: float
    win_rate: float
    change_from_base: float


@dataclass
class SensitivityResults:
    """Sensitivity analysis results"""
    parameter_name: str
    base_win_rate: float
    data_points: List[SensitivityDataPoint]
    impact_factor: str  # "LOW", "MEDIUM", "HIGH"
    
    def to_text(self, team_name: str = "Team") -> str:
        """Format as text output"""
        lines = [
            f"Sensitivity Analysis: {self.parameter_name}",
            f"Base win rate: {self.base_win_rate:.2f}%",
            "",
            "Parameter Value | Win Rate | Change"
        ]
        
        for point in self.data_points:
            change_str = f"{point.change_from_base:+.2f}%" if point.change_from_base != 0 else " 0.00% (base)"
            lines.append(f"{point.parameter_value:.2f}           | {point.win_rate:.2f}%   | {change_str}")
        
        # Calculate total range
        min_change = min(p.change_from_base for p in self.data_points)
        max_change = max(p.change_from_base for p in self.data_points)
        total_range = max_change - min_change
        
        lines.append(f"\nImpact Factor: {self.impact_factor} ({total_range:.2f}% range)")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output"""
        return {
            'parameter_name': self.parameter_name,
            'base_win_rate': self.base_win_rate,
            'data_points': [
                {
                    'parameter_value': p.parameter_value,
                    'win_rate': p.win_rate,
                    'change_from_base': p.change_from_base
                }
                for p in self.data_points
            ],
            'impact_factor': self.impact_factor
        }