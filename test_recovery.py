#!/usr/bin/env python3
"""
Camera Recovery Test Script

This script tests the camera control system's ability to recover from
color disturbances by simulating various scenarios.
"""

import asyncio
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.utils import CameraSettingsAdjuster, acceptable_ranges
from cost.cost_functions import CostFunctionCalculator

def test_recovery_scenarios():
    """Test various recovery scenarios."""
    
    print("=" * 60)
    print("CAMERA RECOVERY TEST")
    print("=" * 60)
    
    # Initialize components
    adjuster = CameraSettingsAdjuster(acceptable_ranges)
    cost_calc = CostFunctionCalculator()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Normal Range",
            "features": {"normalized_brightness": 0.55, "normalized_saturation": 0.5},
            "expected": "No adjustment"
        },
        {
            "name": "Slightly Low Brightness",
            "features": {"normalized_brightness": 0.25, "normalized_saturation": 0.5},
            "expected": "Small adjustment"
        },
        {
            "name": "Very Low Brightness (Recovery Test)",
            "features": {"normalized_brightness": 0.1, "normalized_saturation": 0.5},
            "expected": "Aggressive adjustment"
        },
        {
            "name": "Very High Brightness (Recovery Test)",
            "features": {"normalized_brightness": 0.9, "normalized_saturation": 0.5},
            "expected": "Aggressive adjustment"
        },
        {
            "name": "Very Low Saturation (Recovery Test)",
            "features": {"normalized_brightness": 0.55, "normalized_saturation": 0.1},
            "expected": "Aggressive adjustment"
        },
        {
            "name": "Very High Saturation (Recovery Test)",
            "features": {"normalized_brightness": 0.55, "normalized_saturation": 0.9},
            "expected": "Aggressive adjustment"
        },
        {
            "name": "Both Out of Range (Recovery Test)",
            "features": {"normalized_brightness": 0.1, "normalized_saturation": 0.1},
            "expected": "Multiple aggressive adjustments"
        }
    ]
    
    # Sample camera parameters
    sample_config = {
        "ExposureIris": "11",
        "ExposureGain": "3",
        "ExposureExposureTime": "10",
        "DigitalBrightLevel": "0",
        "ColorSaturation": "7"
    }
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        print(f"Image features: {scenario['features']}")
        print(f"Expected: {scenario['expected']}")
        
        # Test adjustment logic
        adjustments = adjuster.adjust_camera_settings(sample_config, scenario['features'])
        
        if adjustments:
            print("✓ Adjustments suggested:")
            for param, value in adjustments.items():
                current = sample_config.get(param, 'N/A')
                print(f"  {param}: {current} -> {value}")
                
                # Show cost analysis
                param_range = adjuster.cam_params_range.get(param, [])
                if param_range:
                    try:
                        current_idx = param_range.index(str(current))
                        target_idx = param_range.index(str(value))
                        feature_delta = scenario['features']['normalized_brightness'] - 0.55  # Midpoint
                        cost = cost_calc.calculate_adjustment_cost(
                            param, current, value, param_range, feature_delta
                        )
                        print(f"    Cost: {cost:.2f}")
                    except (ValueError, IndexError):
                        print(f"    Cost: Unable to calculate")
        else:
            print("✓ No adjustments needed")
        
        print(f"Result: {'✓ PASS' if adjustments or scenario['expected'] == 'No adjustment' else '✗ FAIL'}")
    
    print(f"\n{'='*60}")
    print("RECOVERY TEST SUMMARY:")
    print("• Expanded acceptable ranges for better recovery")
    print("• Reduced hysteresis for more responsive adjustments")
    print("• Aggressive multi-step adjustments for large deviations")
    print("• Enhanced cost function for better parameter selection")
    print("• Recovery mode enabled for fast correction")
    print(f"{'='*60}")

def test_hysteresis_bounds():
    """Test hysteresis bounds calculation."""
    
    print("\n" + "=" * 60)
    print("HYSTERESIS BOUNDS TEST")
    print("=" * 60)
    
    cost_calc = CostFunctionCalculator()
    
    # Test brightness range
    brightness_range = (0.3, 0.8)
    inner_bounds, outer_bounds = cost_calc.get_hysteresis_bounds('normalized_brightness', brightness_range)
    
    print(f"Brightness Range: {brightness_range}")
    print(f"Inner Bounds: {inner_bounds}")
    print(f"Outer Bounds: {outer_bounds}")
    
    # Test various values
    test_values = [0.1, 0.25, 0.35, 0.55, 0.75, 0.85, 0.95]
    
    for value in test_values:
        should_adjust, reason = cost_calc.should_adjust_feature('normalized_brightness', value, brightness_range)
        print(f"Value {value:.2f}: {'ADJUST' if should_adjust else 'NO ADJUST'} - {reason}")

if __name__ == "__main__":
    test_recovery_scenarios()
    test_hysteresis_bounds()
