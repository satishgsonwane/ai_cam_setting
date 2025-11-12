# Configuration Reference Guide

This document provides comprehensive documentation for all configuration parameters in the AI Camera Settings system.

## Table of Contents

- [Cost Weights](#cost-weights)
- [Hysteresis](#hysteresis)
- [Protocol Configuration](#protocol-configuration)
- [ROI Detection](#roi-detection)
- [Camera Settings](#camera-settings)
- [Network Configuration](#network-configuration)
- [Image Processing](#image-processing)
- [Master Camera](#master-camera)

---

## Cost Weights

Camera parameter adjustment preferences - lower cost means preferred parameter.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_cost` | float | Starting cost value for this parameter type |
| `max_cost` | float | Maximum cost when parameter is far from optimal |
| `min_cost` | float | Minimum cost when parameter is close to optimal |
| `preferred_direction` | string | Direction preference: `"increase"`, `"decrease"`, or `"either"` |

### Camera Parameters

#### ExposureIris
- **Cost**: Low (0.5 base, 2.0 max, 0.2 min)
- **Direction**: Increase preferred
- **Description**: Preferred for brightness adjustments, minimal depth-of-field impact

#### ExposureExposureTime
- **Cost**: Medium (1.5 base, 5.0 max, 0.5 min)
- **Direction**: Decrease preferred
- **Description**: Affects motion blur, faster shutter preferred

#### ExposureGain
- **Cost**: High (3.0 base, 10.0 max, 1.0 min)
- **Direction**: Decrease preferred
- **Description**: Introduces noise, use as last resort

#### DigitalBrightLevel
- **Cost**: Medium-High (2.0 base, 6.0 max, 0.5 min)
- **Direction**: Either
- **Description**: Digital processing overhead

#### ColorSaturation
- **Cost**: Low (0.8 base, 3.0 max, 0.3 min)
- **Direction**: Either
- **Description**: Low cost for color adjustments

---

## Hysteresis

Prevents oscillation by creating dead bands around acceptable ranges.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dead_band_percentage` | float | 0.05 | No adjustment zone around target (5% = 0.05) |
| `inner_threshold_percentage` | float | 0.02 | Inner boundary for fine adjustments (2% = 0.02) |
| `outer_threshold_percentage` | float | 0.08 | Outer boundary for coarse adjustments (8% = 0.08) |

### Behavior

- **Dead Band**: No adjustments made when within acceptable range
- **Inner Threshold**: Fine adjustments for small deviations
- **Outer Threshold**: Coarse adjustments for large deviations

---

## Protocol Configuration

Camera communication protocol settings with advanced concurrency control.

### Protocol Types

#### CGI (HTTP-based)
- **Use Case**: Web-based camera control
- **Timeout**: 2 seconds
- **Max Attempts**: 50 retries
- **Retry Delay**: 0.5 seconds
- **Connection Pool**: 6 concurrent connections

#### VISCA (UDP-based VISCA-over-IP)
- **Use Case**: Professional PTZ cameras
- **Port**: 52381 (default)
- **Timeout**: 0.1 seconds
- **Max Attempts**: 2 retries
- **Retry Delay**: 0.01 seconds
- **Batch Size**: 5 parameters per batch
- **Connection Pool**: 6 concurrent connections

### Controlled Concurrency

Advanced concurrency control with rate limiting for VISCA protocol.

#### Core Settings

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | boolean | true | - | Master switch for controlled concurrency |
| `max_concurrent_operations` | integer | 5 | 1-10 | Maximum simultaneous parameter operations |
| `fallback_to_sequential` | boolean | true | - | Enable adaptive behavior on failures |

#### Timing Configuration

| Parameter | Type | Default | Range | Unit | Description |
|-----------|------|---------|-------|------|-------------|
| `concurrent` | integer | 10 | 5-50 | ms | Delay between concurrent operations |
| `sequential` | integer | 20 | 15-100 | ms | Delay between sequential operations |
| `retry_delay` | integer | 5 | 5-50 | ms | Additional delay before retrying |

#### Rate Limiting

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `set_operations` | boolean | true | - | Apply rate limiting to SET operations |
| `get_operations` | boolean | true | - | Apply rate limiting to GET operations |
| `max_requests_per_second` | integer | 10 | 5-50 | Maximum requests per second |

### Performance Configurations

#### Conservative (Maximum Safety)
```json
{
  "enabled": true,
  "max_concurrent_operations": 2,
  "fallback_to_sequential": true,
  "pacing_ms": {
    "concurrent": 20,
    "sequential": 30,
    "retry_delay": 10
  },
  "rate_limiting": {
    "set_operations": true,
    "get_operations": true,
    "max_requests_per_second": 5
  }
}
```
- **Use Case**: Debugging, testing, unreliable hardware
- **Performance**: Slowest but most reliable

#### Balanced (Production Default)
```json
{
  "enabled": true,
  "max_concurrent_operations": 5,
  "fallback_to_sequential": true,
  "pacing_ms": {
    "concurrent": 10,
    "sequential": 20,
    "retry_delay": 5
  },
  "rate_limiting": {
    "set_operations": true,
    "get_operations": true,
    "max_requests_per_second": 10
  }
}
```
- **Use Case**: Most production environments
- **Performance**: Optimal balance of speed and reliability

#### Aggressive (Maximum Speed)
```json
{
  "enabled": true,
  "max_concurrent_operations": 8,
  "fallback_to_sequential": true,
  "pacing_ms": {
    "concurrent": 5,
    "sequential": 15,
    "retry_delay": 3
  },
  "rate_limiting": {
    "set_operations": true,
    "get_operations": true,
    "max_requests_per_second": 20
  }
}
```
- **Use Case**: High-performance environments with reliable hardware
- **Performance**: Fastest but riskier

### Monitoring

Use `protocol.get_concurrency_stats()` to monitor performance:

```python
stats = protocol.get_concurrency_stats()
print(f"Success Rate: {stats['success_rate']:.2%}")
print(f"Current Limit: {stats['current_limit']}")
print(f"Rate Limiting: {stats['rate_limiting_active']}")
```

**Available Metrics**:
- `enabled` - Whether controlled concurrency is active
- `current_limit` - Current concurrency limit (may be reduced by adaptive behavior)
- `max_limit` - Maximum configured concurrency limit
- `success_count` - Total successful operations
- `failure_count` - Total failed operations
- `success_rate` - Percentage of successful operations
- `rate_limiting_active` - Whether rate limiting is enabled

---

## ROI Detection

Region of Interest detection settings for image analysis.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_green_mask` | boolean | false | Enable green pitch mask filtering |
| `green_hsv_range.lower` | array | [35, 40, 40] | Lower HSV threshold [Hue, Saturation, Value] |
| `green_hsv_range.upper` | array | [85, 255, 255] | Upper HSV threshold [Hue, Saturation, Value] |
| `morphology.kernel_size` | integer | 5 | Size of morphological kernel |
| `morphology.iterations` | integer | 2 | Number of morphological operations |

### Green Pitch Detection

- **Purpose**: Filter out green pitch areas for robust field analysis
- **HSV Range**: Adjustable color range for different lighting conditions
- **Morphology**: Noise removal and mask cleaning

---

## Camera Settings

Camera parameter adjustment rules and acceptable ranges.

### Acceptable Ranges

| Feature | Range | Description |
|---------|-------|-------------|
| `normalized_brightness` | [0.25, 0.5] | Acceptable brightness range (0.0-1.0) |
| `normalized_saturation` | [0.4, 0.7] | Acceptable saturation range (0.0-1.0) |

### Adjustment Rules

| Feature | Parameters | Description |
|---------|------------|-------------|
| `normalized_brightness` | ExposureIris, ExposureExposureTime, ExposureGain, DigitalBrightLevel | Parameters to adjust for brightness optimization |
| `normalized_saturation` | ColorSaturation | Parameters to adjust for saturation optimization |

---

## Network Configuration

Network settings for camera communication.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `venue_number` | integer | 13 | Venue identifier for multi-venue deployments |
| `username` | string | "admin" | Camera authentication username |
| `password` | string | "media99zz" | Camera authentication password |

---

## Image Processing

Image processing and analysis settings.

### Frame Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame_size.height` | integer | 1080 | Input frame height in pixels |
| `frame_size.width` | integer | 1920 | Input frame width in pixels |
| `crop_size.height` | integer | 360 | Lower third crop height in pixels |
| `crop_size.width` | integer | 1920 | Lower third crop width in pixels |

### Analysis Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sleep_time_seconds` | float | 1.0 | Delay between image captures |
| `decimal_places` | integer | 3 | Precision for numerical calculations |

---

## Master Camera

Multi-camera coordination settings.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cam_id` | integer | 1 | Camera ID of the master camera for coordination |

---

## Best Practices

### Configuration Tuning

1. **Start Conservative**: Begin with conservative settings and gradually increase
2. **Monitor Performance**: Use concurrency stats to track success rates
3. **Test Thoroughly**: Validate settings with your specific camera hardware
4. **Adjust Based on Environment**: Network conditions affect optimal settings

### Troubleshooting

#### High Failure Rates
- Reduce `max_concurrent_operations`
- Increase `pacing_ms` values
- Lower `max_requests_per_second`
- Enable `fallback_to_sequential`

#### Slow Performance
- Increase `max_concurrent_operations` (if success rate is high)
- Decrease `pacing_ms` values (if cameras can handle it)
- Increase `max_requests_per_second` (if network allows)

#### Camera Overload
- Enable rate limiting for both SET and GET operations
- Increase `retry_delay` and `sequential` pacing
- Reduce concurrency limits

### VISCA Compliance

- **Sequential Operations**: Minimum 20ms between commands
- **Concurrent Operations**: Minimum 10ms between commands
- **Command Buffer**: Avoid overwhelming camera command buffer
- **ACK Handling**: System automatically handles ACK and Completion responses

---

## Configuration Examples

### Complete Production Configuration
```json
{
  "cost_weights": {
    "ExposureIris": {
      "base_cost": 0.5,
      "max_cost": 2.0,
      "min_cost": 0.2,
      "preferred_direction": "increase"
    }
  },
  "hysteresis": {
    "dead_band_percentage": 0.05,
    "inner_threshold_percentage": 0.02,
    "outer_threshold_percentage": 0.08
  },
  "protocol": {
    "type": "visca",
    "async_enabled": true,
    "visca": {
      "port": 52381,
      "timeout": 0.1,
      "max_attempts": 2,
      "retry_delay": 0.01,
      "concurrent_params": true,
      "batch_size": 5,
      "connection_pool_size": 6,
      "concurrency": {
        "enabled": true,
        "max_concurrent_operations": 5,
        "fallback_to_sequential": true,
        "pacing_ms": {
          "concurrent": 10,
          "sequential": 20,
          "retry_delay": 5
        },
        "rate_limiting": {
          "set_operations": true,
          "get_operations": true,
          "max_requests_per_second": 10
        }
      }
    }
  }
}
```

For more examples and detailed explanations, refer to the specific sections above.
