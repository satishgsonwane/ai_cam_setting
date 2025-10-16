# AI Camera Control System

A smart camera control system with protocol abstraction for Sony SRG-XB25/SRG-XP1 cameras. Supports both CGI (HTTP) and VISCA-over-IP protocols with intelligent parameter adjustment.

## Features

- **Protocol Abstraction**: Support for both CGI and VISCA-over-IP protocols
- **Intelligent Parameter Adjustment**: Cost-based parameter selection with hysteresis
- **ROI Detection**: Region of interest detection for better image analysis
- **Master/Slave Architecture**: Synchronized multi-camera control
- **Real-time Communication**: NATS-based messaging system
- **Comprehensive Testing**: Unit tests and integration tests

## Repository Structure

```
ai_cam_settings/
├── src/                    # Source code
│   ├── core/              # Main control engine
│   ├── protocols/         # Camera protocol implementations
│   ├── detection/         # ROI detection and image processing
│   ├── cost/              # Cost function calculations
│   └── utils/             # Utility functions and settings management
├── scripts/               # Additional shell scripts
├── configs/               # Configuration files
├── tests/                 # Test suite
├── demos/                 # Demonstration scripts
├── docs/                  # Documentation
├── setrunall.sh           # Start all cameras script
└── setstopall.sh          # Stop all cameras script
```

## Quick Start

### 1. Configuration

Copy the example configuration and customize it:

```bash
cp configs/camera_control_config.json.example configs/camera_control_config.json
```

Edit `configs/camera_control_config.json` with your camera network settings.

### 2. Running the System

Start cameras with VISCA protocol:

```bash
./setrunall.sh -p visca -v 13 -c 1,2,3
```

Start cameras with CGI protocol:

```bash
./setrunall.sh -p cgi -v 13 -c 1,2,3
```

### 3. Stopping the System

```bash
./setstopall.sh
```

## Protocol Support

### CGI Protocol
- HTTP-based communication
- Digest authentication
- Suitable for network cameras with CGI interface

### VISCA Protocol
- UDP-based VISCA-over-IP communication
- Direct Sony camera control
- Optimized for Sony SRG-XB25/SRG-XP1 cameras

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

Run protocol-specific tests:

```bash
python tests/test_protocols.py
python tests/test_system.py
```

## Demos

Run demonstration scripts:

```bash
python demos/demo_system.py
python demos/demo_protocol_agnostic.py
```

## Configuration

### Camera Configuration
- `configs/camera_control_config.json`: Main system configuration
- `configs/camera_settings_features_config.json`: Camera parameter ranges
- `configs/cam_params_range.json`: Parameter value ranges

### Environment Variables
- Set appropriate conda environment in scripts
- Configure NATS server connection
- Set log directory paths

## Development

### Adding New Protocols
1. Create new protocol class inheriting from `CameraProtocolInterface`
2. Implement required methods: `connect()`, `disconnect()`, `get_camera_params()`, `set_camera_params()`
3. Register in `ProtocolFactory`

### Adding New Parameters
1. Update parameter mappings in protocol classes
2. Add to acceptable ranges in configuration
3. Update cost functions if needed

## Dependencies

- Python 3.10+
- OpenCV
- NumPy
- PyTorch
- NATS client
- Requests
- Asyncio

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
