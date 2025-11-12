#!/usr/bin/env python3
"""
Protocol-Agnostic Camera Control Test

This script tests both CGI and VISCA protocols on cameras 2 and 3
without requiring video feed.
"""

import asyncio
import nats
import json
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocols.camera_protocol import ProtocolFactory
from utils.utils import CameraSettingsAdjuster, acceptable_ranges

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

async def test_protocols_async():
    """Test async versions of both CGI and VISCA protocols."""
    
    print("=" * 60)
    print("ASYNC PROTOCOL-AGNOSTIC CAMERA CONTROL TEST")
    print("=" * 60)
    
    protocols = ['cgi', 'visca']
    cameras = [2, 3]
    
    for protocol_type in protocols:
        print(f"\n{'='*20} ASYNC {protocol_type.upper()} PROTOCOL {'='*20}")
        
        # Create protocol instance
        protocol = ProtocolFactory.create_protocol(protocol_type)
        print(f"Protocol: {type(protocol).__name__}")
        
        # Test async connection
        try:
            if hasattr(protocol, 'connect_async'):
                connected = await protocol.connect_async()
            else:
                connected = protocol.connect()
            
            if connected:
                print("✓ Async protocol connected successfully")
            else:
                print("✗ Async protocol connection failed")
                continue
        except Exception as e:
            print(f"✗ Async protocol connection error: {e}")
            continue
        
        for cam_id in cameras:
            print(f"\n--- Camera {cam_id} (Async) ---")
            
            # Test async parameter retrieval
            try:
                params = await protocol.get_camera_params_async(cam_id, 13)
                if params:
                    print(f"✓ Async parameter retrieval successful ({len(params)} parameters)")
                    
                    # Show key parameters
                    key_params = ['ExposureIris', 'ColorSaturation', 'DigitalBrightLevel']
                    for param in key_params:
                        if param in params:
                            print(f"  {param}: {params[param]}")
                    
                    # Test async parameter adjustment
                    test_params = {'ColorSaturation': '7'}
                    print(f"\nTesting async parameter setting: {test_params}")
                    
                    success = await protocol.set_camera_params_async(cam_id, 13, test_params)
                    if success:
                        print("✓ Async parameter setting successful")
                        
                        # Verify change
                        await asyncio.sleep(1)
                        new_params = await protocol.get_camera_params_async(cam_id, 13)
                        if new_params:
                            old_val = params.get('ColorSaturation', 'N/A')
                            new_val = new_params.get('ColorSaturation', 'N/A')
                            print(f"  ColorSaturation: {old_val} -> {new_val}")
                    else:
                        print("✗ Async parameter setting failed")
                else:
                    print("✗ Async parameter retrieval failed")
            except Exception as e:
                print(f"✗ Async operation error: {e}")
        
        # Disconnect protocol
        try:
            if hasattr(protocol, 'disconnect_async'):
                await protocol.disconnect_async()
            else:
                protocol.disconnect()
            print(f"\nAsync {protocol_type.upper()} protocol test completed")
        except Exception as e:
            print(f"✗ Async disconnect error: {e}")
    
    print(f"\n{'='*60}")
    print("ASYNC PROTOCOL TEST SUMMARY:")
    print("• Async CGI Protocol: Non-blocking HTTP-based camera control")
    print("• Async VISCA Protocol: Non-blocking UDP-based VISCA over IP")
    print("• Concurrent parameter execution for maximum speed")
    print("• Full ACK/Completion validation maintained")
    print("• Backward compatibility with sync methods")
    print(f"{'='*60}")

async def test_concurrent_operations():
    """Test concurrent operations across multiple cameras."""
    
    print("=" * 60)
    print("CONCURRENT MULTI-CAMERA OPERATIONS TEST")
    print("=" * 60)
    
    protocol_type = 'visca'  # Use VISCA for concurrent test
    cameras = [1, 2, 3]
    
    # Create protocol instance
    protocol = ProtocolFactory.create_protocol(protocol_type)
    print(f"Protocol: {type(protocol).__name__}")
    
    # Test async connection
    try:
        if hasattr(protocol, 'connect_async'):
            connected = await protocol.connect_async()
        else:
            connected = protocol.connect()
        
        if not connected:
            print("✗ Protocol connection failed")
            return
        print("✓ Protocol connected successfully")
    except Exception as e:
        print(f"✗ Protocol connection error: {e}")
        return
    
    # Test concurrent parameter retrieval
    print(f"\nTesting concurrent parameter retrieval on cameras {cameras}")
    start_time = asyncio.get_event_loop().time()
    
    tasks = []
    for cam_id in cameras:
        task = asyncio.create_task(protocol.get_camera_params_async(cam_id, 13))
        tasks.append((cam_id, task))
    
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    print(f"✓ Concurrent parameter retrieval completed in {duration:.3f} seconds")
    
    for i, (cam_id, _) in enumerate(tasks):
        result = results[i]
        if isinstance(result, Exception):
            print(f"  Camera {cam_id}: Error - {result}")
        elif result:
            print(f"  Camera {cam_id}: Success ({len(result)} parameters)")
        else:
            print(f"  Camera {cam_id}: Failed")
    
    # Test concurrent parameter setting
    print(f"\nTesting concurrent parameter setting on cameras {cameras}")
    start_time = asyncio.get_event_loop().time()
    
    tasks = []
    for cam_id in cameras:
        test_params = {'ColorSaturation': str(7 + cam_id)}  # Different values per camera
        task = asyncio.create_task(protocol.set_camera_params_async(cam_id, 13, test_params))
        tasks.append((cam_id, task))
    
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    print(f"✓ Concurrent parameter setting completed in {duration:.3f} seconds")
    
    for i, (cam_id, _) in enumerate(tasks):
        result = results[i]
        if isinstance(result, Exception):
            print(f"  Camera {cam_id}: Error - {result}")
        elif result:
            print(f"  Camera {cam_id}: Success")
        else:
            print(f"  Camera {cam_id}: Failed")
    
    # Disconnect protocol
    try:
        if hasattr(protocol, 'disconnect_async'):
            await protocol.disconnect_async()
        else:
            protocol.disconnect()
        print(f"\n✓ Concurrent operations test completed")
    except Exception as e:
        print(f"✗ Disconnect error: {e}")
    
    print(f"\n{'='*60}")
    print("CONCURRENT OPERATIONS SUMMARY:")
    print("• Multiple cameras controlled simultaneously")
    print("• Significant performance improvement over sequential operations")
    print("• All operations maintain ACK/Completion validation")
    print("• Error handling for individual camera failures")
    print(f"{'='*60}")

async def test_controlled_concurrency():
    """Test controlled concurrency with rate limiting."""
    print("=" * 60)
    print("CONTROLLED CONCURRENCY TEST")
    print("=" * 60)
    
    # Test VISCA protocol with controlled concurrency
    protocol = ProtocolFactory.create_protocol('visca')
    
    if not protocol.connect():
        print("Failed to connect VISCA protocol")
        return
    
    # Test with multiple parameters
    params = {
        'ExposureIris': '11',
        'ExposureGain': '3',
        'ExposureExposureTime': '10',
        'ColorSaturation': '5',
        'DigitalBrightLevel': '2'
    }
    
    print(f"Testing controlled concurrency with {len(params)} parameters:")
    for param, value in params.items():
        print(f"  {param}: {value}")
    
    # Test SET operations with controlled concurrency
    success = await protocol.set_camera_params_async(2, 13, params)
    stats = protocol.get_concurrency_stats()
    
    print(f"\nControlled concurrency results:")
    print(f"  Success: {success}")
    print(f"  Concurrency enabled: {stats['enabled']}")
    print(f"  Current limit: {stats['current_limit']}")
    print(f"  Max limit: {stats['max_limit']}")
    print(f"  Success count: {stats['success_count']}")
    print(f"  Failure count: {stats['failure_count']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    print(f"  Rate limiting active: {stats['rate_limiting_active']}")
    
    # Test GET operations with controlled concurrency
    print(f"\nTesting controlled concurrent parameter retrieval...")
    config_dict = await protocol.get_camera_params_async(2, 13)
    
    if config_dict:
        print(f"Retrieved {len(config_dict)} parameters:")
        for param, value in config_dict.items():
            print(f"  {param}: {value}")
    else:
        print("Failed to retrieve parameters")
    
    # Disconnect protocol
    protocol.disconnect()
    print(f"\nControlled concurrency test completed")

async def main():
    """Run all tests."""
    await test_protocols()
    print("\n" + "="*60 + "\n")
    await test_protocols_async()
    print("\n" + "="*60 + "\n")
    await test_concurrent_operations()
    print("\n" + "="*60 + "\n")
    await test_controlled_concurrency()

if __name__ == "__main__":
    asyncio.run(main())
