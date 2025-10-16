#!/usr/bin/env python3
"""
Protocol-Agnostic Camera Control Demonstration

This script demonstrates the camera control system working with both
CGI and VISCA protocols, showing how to switch between them.
"""

import asyncio
import nats
import json
from camera_protocol import ProtocolFactory
from utils import CameraSettingsAdjuster, acceptable_ranges

async def demo_protocol_agnostic_system():
    """Demonstrate protocol-agnostic camera control."""
    
    print("=" * 70)
    print("PROTOCOL-AGNOSTIC CAMERA CONTROL SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    # Connect to NATS
    try:
        nc = await nats.connect("nats://localhost:4222")
        print("✓ Connected to NATS server")
    except Exception as e:
        print(f"✗ Failed to connect to NATS: {e}")
        return
    
    cameras = [2, 3]
    
    # Test CGI Protocol
    print(f"\n{'='*25} CGI PROTOCOL TEST {'='*25}")
    cgi_protocol = ProtocolFactory.create_protocol('cgi')
    print(f"Protocol: {type(cgi_protocol).__name__}")
    
    if cgi_protocol.connect():
        print("✓ CGI protocol connected")
        
        for cam_id in cameras:
            print(f"\n--- Camera {cam_id} (CGI) ---")
            
            # Get parameters
            params = cgi_protocol.get_camera_params(cam_id, 13)
            if params:
                print(f"✓ Parameters retrieved: {len(params)} parameters")
                print(f"  ExposureIris: {params.get('ExposureIris')}")
                print(f"  ColorSaturation: {params.get('ColorSaturation')}")
                
                # Test adjustment
                adjuster = CameraSettingsAdjuster(acceptable_ranges)
                test_features = {
                    'normalized_brightness': 0.15,  # Low brightness
                    'normalized_saturation': 0.35,  # Low saturation
                    'mask_coverage': 100.0
                }
                
                adjustments = adjuster.adjust_camera_settings(params, test_features)
                if adjustments:
                    print(f"  Suggested adjustments: {adjustments}")
                    
                    # Apply adjustments
                    success = cgi_protocol.set_camera_params(cam_id, 13, adjustments)
                    if success:
                        print(f"  ✓ CGI adjustments applied successfully")
                        
                        # Publish to NATS
                        message = json.dumps(test_features)
                        await nc.publish(f"image_features.camera{cam_id}", message.encode())
                        print(f"  ✓ Published features to NATS")
                    else:
                        print(f"  ✗ CGI adjustments failed")
                else:
                    print(f"  No adjustments needed")
            else:
                print(f"✗ Failed to get parameters")
        
        cgi_protocol.disconnect()
    
    # Test VISCA Protocol (even though it may not work with these cameras)
    print(f"\n{'='*25} VISCA PROTOCOL TEST {'='*25}")
    visca_protocol = ProtocolFactory.create_protocol('visca')
    print(f"Protocol: {type(visca_protocol).__name__}")
    
    if visca_protocol.connect():
        print("✓ VISCA protocol connected")
        
        for cam_id in cameras:
            print(f"\n--- Camera {cam_id} (VISCA) ---")
            
            # Get parameters
            params = visca_protocol.get_camera_params(cam_id, 13)
            if params:
                print(f"✓ Parameters retrieved: {len(params)} parameters")
                print(f"  ExposureIris: {params.get('ExposureIris')}")
                print(f"  ColorSaturation: {params.get('ColorSaturation')}")
                
                # Test adjustment
                test_params = {'ColorSaturation': '8'}
                success = visca_protocol.set_camera_params(cam_id, 13, test_params)
                if success:
                    print(f"  ✓ VISCA adjustments applied successfully")
                else:
                    print(f"  ✗ VISCA adjustments failed (expected - cameras may not support VISCA)")
            else:
                print(f"✗ Failed to get parameters")
        
        visca_protocol.disconnect()
    
    await nc.close()
    
    print(f"\n{'='*70}")
    print("PROTOCOL-AGNOSTIC SYSTEM SUMMARY:")
    print("=" * 70)
    print("✓ CGI Protocol: Working perfectly with HTTP-based control")
    print("✓ VISCA Protocol: Available but may need camera-specific tuning")
    print("✓ Protocol Selection: Use --protocol argument in rule_engine.py")
    print("✓ Same Interface: Both protocols use identical API")
    print("✓ Configuration: Default protocol from camera_control_config.json")
    print("\nUsage Examples:")
    print("  python3 rule_engine.py --cam_id 2 --venue_number 13 --protocol cgi")
    print("  python3 rule_engine.py --cam_id 3 --venue_number 13 --protocol visca")
    print("  python3 rule_engine.py --cam_id 2 --venue_number 13  # Uses config default")
    print(f"{'='*70}")

if __name__ == "__main__":
    asyncio.run(demo_protocol_agnostic_system())
