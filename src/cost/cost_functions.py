"""
Cost Functions Module for Smart Camera Control System

This module defines tunable cost weights and calculation logic for camera parameter
adjustments, enabling intelligent prioritization of parameter changes based on
their impact on image quality and system performance.
"""

import json
from typing import Dict, List, Tuple, Union
from dataclasses import dataclass


@dataclass
class ParameterCost:
    """Represents the cost and constraints for a camera parameter."""
    name: str
    base_cost: float
    max_cost: float
    min_cost: float
    preferred_direction: str  # 'increase', 'decrease', or 'either'


class CostFunctionCalculator:
    """
    Calculates the cost of adjusting camera parameters based on tunable weights
    and current parameter state.
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize the cost calculator with configuration.
        
        Args:
            config_file: Path to configuration file containing cost weights
        """
        if config_file is None:
            import os
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
        
        self.parameter_costs = self._load_parameter_costs(config_file)
        self.hysteresis_config = self._load_hysteresis_config(config_file)
        
    def _load_parameter_costs(self, config_file: str) -> Dict[str, ParameterCost]:
        """Load parameter cost configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                cost_weights = config.get('cost_weights', {})
        except FileNotFoundError:
            # Use default cost weights if config file doesn't exist
            cost_weights = self._get_default_cost_weights()
            
        parameter_costs = {}
        for param_name, weights in cost_weights.items():
            parameter_costs[param_name] = ParameterCost(
                name=param_name,
                base_cost=weights.get('base_cost', 1.0),
                max_cost=weights.get('max_cost', 10.0),
                min_cost=weights.get('min_cost', 0.1),
                preferred_direction=weights.get('preferred_direction', 'either')
            )
        return parameter_costs
    
    def _load_hysteresis_config(self, config_file: str) -> Dict[str, float]:
        """Load hysteresis configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('hysteresis', {})
        except FileNotFoundError:
            return self._get_default_hysteresis_config()
    
    def _get_default_cost_weights(self) -> Dict[str, Dict[str, Union[float, str]]]:
        """Get default cost weights for camera parameters."""
        return {
            "ExposureIris": {
                "base_cost": 0.5,  # Low cost - preferred for brightness adjustments
                "max_cost": 2.0,
                "min_cost": 0.2,
                "preferred_direction": "increase"
            },
            "ExposureExposureTime": {
                "base_cost": 1.5,  # Medium cost - affects motion blur
                "max_cost": 5.0,
                "min_cost": 0.5,
                "preferred_direction": "decrease"  # Faster shutter preferred
            },
            "ExposureGain": {
                "base_cost": 3.0,  # High cost - introduces noise
                "max_cost": 10.0,
                "min_cost": 1.0,
                "preferred_direction": "decrease"
            },
            "DigitalBrightLevel": {
                "base_cost": 2.0,  # Medium-high cost - digital processing
                "max_cost": 6.0,
                "min_cost": 0.5,
                "preferred_direction": "either"
            },
            "ColorSaturation": {
                "base_cost": 0.8,  # Low cost for color adjustments
                "max_cost": 3.0,
                "min_cost": 0.3,
                "preferred_direction": "either"
            }
        }
    
    def _get_default_hysteresis_config(self) -> Dict[str, float]:
        """Get default hysteresis configuration."""
        return {
            "dead_band_percentage": 0.05,  # 5% dead band
            "inner_threshold_percentage": 0.02,  # 2% inner threshold
            "outer_threshold_percentage": 0.08   # 8% outer threshold
        }
    
    def calculate_adjustment_cost(
        self, 
        parameter: str, 
        current_value: Union[int, str], 
        target_value: Union[int, str],
        param_range: List[Union[int, str]],
        feature_delta: float
    ) -> float:
        """
        Calculate the cost of adjusting a specific parameter.
        
        Args:
            parameter: Name of the camera parameter
            current_value: Current parameter value
            target_value: Desired parameter value
            param_range: Available parameter values
            feature_delta: How far the feature is from acceptable range
            
        Returns:
            Calculated cost for this adjustment (lower is better)
        """
        if parameter not in self.parameter_costs:
            return 10.0  # High cost for unknown parameters
            
        param_cost = self.parameter_costs[parameter]
        
        # Base cost from configuration
        cost = param_cost.base_cost
        
        # Scale cost based on how far we need to adjust
        try:
            current_idx = param_range.index(str(current_value))
            target_idx = param_range.index(str(target_value))
            adjustment_distance = abs(target_idx - current_idx)
            
            # Increase cost for larger adjustments
            if adjustment_distance > 0:
                cost *= (1 + adjustment_distance * 0.2)
                
        except (ValueError, IndexError):
            # If we can't find indices, use base cost
            pass
        
        # Apply directional preference penalty
        if param_cost.preferred_direction != 'either':
            try:
                current_idx = param_range.index(str(current_value))
                target_idx = param_range.index(str(target_value))
                
                if param_cost.preferred_direction == 'increase' and target_idx < current_idx:
                    cost *= 1.5  # Penalty for going against preference
                elif param_cost.preferred_direction == 'decrease' and target_idx > current_idx:
                    cost *= 1.5
                    
            except (ValueError, IndexError):
                pass
        
        # Scale cost based on feature delta magnitude
        # Larger deltas should prefer more effective parameters
        if abs(feature_delta) > 0.1:  # Large deviation
            cost *= 0.8  # Slightly favor more effective adjustments
        elif abs(feature_delta) < 0.02:  # Small deviation
            cost *= 1.2  # Slightly penalize adjustments for small deviations
            
        return cost
    
    def get_hysteresis_bounds(
        self, 
        feature_name: str, 
        acceptable_range: Tuple[float, float]
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Calculate hysteresis bounds for a feature.
        
        Args:
            feature_name: Name of the image feature
            acceptable_range: Original acceptable range (min, max)
            
        Returns:
            Tuple of (inner_bounds, outer_bounds) where each is (min, max)
        """
        min_val, max_val = acceptable_range
        range_size = max_val - min_val
        
        # Get hysteresis percentages
        dead_band_pct = self.hysteresis_config.get('dead_band_percentage', 0.05)
        inner_pct = self.hysteresis_config.get('inner_threshold_percentage', 0.02)
        outer_pct = self.hysteresis_config.get('outer_threshold_percentage', 0.08)
        
        # Calculate bounds
        inner_expansion = range_size * inner_pct
        outer_expansion = range_size * outer_pct
        
        inner_bounds = (min_val + inner_expansion, max_val - inner_expansion)
        outer_bounds = (min_val - outer_expansion, max_val + outer_expansion)
        
        return inner_bounds, outer_bounds
    
    def should_adjust_feature(
        self, 
        feature_name: str, 
        feature_value: float, 
        acceptable_range: Tuple[float, float]
    ) -> Tuple[bool, str]:
        """
        Determine if a feature should be adjusted based on hysteresis.
        
        Args:
            feature_name: Name of the image feature
            feature_value: Current feature value
            acceptable_range: Original acceptable range
            
        Returns:
            Tuple of (should_adjust, reason) where reason explains the decision
        """
        inner_bounds, outer_bounds = self.get_hysteresis_bounds(feature_name, acceptable_range)
        
        min_val, max_val = acceptable_range
        inner_min, inner_max = inner_bounds
        outer_min, outer_max = outer_bounds
        
        # Check if value is outside outer bounds (definitely needs adjustment)
        if feature_value < outer_min:
            return True, f"Value {feature_value:.3f} below outer threshold {outer_min:.3f}"
        elif feature_value > outer_max:
            return True, f"Value {feature_value:.3f} above outer threshold {outer_max:.3f}"
        
        # Check if value is within inner bounds (definitely doesn't need adjustment)
        elif inner_min <= feature_value <= inner_max:
            return False, f"Value {feature_value:.3f} within inner bounds [{inner_min:.3f}, {inner_max:.3f}]"
        
        # Value is in hysteresis zone - don't adjust to prevent oscillation
        else:
            return False, f"Value {feature_value:.3f} in hysteresis zone, preventing oscillation"
    
    def find_best_adjustment(
        self,
        feature_name: str,
        feature_value: float,
        acceptable_range: Tuple[float, float],
        current_params: Dict[str, Union[int, str]],
        param_ranges: Dict[str, List[Union[int, str]]],
        adjustment_rules: Dict[str, List[str]]
    ) -> Tuple[str, Union[int, str], float]:
        """
        Find the best parameter adjustment for a given feature.
        
        Args:
            feature_name: Name of the image feature to adjust
            feature_value: Current feature value
            acceptable_range: Acceptable range for the feature
            current_params: Current camera parameters
            param_ranges: Available parameter ranges
            adjustment_rules: Rules mapping features to adjustable parameters
            
        Returns:
            Tuple of (best_parameter, new_value, cost)
        """
        if feature_name not in adjustment_rules:
            return None, None, float('inf')
        
        # Calculate feature delta
        min_val, max_val = acceptable_range
        if feature_value < min_val:
            feature_delta = feature_value - min_val  # Negative - need to increase
            increase_needed = True
        elif feature_value > max_val:
            feature_delta = feature_value - max_val  # Positive - need to decrease
            increase_needed = False
        else:
            return None, None, float('inf')  # No adjustment needed
        
        best_param = None
        best_value = None
        best_cost = float('inf')
        
        # Evaluate each possible parameter adjustment
        for param_name in adjustment_rules[feature_name]:
            if param_name not in param_ranges or param_name not in current_params:
                continue
                
            current_value = current_params[param_name]
            param_range = param_ranges[param_name]
            
            # Find next value in appropriate direction
            try:
                current_idx = param_range.index(str(current_value))
                
                if increase_needed and current_idx < len(param_range) - 1:
                    next_value = param_range[current_idx + 1]
                elif not increase_needed and current_idx > 0:
                    next_value = param_range[current_idx - 1]
                else:
                    continue  # Can't adjust this parameter further
                    
                # Calculate cost for this adjustment
                cost = self.calculate_adjustment_cost(
                    param_name, current_value, next_value, param_range, feature_delta
                )
                
                if cost < best_cost:
                    best_cost = cost
                    best_param = param_name
                    best_value = next_value
                    
            except (ValueError, IndexError):
                continue
        
        return best_param, best_value, best_cost
