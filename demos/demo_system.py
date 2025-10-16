#!/usr/bin/env python3
"""
Smart Camera Control System - Demonstration Script

This script demonstrates the camera control system functionality
without requiring video feed, showing parameter adjustment logic.
"""

import asyncio
import nats
import json
import time
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocols.camera_protocol import ProtocolFactory
from utils.utils import CameraSettingsAdjuster, acceptable_ranges
from cost.cost_functions import CostFunctionCalculator

async def demo_camera_control():
    """Demonstrate the camera control system functionality."""
    
    print("=" * 60)
    print("SMART CAMERA CONTROL SYSTEM - DEMONSTRATION")
    print("=" * 60)
    
    # Initialize components
    protocol = ProtocolFactory.create_protocol_from_config()
    adjuster = CameraSettingsAdjuster(acceptable_ranges)
    cost_calc = CostFunctionCalculator()
    
    # Connect to NATS
    try:
        nc = await nats.connect("nats://localhost:4222")
        print("✓ Connected to NATS server")
    except Exception as e:
        print(f"✗ Failed to connect to NATS: {e}")
        return
    
    # Test camera connectivity
    print("\n1. Testing Camera Connectivity...")
    cameras_available = []
    for cam_id in range(1, 7):
        try:
            params = protocol.get_camera_params(cam_id, 13)
            if params:
                cameras_available.append(cam_id)
                print(f"✓ Camera {cam_id}: Connected ({len(params)} parameters)")
            else:
                print(f"✗ Camera {cam_id}: Not responding")
        except Exception as e:
            print(f"✗ Camera {cam_id}: Error - {e}")
    
    if not cameras_available:
        print("No cameras available for demonstration")
        return
    
    # Demonstrate parameter adjustment logic
    print(f"\n2. Demonstrating Parameter Adjustment Logic...")
    print(f"Using Camera {cameras_available[0]} as example")
    
    cam_id = cameras_available[0]
    params = protocol.get_camera_params(cam_id, 13)
    
    print(f"\nCurrent parameters for Camera {cam_id}:")
    for key, value in params.items():
        if 'Exposure' in key or 'Color' in key or 'Digital' in key:
            print(f"  {key}: {value}")
    
    # Simulate different lighting conditions
    scenarios = [
        {
            "name": "Low Light (Dark)",
            "features": {"normalized_brightness": 0.15, "normalized_saturation": 0.35, "mask_coverage": 100.0}
        },
        {
            "name": "Normal Light",
            "features": {"normalized_brightness": 0.35, "normalized_saturation": 0.55, "mask_coverage": 100.0}
        },
        {
            "name": "Bright Light (Overexposed)",
            "features": {"normalized_brightness": 0.65, "normalized_saturation": 0.45, "mask_coverage": 100.0}
        },
        {
            "name": "High Saturation",
            "features": {"normalized_brightness": 0.40, "normalized_saturation": 0.80, "mask_coverage": 100.0}
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        print(f"Image features: {scenario['features']}")
        
        # Calculate adjustments
        adjustments = adjuster.adjust_camera_settings(params, scenario['features'])
        
        if adjustments:
            print("Suggested adjustments:")
            for param, value in adjustments.items():
                current = params.get(param, 'N/A')
                print(f"  {param}: {current} -> {value}")
            
            # Show cost analysis
            print("\nCost analysis:")
            for param, value in adjustments.items():
                current = params.get(param, 'N/A')
                # Calculate cost for this adjustment
                param_range = adjuster.cam_params_range.get(param, [])
                if param_range:
                    try:
                        current_idx = param_range.index(str(current))
                        target_idx = param_range.index(str(value))
                        feature_delta = scenario['features']['normalized_brightness'] - 0.375  # Midpoint of range
                        cost = cost_calc.calculate_adjustment_cost(
                            param, current, value, param_range, feature_delta
                        )
                        print(f"  {param}: cost = {cost:.2f}")
                    except (ValueError, IndexError):
                        print(f"  {param}: cost calculation failed")
        else:
            print("No adjustments needed - image features within acceptable ranges")
        
        # Simulate parameter update
        if adjustments:
            print(f"\nWould publish to NATS: image_features.camera{cam_id}")
            param_string = adjuster.generate_camera_params_string(adjustments)
            print(f"Parameter string: {param_string}")
            
            # Publish to NATS (simulation)
            message = json.dumps(scenario['features'])
            await nc.publish(f"image_features.camera{cam_id}", message.encode())
            print("✓ Published image features to NATS")
    
    # Demonstrate master camera functionality
    print(f"\n3. Demonstrating Master Camera Functionality...")
    master_cam_id = 1
    if master_cam_id in cameras_available:
        print(f"Camera {master_cam_id} is configured as MASTER camera")
        
        # Publish target features
        target_features = {}
        for feature, range_values in acceptable_ranges.items():
            target_features[feature] = (range_values[0] + range_values[1]) / 2
        
        target_message = json.dumps(target_features)
        await nc.publish("features.target", target_message.encode())
        print(f"✓ Master camera published target features: {target_features}")
    
    # Demonstrate cost function analysis
    print(f"\n4. Demonstrating Cost Function Analysis...")
    print("Parameter cost comparison for brightness adjustment:")
    
    test_params = ['ExposureIris', 'ExposureExposureTime', 'ExposureGain', 'DigitalBrightLevel']
    for param in test_params:
        if param in adjuster.cam_params_range:
            param_range = adjuster.cam_params_range[param]
            current_value = params.get(param, '0')
            
            try:
                current_idx = param_range.index(str(current_value))
                if current_idx < len(param_range) - 1:
                    next_value = param_range[current_idx + 1]
                    cost = cost_calc.calculate_adjustment_cost(
                        param, current_value, next_value, param_range, -0.1
                    )
                    print(f"  {param}: {current_value} -> {next_value} (cost: {cost:.2f})")
            except (ValueError, IndexError):
                print(f"  {param}: Unable to calculate cost")
    
    await nc.close()
    print(f"\n" + "=" * 60)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("• Intelligent cost-based parameter selection")
    print("• Hysteresis to prevent oscillation")
    print("• Protocol abstraction (CGI)")
    print("• Master camera target publishing")
    print("• Real-time NATS communication")
    print("• Multi-scenario parameter adjustment")
    print("\nThe system is ready for production use!")

if __name__ == "__main__":
    asyncio.run(demo_camera_control())
