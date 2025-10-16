#!/bin/bash

# Smart Camera Control System - Stop All Cameras
# Enhanced version with graceful shutdown and cleanup

echo "=========================================="
echo "Stopping Smart Camera Control System"
echo "=========================================="

LOG_DIR="/home/ozer/logs/camera_control"

# Function to stop a camera gracefully
stop_camera() {
    local cam_id=$1
    local pid_file="$LOG_DIR/camera_${cam_id}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat $pid_file)
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping camera $cam_id (PID: $pid)..."
            kill -TERM $pid
            
            # Wait for graceful shutdown
            local count=0
            while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo "Force killing camera $cam_id..."
                kill -KILL $pid
            fi
            
            rm -f $pid_file
            echo "Camera $cam_id stopped"
        else
            echo "Camera $cam_id was not running"
            rm -f $pid_file
        fi
    else
        echo "No PID file found for camera $cam_id"
    fi
}

# Stop all rule_engine processes
echo "Stopping all rule_engine processes..."
pkill -f "rule_engine.py"

# Clean up any remaining processes
sleep 2
pkill -9 -f "rule_engine.py" 2>/dev/null

# Clean up PID files
if [ -d "$LOG_DIR" ]; then
    rm -f $LOG_DIR/camera_*.pid
    echo "Cleaned up PID files"
fi

echo "=========================================="
echo "All camera control processes stopped"
echo "=========================================="

