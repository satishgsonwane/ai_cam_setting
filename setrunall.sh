#!/bin/bash

# Smart Camera Control System - Start All Cameras
# Enhanced version with improved error handling and logging

echo "=========================================="
echo "Starting Smart Camera Control System"
echo "=========================================="

# Configuration
VENUE_NUMBER=15  # Grotta venue
LOG_DIR="/home/ozer/logs/camera_control"
mkdir -p $LOG_DIR

# Function to start a camera
start_camera() {
    local cam_id=$1
    local log_file="$LOG_DIR/camera_${cam_id}.log"
    
    echo "Starting camera $cam_id..."
    python3 rule_engine.py --cam_id $cam_id --venue_number $VENUE_NUMBER > $log_file 2>&1 &
    local pid=$!
    echo "Camera $cam_id started with PID $pid"
    echo $pid > "$LOG_DIR/camera_${cam_id}.pid"
}

# Check if JSON config exists, otherwise use default cameras
if [ -f "/home/ozer/AI/AI_configs/cameraconfig.json" ]; then
    echo "Using camera configuration from JSON..."
    # Extract camera IDs which are active
    active_cam_ids=$(jq -r '.camera_config[] | select(.status == "active") | .camera_id' /home/ozer/AI/AI_configs/cameraconfig.json)
    
    # Convert the string of camera IDs into an array
    IFS=$'\n' read -d '' -r -a cam_ids <<< "$active_cam_ids"
    
    echo "Active cameras: ${cam_ids[*]}"
else
    echo "No camera config found, using default cameras 1-6..."
    cam_ids=(1 2 3 4 5 6)
fi

# Start each camera
for cam_id in "${cam_ids[@]}"
do
    if [ ! -z "$cam_id" ] && [ "$cam_id" != "null" ]; then
        start_camera $cam_id
        sleep 2  # Small delay between camera starts
    fi
done

echo "=========================================="
echo "All cameras started successfully!"
echo "Logs available in: $LOG_DIR"
echo "To stop all cameras: ./setstopall.sh"
echo "To check status: ps aux | grep rule_engine"
echo "=========================================="
