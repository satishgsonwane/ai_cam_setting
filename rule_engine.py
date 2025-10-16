import subprocess as sp
import asyncio
import nats
import json
import argparse
from utils import *
from roi_detection import ROIDetector
from camera_protocol import ProtocolFactory

#venue_number = PORT

async def run(cam_id, venue_number):
    """
    Main camera control loop with enhanced features.
    
    Args:
        cam_id: Camera ID (1-6)
        venue_number: Venue number (1-15)
    """
    # Load configuration
    with open('camera_control_config.json', 'r') as f:
        config = json.load(f)
    
    # Determine if this is the master camera
    master_cam_id = config.get('master_camera', {}).get('cam_id', 1)
    is_master = (cam_id == master_cam_id)
    
    # Initialize components
    roi_detector = ROIDetector()
    protocol = ProtocolFactory.create_protocol_from_config()
    adjuster = CameraSettingsAdjuster(acceptable_ranges)
    
    # Connect to NATS
    nc = await nats.connect(servers=["nats://localhost:4222"])
    
    # Initialize video pipe
    command = [ "/home/ozer/venue_video_router/cushm2rawvideo/cushm2pipe", 
        f"/camera{int(cam_id)}", 
        "-scale", 
        "1920x1080", 
        "-rgb" ]
    
    try:
        pipe = sp.Popen(command, stdout = sp.PIPE, bufsize=BUFFER_SIZE)
        print(f"Pipe opened successfully for camera {cam_id}")
        if is_master:
            print(f"Camera {cam_id} is configured as MASTER camera")
    except Exception as e:
        print("Error opening pipe:", e)
        return
    
    # Connect protocol
    if not protocol.connect():
        print("Failed to connect camera protocol")
        return
    
    print(f"Camera {cam_id} control loop started")
    
    while True:
        raw_image = pipe.stdout.read(FRAME_SIZE)
        if len(raw_image) < FRAME_SIZE:
            print("End of stream or error.")
            break

        # Process frame
        imageBGR, imageRGB = process_frame(raw_image)
        imageBGR = crop_lower_third_of_image(imageBGR)
        
        # Calculate image features with ROI filtering
        image_features = calculate_image_metrics(imageBGR, roi_detector)
        
        # Publishing image features over NATS
        data_to_publish = image_features
        message = json.dumps(data_to_publish)
        await nc.publish(f"image_features.camera{int(cam_id)}", message.encode())
        
        # Master camera publishes target features for slave synchronization
        if is_master:
            # Use master's acceptable ranges as target features for slaves
            target_features = {}
            for feature, range_values in acceptable_ranges.items():
                # Use midpoint of acceptable range as target
                target_features[feature] = (range_values[0] + range_values[1]) / 2
            
            target_message = json.dumps(target_features)
            await nc.publish("features.target", target_message.encode())
            print(f"Master camera {cam_id} published target features")

        # Get current camera parameters
        config_dict = get_camera_params(cam_id, venue_number, protocol)
        
        if config_dict is not None:
            # Use CameraSettingsAdjuster to determine necessary adjustments
            camera_params_to_set = adjuster.process_camera_frame(config_dict, image_features)
            
            if camera_params_to_set:
                # Attempt to set the new camera parameters
                success = multi_set_attempt(cam_id, venue_number, USERNAME, PASSWORD, camera_params_to_set, protocol)
                
                if success:
                    print(f"Successfully updated camera parameters: {camera_params_to_set}")
                else:
                    print("Failed to update camera parameters")
        else:
            print("Failed to get current camera parameters")

        await asyncio.sleep(SLEEP_TIME_IN_SEC)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--cam_id", help="Camera ID 1-6")
    parser.add_argument("--venue_number", help="Venue number 1-15", default=15)
    args = parser.parse_args()
    cam_id = int(args.cam_id)
    venue_number = int(args.venue_number)
    if (cam_id in [1,2,3,4,5,6]):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(cam_id, venue_number))
    else:
        print("Invalid camera ID or venue number")
        exit(-1)
