#!/usr/bin/env python3
"""
Protocol-Agnostic Camera Control Test

This script tests both CGI and VISCA protocols on cameras 2 and 3
without requiring video feed.
"""

import asyncio
import nats
import json
from camera_protocol import ProtocolFactory
from utils import CameraSettingsAdjuster, acceptable_ranges

async def test_protocols():
    """Test both CGI and VISCA protocols."""
    
    print("=" * 60)
    print("PROTOCOL-AGNOSTIC CAMERA CONTROL TEST")
    print("=" * 60)
    
    protocols = ['cgi', 'visca']
    cameras = [2, 3]
    
    for protocol_type in protocols:
        print(f"\n{'='*20} {protocol_type.upper()} PROTOCOL {'='*20}")
        
        # Create protocol instance
        protocol = ProtocolFactory.create_protocol(protocol_type)
        print(f"Protocol: {type(protocol).__name__}")
        
        # Test connection
        if protocol.connect():
            print("✓ Protocol connected successfully")
        else:
            print("✗ Protocol connection failed")
            continue
        
        for cam_id in cameras:
            print(f"\n--- Camera {cam_id} ---")
            
            # Test parameter retrieval
            params = protocol.get_camera_params(cam_id, 13)
            if params:
                print(f"✓ Parameter retrieval successful ({len(params)} parameters)")
                
                # Show key parameters
                key_params = ['ExposureIris', 'ColorSaturation', 'DigitalBrightLevel']
                for param in key_params:
                    if param in params:
                        print(f"  {param}: {params[param]}")
                
                # Test parameter adjustment
                test_params = {'ColorSaturation': '7'}
                print(f"\nTesting parameter setting: {test_params}")
                
                success = protocol.set_camera_params(cam_id, 13, test_params)
                if success:
                    print("✓ Parameter setting successful")
                    
                    # Verify change
                    import time
                    time.sleep(1)
                    new_params = protocol.get_camera_params(cam_id, 13)
                    if new_params:
                        old_val = params.get('ColorSaturation', 'N/A')
                        new_val = new_params.get('ColorSaturation', 'N/A')
                        print(f"  ColorSaturation: {old_val} -> {new_val}")
                else:
                    print("✗ Parameter setting failed")
            else:
                print("✗ Parameter retrieval failed")
        
        # Disconnect protocol
        protocol.disconnect()
        print(f"\n{protocol_type.upper()} protocol test completed")
    
    print(f"\n{'='*60}")
    print("PROTOCOL TEST SUMMARY:")
    print("• CGI Protocol: HTTP-based camera control")
    print("• VISCA Protocol: UDP-based VISCA over IP")
    print("• Both protocols support the same interface")
    print("• Protocol can be selected via --protocol argument")
    print("• Default protocol comes from camera_control_config.json")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_protocols())
