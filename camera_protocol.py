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


class CGIProtocol(CameraProtocolInterface):
    """CGI (HTTP) protocol implementation for camera communication."""
    
    def __init__(self, config_file: str = "camera_control_config.json"):
        """
        Initialize CGI protocol.
        
        Args:
            config_file: Path to configuration file
        """
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


class VISCAProtocol(CameraProtocolInterface):
    """VISCA over IP protocol implementation for camera communication."""
    
    def __init__(self, config_file: str = "camera_control_config.json"):
        """
        Initialize VISCA protocol.
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self._load_config(config_file)
        self.connected = False
        self.socket = None
        self.port = self.config.get('protocol', {}).get('visca', {}).get('port', 52381)
        self.timeout = self.config.get('protocol', {}).get('visca', {}).get('timeout', 1.0)
        self.max_attempts = self.config.get('protocol', {}).get('visca', {}).get('max_attempts', 10)
        self.retry_delay = self.config.get('protocol', {}).get('visca', {}).get('retry_delay', 0.5)
        
        # VISCA command mappings
        self.command_map = self._initialize_command_map()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _initialize_command_map(self) -> Dict[str, Dict[str, bytes]]:
        """Initialize VISCA command mappings."""
        return {
            'ExposureIris': {
                'inquiry': b'\x81\x09\x04\x38\xFF',  # Iris Position Inq
                'set': b'\x81\x01\x04\x38'  # Iris Position Set (value appended)
            },
            'ExposureGain': {
                'inquiry': b'\x81\x09\x04\x3C\xFF',  # Gain Position Inq
                'set': b'\x81\x01\x04\x3C'  # Gain Position Set (value appended)
            },
            'ExposureExposureTime': {
                'inquiry': b'\x81\x09\x04\x3A\xFF',  # Shutter Position Inq
                'set': b'\x81\x01\x04\x3A'  # Shutter Position Set (value appended)
            },
            'ColorSaturation': {
                'inquiry': b'\x81\x09\x04\x49\xFF',  # Color Gain Inq
                'set': b'\x81\x01\x04\x49'  # Color Gain Set (value appended)
            },
            'DigitalBrightLevel': {
                'inquiry': b'\x81\x09\x04\x4E\xFF',  # Digital Gain Inq
                'set': b'\x81\x01\x04\x4E'  # Digital Gain Set (value appended)
            }
        }
    
    def connect(self) -> bool:
        """Establish UDP connection for VISCA protocol."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to create VISCA socket: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close UDP connection."""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            return True
        except Exception as e:
            print(f"Error closing VISCA socket: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if VISCA connection is active."""
        return self.connected and self.socket is not None
    
    def _create_visca_packet(self, command: bytes, value: int = None) -> bytes:
        """
        Create VISCA packet with proper formatting.
        
        Args:
            command: Base command bytes
            value: Optional parameter value
            
        Returns:
            Complete VISCA packet
        """
        packet = command
        if value is not None:
            # Convert value to VISCA format (typically 2 bytes)
            packet += struct.pack('>H', value)  # Big-endian unsigned short
        packet += b'\xFF'  # Terminator
        return packet
    
    def _send_visca_command(self, cam_id: int, venue_number: int, command: bytes) -> Optional[bytes]:
        """
        Send VISCA command and receive response.
        
        Args:
            cam_id: Camera ID (1-6)
            venue_number: Venue number (1-15)
            command: VISCA command bytes
            
        Returns:
            Response bytes or None if failed
        """
        if not self.is_connected():
            return None
        
        venue_number += 54
        camera_ip = f"192.168.{venue_number}.5{cam_id}"
        
        try:
            # Send command
            self.socket.sendto(command, (camera_ip, self.port))
            
            # Receive response
            response, addr = self.socket.recvfrom(1024)
            return response
            
        except socket.timeout:
            print(f"VISCA command timeout for camera {cam_id}")
            return None
        except Exception as e:
            print(f"Error sending VISCA command: {e}")
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
        
        for param_name, commands in self.command_map.items():
            if 'inquiry' in commands:
                command = self._create_visca_packet(commands['inquiry'])
                response = self._send_visca_command(cam_id, venue_number, command)
                
                if response and len(response) >= 4:
                    # Parse VISCA response (simplified - actual parsing depends on camera model)
                    # This is a placeholder implementation
                    value = response[3] if len(response) > 3 else "0"
                    config_dict[param_name] = str(value)
                else:
                    print(f"Failed to get {param_name} via VISCA")
                    config_dict[param_name] = "0"
        
        return config_dict if config_dict else None
    
    def set_camera_params(self, cam_id: int, venue_number: int, params_dict: Dict[str, Union[int, str]]) -> bool:
        """
        Set camera parameters via VISCA commands.
        
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
        
        for param_name, value in params_dict.items():
            if param_name in self.command_map and 'set' in self.command_map[param_name]:
                command = self._create_visca_packet(
                    self.command_map[param_name]['set'], 
                    int(value)
                )
                
                for attempt in range(self.max_attempts):
                    response = self._send_visca_command(cam_id, venue_number, command)
                    
                    if response and len(response) >= 2:
                        # Check for ACK (0x41) or COMPLETION (0x51)
                        if response[1] in [0x41, 0x51]:
                            print(f"Successfully set {param_name}={value} via VISCA")
                            success_count += 1
                            break
                        else:
                            print(f"VISCA command failed for {param_name}, attempt {attempt + 1}")
                    else:
                        print(f"No response for {param_name}, attempt {attempt + 1}")
                    
                    if attempt < self.max_attempts - 1:
                        time.sleep(self.retry_delay)
        
        return success_count == len(params_dict)


class ProtocolFactory:
    """Factory class for creating camera protocol instances."""
    
    @staticmethod
    def create_protocol(protocol_type: str = "cgi", config_file: str = "camera_control_config.json") -> CameraProtocolInterface:
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
    def create_protocol_from_config(config_file: str = "camera_control_config.json") -> CameraProtocolInterface:
        """
        Create protocol instance based on configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Protocol instance
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                protocol_type = config.get('protocol', {}).get('type', 'cgi')
                return ProtocolFactory.create_protocol(protocol_type, config_file)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using default CGI protocol")
            return CGIProtocol()
