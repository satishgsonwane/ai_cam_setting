#!/bin/bash

# Smart Camera Control System - Deployment Script
# This script deploys the enhanced camera control system to the venue

VENUE_NUMBER=15  # Grotta venue
VENUE_USER="ozer"  # Adjust this to your venue username
VENUE_HOST="192.168.69.1"  # Adjust this to your venue IP

echo "=========================================="
echo "Smart Camera Control System Deployment"
echo "=========================================="

# Check if we're already on the venue system
if [[ $(hostname) == *"venue"* ]] || [[ $(pwd) == *"/home/ozer"* ]]; then
    echo "Already on venue system. Starting deployment..."
    DEPLOY_LOCAL=true
else
    echo "Deploying to venue system via SSH..."
    DEPLOY_LOCAL=false
fi

if [ "$DEPLOY_LOCAL" = false ]; then
    echo "Copying files to venue system..."
    
    # Create remote directory if it doesn't exist
    ssh $VENUE_USER@$VENUE_HOST "mkdir -p /home/$VENUE_USER/ai_cam_settings"
    
    # Copy all Python files and configs
    scp *.py *.json $VENUE_USER@$VENUE_HOST:/home/$VENUE_USER/ai_cam_settings/
    
    # Copy shell scripts
    scp setrunall.sh setstopall.sh $VENUE_USER@$VENUE_HOST:/home/$VENUE_USER/ai_cam_settings/
    
    echo "Files copied successfully!"
    echo "Connecting to venue system..."
    
    # SSH into venue and run deployment
    ssh $VENUE_USER@$VENUE_HOST << 'EOF'
        cd /home/ozer/ai_cam_settings
        
        echo "Setting up Python environment..."
        python3 -m pip install --user nats-py opencv-python requests
        
        echo "Testing system..."
        python3 test_system.py
        
        echo "Deployment complete! Ready to run cameras."
        echo "To start all cameras: ./setrunall.sh"
        echo "To stop all cameras: ./setstopall.sh"
        echo "To run single camera: python3 rule_engine.py --cam_id 1 --venue_number 15"
EOF

else
    echo "Setting up Python environment..."
    python3 -m pip install --user nats-py opencv-python requests
    
    echo "Testing system..."
    python3 test_system.py
    
    echo "Deployment complete! Ready to run cameras."
    echo "To start all cameras: ./setrunall.sh"
    echo "To stop all cameras: ./setstopall.sh"
    echo "To run single camera: python3 rule_engine.py --cam_id 1 --venue_number 15"
fi

echo "=========================================="
echo "Deployment Summary:"
echo "• Enhanced cost-based parameter selection"
echo "• Hysteresis to prevent oscillation"
echo "• Protocol abstraction (CGI/VISCA ready)"
echo "• ROI detection with green mask filtering"
echo "• Master camera (cam_id=1) for multi-cam sync"
echo "=========================================="
