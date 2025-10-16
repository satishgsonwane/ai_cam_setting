#!/bin/bash

# Smart Camera Control System - Start All Cameras
# Enhanced version with improved error handling, logging, and argument parsing

# Default configuration
VENUE_NUMBER=13  # Grotta venue
LOG_DIR="/home/ozer/logs/camera_control"
PROTOCOL=""
CAMERA_IDS=""
CONFIG_FILE="/home/ozer/AI/AI_configs/cameraconfig.json"
VERBOSE=false
DRY_RUN=false
CONDA_ENV="ball_tracker"  # Default conda environment

# Function to display usage
show_usage() {
    echo "=========================================="
    echo "Smart Camera Control System - Start All Cameras"
    echo "=========================================="
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  -p, --protocol PROTOCOL    Camera protocol: 'cgi' or 'visca' (default: from config)"
    echo "  -v, --venue NUMBER         Venue number 1-15 (default: 13)"
    echo "  -c, --cameras IDS          Comma-separated camera IDs (default: from config or 1-6)"
    echo "  -l, --log-dir DIR          Log directory (default: /home/ozer/logs/camera_control)"
    echo "  -f, --config-file FILE     Camera config JSON file (default: /home/ozer/AI/AI_configs/cameraconfig.json)"
    echo "  -e, --env ENV_NAME         Conda environment name (default: ball_tracker)"
    echo "  -V, --verbose              Enable verbose output"
    echo "  -d, --dry-run              Show what would be done without actually starting cameras"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 --protocol visca --venue 13"
    echo "  $0 -p cgi -v 15 -c 1,2,3"
    echo "  $0 --dry-run --verbose"
    echo "  $0 -p visca -V"
    echo "=========================================="
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--protocol)
            PROTOCOL="$2"
            if [[ "$PROTOCOL" != "cgi" && "$PROTOCOL" != "visca" ]]; then
                echo "Error: Protocol must be 'cgi' or 'visca'"
                exit 1
            fi
            shift 2
            ;;
        -v|--venue)
            VENUE_NUMBER="$2"
            if ! [[ "$VENUE_NUMBER" =~ ^[0-9]+$ ]] || [ "$VENUE_NUMBER" -lt 1 ] || [ "$VENUE_NUMBER" -gt 15 ]; then
                echo "Error: Venue number must be between 1 and 15"
                exit 1
            fi
            shift 2
            ;;
        -c|--cameras)
            CAMERA_IDS="$2"
            shift 2
            ;;
        -l|--log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        -f|--config-file)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -e|--env)
            CONDA_ENV="$2"
            shift 2
            ;;
        -V|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create log directory
mkdir -p "$LOG_DIR"

# Verbose output function
verbose_echo() {
    if [ "$VERBOSE" = true ]; then
        echo "$@"
    fi
}

# Function to start a camera
start_camera() {
    local cam_id=$1
    local protocol=${2:-""}  # Optional protocol argument
    local log_file="$LOG_DIR/camera_${cam_id}.log"
    
    # Get conda environment path
    local conda_python="/root/miniconda3/envs/${CONDA_ENV}/bin/python"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would start camera $cam_id with protocol: ${protocol:-"from config"}"
        verbose_echo "[DRY RUN] Conda environment: $CONDA_ENV"
        verbose_echo "[DRY RUN] Python path: $conda_python"
        verbose_echo "[DRY RUN] Command: $conda_python rule_engine.py --cam_id $cam_id --venue_number $VENUE_NUMBER ${protocol:+--protocol $protocol}"
        verbose_echo "[DRY RUN] Log file: $log_file"
        return
    fi
    
    echo "Starting camera $cam_id..."
    if [ -n "$protocol" ]; then
        echo "Using $protocol protocol"
        "$conda_python" rule_engine.py --cam_id $cam_id --venue_number $VENUE_NUMBER --protocol $protocol > $log_file 2>&1 &
    else
        "$conda_python" rule_engine.py --cam_id $cam_id --venue_number $VENUE_NUMBER > $log_file 2>&1 &
    fi
    local pid=$!
    echo "Camera $cam_id started with PID $pid"
    echo $pid > "$LOG_DIR/camera_${cam_id}.pid"
    verbose_echo "Log file: $log_file"
    verbose_echo "Using conda environment: $CONDA_ENV ($conda_python)"
}

# Determine camera IDs to use
if [ -n "$CAMERA_IDS" ]; then
    # Use explicitly provided camera IDs
    echo "Using specified camera IDs: $CAMERA_IDS"
    IFS=',' read -ra cam_ids <<< "$CAMERA_IDS"
    verbose_echo "Parsed camera IDs: ${cam_ids[*]}"
elif [ -f "$CONFIG_FILE" ]; then
    # Use camera configuration from JSON
    echo "Using camera configuration from JSON: $CONFIG_FILE"
    verbose_echo "Extracting active cameras from config..."
    
    # Extract camera IDs which are active
    active_cam_ids=$(jq -r '.camera_config[] | select(.status == "active") | .camera_id' "$CONFIG_FILE" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$active_cam_ids" ]; then
        # Convert the string of camera IDs into an array
        IFS=$'\n' read -d '' -r -a cam_ids <<< "$active_cam_ids"
        echo "Active cameras from config: ${cam_ids[*]}"
    else
        echo "Failed to parse config file or no active cameras found, using default cameras 1-6..."
        cam_ids=(1 2 3 4 5 6)
    fi
else
    echo "No camera config found at $CONFIG_FILE, using default cameras 1-6..."
    cam_ids=(1 2 3 4 5 6)
fi

# Validate camera IDs
for cam_id in "${cam_ids[@]}"; do
    if ! [[ "$cam_id" =~ ^[0-9]+$ ]] || [ "$cam_id" -lt 1 ] || [ "$cam_id" -gt 6 ]; then
        echo "Error: Invalid camera ID '$cam_id'. Must be between 1 and 6."
        exit 1
    fi
done

# Display configuration summary
echo "=========================================="
echo "Configuration Summary:"
echo "  Venue Number: $VENUE_NUMBER"
echo "  Protocol: ${PROTOCOL:-"from config"}"
echo "  Camera IDs: ${cam_ids[*]}"
echo "  Conda Environment: $CONDA_ENV"
echo "  Log Directory: $LOG_DIR"
echo "  Config File: $CONFIG_FILE"
echo "  Verbose: $VERBOSE"
echo "  Dry Run: $DRY_RUN"
echo "=========================================="

# Start each camera
echo "Starting cameras..."
for cam_id in "${cam_ids[@]}"
do
    if [ ! -z "$cam_id" ] && [ "$cam_id" != "null" ]; then
        start_camera $cam_id $PROTOCOL
        if [ "$DRY_RUN" = false ]; then
            sleep 2  # Small delay between camera starts
        fi
    fi
done

if [ "$DRY_RUN" = true ]; then
    echo "=========================================="
    echo "DRY RUN COMPLETED - No cameras were actually started"
    echo "=========================================="
else
    echo "=========================================="
    echo "All cameras started successfully!"
    echo "Logs available in: $LOG_DIR"
    echo "To stop all cameras: ./setstopall.sh"
    echo "To check status: ps aux | grep rule_engine"
    echo "=========================================="
fi
