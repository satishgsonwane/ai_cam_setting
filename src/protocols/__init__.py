"""
Camera Protocol Abstraction Layer

Provides abstraction for different camera communication protocols.
"""

from .camera_protocol import ProtocolFactory, CameraProtocolInterface, CGIProtocol, VISCAProtocol

__all__ = ['ProtocolFactory', 'CameraProtocolInterface', 'CGIProtocol', 'VISCAProtocol']
