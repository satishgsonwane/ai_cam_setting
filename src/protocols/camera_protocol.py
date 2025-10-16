"""
Camera Protocol Abstraction Layer

This module provides an abstraction layer for camera communication protocols,
supporting both CGI (HTTP) and VISCA (UDP) protocols for camera control.
"""

import json
import socket
import time
import requests
from requests.auth import HTTPDigestAuth
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Tuple
import struct
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector


class CameraProtocolInterface(ABC):
    """Abstract base class for camera communication protocols."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to camera."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Close connection to camera."""
        pass
    
    @abstractmethod
    def get_camera_params(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """Get current camera parameters."""
        pass
    
    @abstractmethod
    def set_camera_params(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """Set camera parameters."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass
    
    @abstractmethod
    async def set_camera_params_async(self, cam_id: int, venue_number: int, 
                                    params_dict: Dict[str, Union[int, str]]) -> bool:
        """Async version of set_camera_params."""
        pass
    
    @abstractmethod
    async def get_camera_params_async(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """Async version of get_camera_params."""
        pass


class CGIProtocol(CameraProtocolInterface):
    """CGI (HTTP) protocol implementation for camera communication."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize CGI protocol.
        
        Args:
            config_file: Path to configuration file
        """
        if config_file is None:
            import os
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
        self.config = self._load_config(config_file)
        self.connected = False
        self.username = self.config.get('network', {}).get('username', 'admin')
        self.password = self.config.get('network', {}).get('password', '123')
        self.timeout = self.config.get('protocol', {}).get('cgi', {}).get('timeout', 2)
        self.max_attempts = self.config.get('protocol', {}).get('cgi', {}).get('max_attempts', 50)
        self.retry_delay = self.config.get('protocol', {}).get('cgi', {}).get('retry_delay', 1.0)
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def connect(self) -> bool:
        """CGI protocol doesn't require persistent connection."""
        self.connected = True
        return True
    
    def disconnect(self) -> bool:
        """CGI protocol doesn't require persistent connection."""
        self.connected = False
        return True
    
    def is_connected(self) -> bool:
        """Check if CGI protocol is ready."""
        return self.connected
    
    def get_camera_params(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """
        Get current camera parameters via CGI inquiry.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            
        Returns:
            Dictionary of camera parameters or None if failed
        """
        venue_number += 54
        url = f'http://192.168.{venue_number}.5{cam_id}/command/inquiry.cgi?inqjs=imaging'
        
        try:
            response = requests.get(
                url, 
                auth=HTTPDigestAuth(self.username, self.password), 
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                print(f"Failed to get camera params. Status code: {response.status_code}")
                return None
            
            # Parse response
            config_dict = {}
            lines = response.text.splitlines()
            for line in lines:
                if 'var ' in line and '=' in line:
                    # Extract parameter name and value
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        param_name = parts[0].replace('var ', '').replace('"', '').strip()
                        param_value = parts[1].replace('"', '').replace(';', '').strip()
                        config_dict[param_name] = param_value
            
            return config_dict
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting camera params: {e}")
            return None
    
    def set_camera_params(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """
        Set camera parameters via CGI command.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            params_dict: Dictionary of parameters to set
            
        Returns:
            True if successful, False otherwise
        """
        if not params_dict:
            return True
        
        venue_number += 54
        params_string = "&".join(f"{k}={v}" for k, v in params_dict.items())
        url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{params_string}'
        
        for attempt in range(self.max_attempts):
            try:
                response = requests.post(
                    url, 
                    auth=HTTPDigestAuth(self.username, self.password), 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    print(f"Successfully set camera parameters on attempt {attempt + 1}")
                    return True
                else:
                    print(f"Failed to set camera parameters on attempt {attempt + 1}. Status code: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Error setting camera params on attempt {attempt + 1}: {e}")
            
            if attempt < self.max_attempts - 1:
                time.sleep(self.retry_delay)
        
        print(f"Failed to set camera parameters after {self.max_attempts} attempts")
        return False
    
    async def get_camera_params_async(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """
        Get current camera parameters via CGI inquiry (async version).
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            
        Returns:
            Dictionary of camera parameters or None if failed
        """
        venue_number += 54
        url = f'http://192.168.{venue_number}.5{cam_id}/command/inquiry.cgi?inqjs=imaging'
        
        timeout = ClientTimeout(total=self.timeout)
        connector = TCPConnector(limit=10, limit_per_host=5)
        
        async with ClientSession(timeout=timeout, connector=connector) as session:
            try:
                async with session.get(url, auth=aiohttp.BasicAuth(self.username, self.password)) as response:
                    if response.status != 200:
                        print(f"Failed to get camera params. Status code: {response.status}")
                        return None
                    
                    text = await response.text()
                    
                    # Parse response
                    config_dict = {}
                    lines = text.splitlines()
                    for line in lines:
                        if 'var ' in line and '=' in line:
                            # Extract parameter name and value
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                param_name = parts[0].replace('var ', '').replace('"', '').strip()
                                param_value = parts[1].replace('"', '').replace(';', '').strip()
                                config_dict[param_name] = param_value
                    
                    return config_dict
                    
            except aiohttp.ClientError as e:
                print(f"Error getting camera params: {e}")
                return None
    
    async def set_camera_params_async(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """
        Set camera parameters via CGI command (async version).
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            params_dict: Dictionary of parameters to set
            
        Returns:
            True if successful, False otherwise
        """
        if not params_dict:
            return True
        
        venue_number += 54
        params_string = "&".join(f"{k}={v}" for k, v in params_dict.items())
        url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{params_string}'
        
        timeout = ClientTimeout(total=self.timeout)
        connector = TCPConnector(limit=10, limit_per_host=5)
        
        async with ClientSession(timeout=timeout, connector=connector) as session:
            for attempt in range(self.max_attempts):
                try:
                    async with session.post(url, auth=aiohttp.BasicAuth(self.username, self.password)) as response:
                        if response.status == 200:
                            print(f"Successfully set camera parameters on attempt {attempt + 1}")
                            return True
                        else:
                            print(f"Failed to set camera parameters on attempt {attempt + 1}. Status code: {response.status}")
                            
                except aiohttp.ClientError as e:
                    print(f"Error setting camera params on attempt {attempt + 1}: {e}")
                
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
            
            print(f"Failed to set camera parameters after {self.max_attempts} attempts")
            return False


class VISCADatagramProtocol(asyncio.DatagramProtocol):
    """Custom datagram protocol for handling VISCA over IP responses."""
    
    def __init__(self, visca_protocol):
        self.visca_protocol = visca_protocol
        self.transport = None
        
    def connection_made(self, transport):
        """Called when connection is established."""
        self.transport = transport
        
    def datagram_received(self, data, addr):
        """Handle incoming VISCA responses."""
        if len(data) > 8:
            visca_payload = data[8:]
            sequence_number = struct.unpack('>I', data[4:8])[0]
            
            # Resolve pending futures
            if sequence_number in self.visca_protocol.command_futures:
                future = self.visca_protocol.command_futures.pop(sequence_number)
                if not future.done():
                    future.set_result(visca_payload)
    
    def error_received(self, exc):
        """Handle protocol errors."""
        print(f"VISCA datagram protocol error: {exc}")
    
    def connection_lost(self, exc):
        """Called when connection is lost."""
        if exc:
            print(f"VISCA datagram protocol connection lost: {exc}")


class VISCAProtocol(CameraProtocolInterface):
    """
    VISCA over IP protocol implementation for Sony SRG-XB25/SRG-XP1 cameras.
    
    Implements proper UDP socket handling, VISCA-IP headers, separate command/inquiry flows,
    and 1V pacing (20ms at 50p) for reliable communication.
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize VISCA protocol.
        
        Args:
            config_file: Path to configuration file
        """
        if config_file is None:
            import os
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
        self.config = self._load_config(config_file)
        self.connected = False
        self.socket = None  # Single UDP socket for send+recv
        self.port = 52381  # Fixed VISCA over IP port
        
        # Timing configuration (4V = 80ms at 50p, add margin)
        self.timeout = 0.15  # 150ms per transaction
        self.v_cycle = 0.02  # 20ms (1V at 50p)
        self.max_attempts = 3  # Reduced attempts
        
        # VISCA addressing (locked for VISCA over IP)
        self.device_addr = 0x01  # Camera address always 1
        self.reply_header = 0x90  # Device addr + 8
        
        # VISCA-IP header management
        self.sequence_number = 0  # Sequence number for VISCA-IP header
        
        # VISCA command mappings
        self.command_map = self._initialize_command_map()
        
        # Async support
        self.command_futures = {}  # Track pending commands by sequence number
        self.datagram_protocol = None
        self.transport = None
    
    def _build_visca_ip_packet(self, visca_payload: bytes) -> bytes:
        """
        Build VISCA-over-IP packet with proper header.
        
        VISCA-IP header format (8 bytes):
        - Byte 0-1: Message type (0x0100 for command, 0x0110 for inquiry, 0x0111 for reply)
        - Byte 2-3: Payload length
        - Byte 4-7: Sequence number
        
        Args:
            visca_payload: The VISCA serial payload (0x81...FF)
            
        Returns:
            Complete VISCA-IP packet (header + payload)
        """
        # Increment sequence number
        self.sequence_number = (self.sequence_number + 1) & 0xFFFFFFFF
        
        # Determine message type based on payload (0x09 = inquiry, 0x01 = command)
        if len(visca_payload) >= 2 and visca_payload[1] == 0x09:
            msg_type = 0x0110  # Inquiry
        else:
            msg_type = 0x0100  # Command
        
        # Build header
        payload_length = len(visca_payload)
        header = struct.pack('>HHI', msg_type, payload_length, self.sequence_number)
        
        return header + visca_payload
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _initialize_command_map(self) -> Dict[str, Dict[str, bytes]]:
        """
        Initialize VISCA command mappings for Sony SRG-XB25/SRG-XP1.
        Uses commands that are verified to work on these cameras.
        """
        return {
            'ExposureGain': {
                'inquiry': b'\x81\x09\x04\x4C\xFF',  # Gain Inquiry (0x4C) - Returns 4-byte
                'set': b'\x81\x01\x04\x4C\x00\x00\x00'  # Gain Direct Set (4-byte value)
            },
            'ExposureExposureTime': {
                'inquiry': b'\x81\x09\x04\x4A\xFF',  # Shutter Inquiry (0x4A) - Returns 4-byte
                'set': b'\x81\x01\x04\x4A\x00\x00\x00'  # Shutter Direct Set (4-byte value)
            },
            'ExposureIris': {
                'inquiry': b'\x81\x09\x04\x4B\xFF',  # Iris Inquiry (0x4B) - Returns 4-byte
                'set': b'\x81\x01\x04\x4B\x00\x00\x00'  # Iris Direct Set (4-byte value)
            },
            'ColorSaturation': {
                'inquiry': b'\x81\x09\x04\x49\xFF',  # Color Gain Inq (0x49) - Returns 4-byte - VERIFIED WORKING
                'set': b'\x81\x01\x04\x49\x00\x00\x00'  # Color Gain Set (4-byte value) - VERIFIED WORKING
            },
            'DigitalBrightLevel': {
                'inquiry': b'\x81\x09\x04\x3E\xFF',  # Exposure Comp Inq (0x3E) - Returns 1-byte
                'set': b'\x81\x01\x04\x3E'  # Exposure Comp Set (1-byte value)
            }
        }
    
    def connect(self) -> bool:
        """
        Establish UDP connection for VISCA protocol (sync version).
        Creates UDP socket for sending/receiving. Port is auto-assigned by OS.
        """
        try:
            if self.socket is None:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Don't bind to specific port - let OS assign ephemeral port
                # This allows multiple camera instances to run simultaneously
                # Camera will reply to whatever source port we use
                self.socket.settimeout(self.timeout)
                self.connected = True
                # Get the assigned port for logging
                local_port = self.socket.getsockname()[1] if self.socket.getsockname()[1] != 0 else "auto"
                print(f"VISCA: Created UDP socket (local port: {local_port}) for send+recv")
            return True
        except Exception as e:
            print(f"VISCA: Failed to create socket: {e}")
            return False
    
    async def connect_async(self) -> bool:
        """
        Establish async UDP connection for VISCA protocol.
        Creates async datagram endpoint for sending/receiving.
        """
        try:
            if self.transport is None:
                loop = asyncio.get_event_loop()
                self.datagram_protocol = VISCADatagramProtocol(self)
                self.transport, self.datagram_protocol = await loop.create_datagram_endpoint(
                    lambda: self.datagram_protocol,
                    local_addr=('0.0.0.0', 0)  # Let OS assign port
                )
                self.connected = True
                local_addr = self.transport.get_extra_info('sockname')
                print(f"VISCA: Created async UDP endpoint (local port: {local_addr[1]}) for send+recv")
            return True
        except Exception as e:
            print(f"VISCA: Failed to create async socket: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close UDP connection (sync version)."""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            return True
        except Exception as e:
            print(f"Error closing VISCA socket: {e}")
            return False
    
    async def disconnect_async(self) -> bool:
        """Close async UDP connection."""
        try:
            if self.transport:
                self.transport.close()
                self.transport = None
            self.datagram_protocol = None
            self.connected = False
            return True
        except Exception as e:
            print(f"Error closing VISCA async socket: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if VISCA connection is active."""
        return self.connected and (self.socket is not None or self.transport is not None)
    
    def _create_visca_packet(self, command: bytes, value: int = None) -> bytes:
        """
        Create VISCA packet with proper Sony SRG-XB25/SRG-XP1 formatting.
        
        Args:
            command: Base command bytes (may or may not have FF terminator)
            value: Optional parameter value
            
        Returns:
            Complete VISCA packet
        """
        # Check if command already has FF terminator
        if command.endswith(b'\xFF'):
            # Inquiry command - already complete
            if value is None:
                return command
            # Set command template - remove FF, add value, add FF back
            packet = command[:-1]  # Remove existing FF
        else:
            packet = command
        
        if value is not None:
            # Handle different command types based on command length
            if len(packet) == 7:  # Color Gain/Iris/Gain/Shutter (already has 00 00 00, just add last byte)
                # Value is 0-14 range, add it as single byte
                packet += bytes([value & 0xFF])
            elif len(packet) == 6:  # 2-byte commands
                # Convert to 2-byte format (high nibble, low nibble)
                high_byte = (value >> 4) & 0x0F
                low_byte = value & 0x0F
                packet += bytes([high_byte, low_byte])
            else:  # Single byte commands
                # Clamp value to valid range
                if value < 0:
                    value = 0
                elif value > 15:
                    value = 15
                packet += bytes([value])
        
        # Add terminator if not already present
        if not packet.endswith(b'\xFF'):
            packet += b'\xFF'
        
        return packet
    
    def _send_visca_command(self, cam_id: int, venue_number: int, command: bytes) -> Optional[bytes]:
        """
        Send VISCA command with VISCA-IP header and receive response.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            command: VISCA payload (0x81...FF)
            
        Returns:
            VISCA payload response (header stripped) or None if failed
        """
        if not self.is_connected():
            print(f"VISCA not connected for camera {cam_id}")
            return None
        
        venue_number += 54
        camera_ip = f"192.168.{venue_number}.5{cam_id}"
        
        for attempt in range(self.max_attempts):
            try:
                # Build VISCA-IP packet (header + payload)
                packet = self._build_visca_ip_packet(command)
                
                # Send packet
                self.socket.sendto(packet, (camera_ip, self.port))
                
                # Receive response (VISCA-IP header + VISCA payload)
                response, _ = self.socket.recvfrom(1024)
                
                # Skip VISCA-IP header (8 bytes) and return VISCA payload
                if len(response) > 8:
                    visca_payload = response[8:]
                    
                    # Validate VISCA response
                    if len(visca_payload) >= 3 and visca_payload[0] == self.reply_header:
                        return visca_payload
                
                # Pace between attempts
                if attempt < self.max_attempts - 1:
                    time.sleep(self.v_cycle)
                
            except socket.timeout:
                if attempt < self.max_attempts - 1:
                    time.sleep(self.v_cycle)
                else:
                    print(f"VISCA timeout for camera {cam_id} after {self.max_attempts} attempts")
                    return None
            except Exception as e:
                print(f"VISCA error for camera {cam_id}: {e}")
                if attempt < self.max_attempts - 1:
                    time.sleep(self.v_cycle)
                else:
                    return None
        
        return None
    
    def get_camera_params(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """
        Get current camera parameters via VISCA inquiry commands.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            
        Returns:
            Dictionary of camera parameters or None if failed
        """
        config_dict = {}
        
        # Clear any stale responses from socket buffer
        self.socket.setblocking(False)
        try:
            while True:
                self.socket.recvfrom(1024)
        except:
            pass
        self.socket.setblocking(True)
        self.socket.settimeout(self.timeout)
        
        for param_name, commands in self.command_map.items():
            if 'inquiry' in commands:
                command = self._create_visca_packet(commands['inquiry'])
                response = self._send_visca_command(cam_id, venue_number, command)
                
                if response and len(response) >= 3:
                    # Parse Sony VISCA response format: 0x90 0x50 [values] 0xFF
                    if response[0] == 0x90 and response[1] == 0x50:
                        if len(response) == 4:  # Single byte response (DigitalBrightLevel): 90 50 0X FF
                            value = response[2]
                            config_dict[param_name] = str(value)
                            print(f"VISCA: Got {param_name}={value} from camera {cam_id}")
                        elif len(response) == 7:  # Four byte response: 90 50 0p 0q 0r 0s FF
                            # Format for Iris, Gain, Shutter, ColorSaturation (4 nibbles)
                            p = response[2] & 0x0F
                            q = response[3] & 0x0F
                            r = response[4] & 0x0F
                            s = response[5] & 0x0F
                            value = (p << 12) | (q << 8) | (r << 4) | s
                            config_dict[param_name] = str(value)
                            print(f"VISCA: Got {param_name}={value} from camera {cam_id}")
                        else:
                            print(f"VISCA: Unexpected response length ({len(response)}) for {param_name}: {response.hex()}")
                            config_dict[param_name] = "0"
                    else:
                        print(f"VISCA: Unexpected response format for {param_name}: {response.hex()}")
                        config_dict[param_name] = "0"
                else:
                    print(f"VISCA: Failed to get {param_name} from camera {cam_id}")
                    config_dict[param_name] = "0"
        
        return config_dict if config_dict else None
    
    def set_camera_params(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """
        Set camera parameters via VISCA commands with improved error handling.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            params_dict: Dictionary of parameters to set
            
        Returns:
            True if successful, False otherwise
        """
        if not params_dict:
            return True
        
        success_count = 0
        total_params = len(params_dict)
        
        for param_name, value in params_dict.items():
            if param_name in self.command_map and 'set' in self.command_map[param_name]:
                try:
                    # Convert value to integer
                    int_value = int(value)
                    
                    # Create command packet
                    command = self._create_visca_packet(
                        self.command_map[param_name]['set'], 
                        int_value
                    )
                    
                    print(f"VISCA: Setting {param_name}={int_value} on camera {cam_id} (hex: {command.hex()})")
                    
                    # Send command
                    response = self._send_visca_command(cam_id, venue_number, command)
                    
                    if response and len(response) >= 3:
                        # For SET commands: expect ACK (0x90 0x4z FF) then Completion (0x90 0x5z FF)
                        if response[0] == 0x90 and (response[1] & 0xF0) == 0x40:  # Got ACK
                            # Wait for Completion
                            try:
                                completion, _ = self.socket.recvfrom(1024)
                                if len(completion) > 8:
                                    comp_payload = completion[8:]
                                    if comp_payload[0] == 0x90 and (comp_payload[1] & 0xF0) == 0x50:
                                        print(f"VISCA: Successfully set {param_name}={int_value} on camera {cam_id}")
                                        success_count += 1
                                    else:
                                        print(f"VISCA: Unexpected completion for {param_name}: {comp_payload.hex()}")
                            except Exception as e:
                                print(f"VISCA: No completion for {param_name}: {e}")
                        elif response[0] == 0x90 and (response[1] & 0xF0) == 0x50:  # Direct completion
                            print(f"VISCA: Successfully set {param_name}={int_value} on camera {cam_id}")
                            success_count += 1
                        else:
                            print(f"VISCA: Failed to set {param_name} on camera {cam_id}, response: {response.hex()}")
                    else:
                        print(f"VISCA: No response for {param_name} on camera {cam_id}")
                        
                except ValueError:
                    print(f"VISCA: Invalid value for {param_name}: {value}")
                except Exception as e:
                    print(f"VISCA: Error setting {param_name} on camera {cam_id}: {e}")
            else:
                print(f"VISCA: Unknown parameter {param_name}")
        
        success_rate = success_count / total_params if total_params > 0 else 0
        print(f"VISCA: Set {success_count}/{total_params} parameters successfully on camera {cam_id}")
        
        # Return True if at least some parameters were set successfully (not requiring ALL)
        return success_count > 0
    
    async def _send_visca_command_async(self, cam_id: int, venue_number: int, command: bytes) -> Optional[bytes]:
        """
        Send VISCA command with VISCA-IP header and receive response (async version).
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            command: VISCA payload (0x81...FF)
            
        Returns:
            VISCA payload response (header stripped) or None if failed
        """
        if not self.is_connected():
            print(f"VISCA not connected for camera {cam_id}")
            return None
        
        venue_number += 54
        camera_ip = f"192.168.{venue_number}.5{cam_id}"
        
        for attempt in range(self.max_attempts):
            try:
                # Build VISCA-IP packet (header + payload)
                packet = self._build_visca_ip_packet(command)
                
                # Send packet
                self.transport.sendto(packet, (camera_ip, self.port))
                
                # Wait for response with timeout
                sequence_number = struct.unpack('>I', packet[4:8])[0]
                future = asyncio.Future()
                self.command_futures[sequence_number] = future
                
                try:
                    response = await asyncio.wait_for(future, timeout=self.timeout)
                    
                    # Validate VISCA response
                    if len(response) >= 3 and response[0] == self.reply_header:
                        return response
                    
                except asyncio.TimeoutError:
                    print(f"VISCA timeout for camera {cam_id} on attempt {attempt + 1}")
                    self.command_futures.pop(sequence_number, None)
                
                # Pace between attempts
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.v_cycle)
                
            except Exception as e:
                print(f"VISCA error for camera {cam_id}: {e}")
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.v_cycle)
                else:
                    return None
        
        return None
    
    async def _set_single_param_async(self, cam_id: int, venue_number: int, 
                                    param_name: str, value: Union[int, str]) -> bool:
        """Set a single parameter asynchronously."""
        try:
            # Convert value to integer
            int_value = int(value)
            
            # Create command packet
            command = self._create_visca_packet(
                self.command_map[param_name]['set'], 
                int_value
            )
            
            print(f"VISCA: Setting {param_name}={int_value} on camera {cam_id}")
            
            # Send command and wait for response
            response = await self._send_visca_command_async(cam_id, venue_number, command)
            
            if response and len(response) >= 3:
                # For SET commands: expect ACK (0x90 0x4z FF) then Completion (0x90 0x5z FF)
                if response[0] == 0x90 and (response[1] & 0xF0) == 0x40:  # Got ACK
                    # Wait for Completion
                    try:
                        completion = await self._wait_for_completion_async()
                        if completion and completion[0] == 0x90 and (completion[1] & 0xF0) == 0x50:
                            print(f"VISCA: Successfully set {param_name}={int_value} on camera {cam_id}")
                            return True
                        else:
                            print(f"VISCA: Unexpected completion for {param_name}: {completion.hex() if completion else 'None'}")
                    except Exception as e:
                        print(f"VISCA: No completion for {param_name}: {e}")
                elif response[0] == 0x90 and (response[1] & 0xF0) == 0x50:  # Direct completion
                    print(f"VISCA: Successfully set {param_name}={int_value} on camera {cam_id}")
                    return True
                else:
                    print(f"VISCA: Failed to set {param_name} on camera {cam_id}, response: {response.hex()}")
            else:
                print(f"VISCA: No response for {param_name} on camera {cam_id}")
            
            return False
            
        except ValueError:
            print(f"VISCA: Invalid value for {param_name}: {value}")
            return False
        except Exception as e:
            print(f"VISCA: Error setting {param_name} on camera {cam_id}: {e}")
            return False
    
    async def _wait_for_completion_async(self) -> Optional[bytes]:
        """Wait for completion response asynchronously."""
        try:
            # Wait for next response in command_futures
            if self.command_futures:
                # Get the first pending future
                sequence_number, future = next(iter(self.command_futures.items()))
                completion = await asyncio.wait_for(future, timeout=self.timeout)
                self.command_futures.pop(sequence_number, None)
                return completion
        except asyncio.TimeoutError:
            pass
        return None
    
    async def get_camera_params_async(self, cam_id: int, venue_number: int) -> Optional[Dict[str, str]]:
        """
        Get current camera parameters via VISCA inquiry commands (async version).
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            
        Returns:
            Dictionary of camera parameters or None if failed
        """
        config_dict = {}
        
        # Clear any stale responses from command_futures
        self.command_futures.clear()
        
        # Create tasks for all inquiry commands
        inquiry_tasks = []
        for param_name, commands in self.command_map.items():
            if 'inquiry' in commands:
                command = self._create_visca_packet(commands['inquiry'])
                task = asyncio.create_task(
                    self._send_visca_command_async(cam_id, venue_number, command)
                )
                inquiry_tasks.append((param_name, task))
        
        # Execute all inquiries concurrently
        results = await asyncio.gather(*[task for _, task in inquiry_tasks], return_exceptions=True)
        
        # Process results
        for i, (param_name, _) in enumerate(inquiry_tasks):
            response = results[i]
            
            if isinstance(response, Exception):
                print(f"VISCA: Exception getting {param_name} from camera {cam_id}: {response}")
                config_dict[param_name] = "0"
                continue
            
            if response and len(response) >= 3:
                # Parse Sony VISCA response format: 0x90 0x50 [values] 0xFF
                if response[0] == 0x90 and response[1] == 0x50:
                    if len(response) == 4:  # Single byte response (DigitalBrightLevel): 90 50 0X FF
                        value = response[2]
                        config_dict[param_name] = str(value)
                        print(f"VISCA: Got {param_name}={value} from camera {cam_id}")
                    elif len(response) == 7:  # Four byte response: 90 50 0p 0q 0r 0s FF
                        # Format for Iris, Gain, Shutter, ColorSaturation (4 nibbles)
                        p = response[2] & 0x0F
                        q = response[3] & 0x0F
                        r = response[4] & 0x0F
                        s = response[5] & 0x0F
                        value = (p << 12) | (q << 8) | (r << 4) | s
                        config_dict[param_name] = str(value)
                        print(f"VISCA: Got {param_name}={value} from camera {cam_id}")
                    else:
                        print(f"VISCA: Unexpected response length ({len(response)}) for {param_name}: {response.hex()}")
                        config_dict[param_name] = "0"
                else:
                    print(f"VISCA: Unexpected response format for {param_name}: {response.hex()}")
                    config_dict[param_name] = "0"
            else:
                print(f"VISCA: Failed to get {param_name} from camera {cam_id}")
                config_dict[param_name] = "0"
        
        return config_dict if config_dict else None
    
    async def set_camera_params_async(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """
        Set camera parameters via VISCA commands with concurrent execution (async version).
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            params_dict: Dictionary of parameters to set
            
        Returns:
            True if successful, False otherwise
        """
        if not params_dict:
            return True
        
        # Create tasks for all parameters
        tasks = []
        for param_name, value in params_dict.items():
            if param_name in self.command_map and 'set' in self.command_map[param_name]:
                task = asyncio.create_task(
                    self._set_single_param_async(cam_id, venue_number, param_name, value)
                )
                tasks.append(task)
        
        if not tasks:
            print("VISCA: No valid parameters to set")
            return False
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(1 for result in results if result is True)
        total_params = len(params_dict)
        
        print(f"VISCA: Set {success_count}/{total_params} parameters successfully on camera {cam_id}")
        
        # Return True if at least some parameters were set successfully
        return success_count > 0


class ProtocolFactory:
    """Factory class for creating camera protocol instances."""
    
    @staticmethod
    def create_protocol(protocol_type: str = "cgi", config_file: str = None) -> CameraProtocolInterface:
        """
        Create a camera protocol instance.
        
        Args:
            protocol_type: Type of protocol ('cgi' or 'visca')
            config_file: Path to configuration file
            
        Returns:
            Protocol instance
            
        Raises:
            ValueError: If protocol type is not supported
        """
        if protocol_type.lower() == "cgi":
            return CGIProtocol(config_file)
        elif protocol_type.lower() == "visca":
            return VISCAProtocol(config_file)
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")
    
    @staticmethod
    def create_protocol_from_config(config_file: str = None) -> CameraProtocolInterface:
        """
        Create protocol instance based on configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Protocol instance
        """
        if config_file is None:
            import os
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                protocol_type = config.get('protocol', {}).get('type', 'cgi')
                return ProtocolFactory.create_protocol(protocol_type, config_file)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using default CGI protocol")
            return CGIProtocol(config_file)
