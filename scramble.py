import requests
from requests.auth import HTTPDigestAuth
import time
import argparse
from utils import *

# def scramble_camera_params(cam_id, venue_number, USERNAME, PASSWORD):
#     venue_number += 54
#     scrambled_params = "ExposureIris=0&WhiteBalanceMode=outdoor&ColorMatrixEnable=off&DetailLevel=0&DigitalBrightLevel=0"
#     scrambled_url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{scrambled_params}'
#     print(scrambled_url)
#     for attempt in range(ATTEMPTS_SET_CGI):
#         try:
#             scrambled_response = requests.post(scrambled_url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=TIMEOUT_CGI)
#             if scrambled_response.status_code == 200:
#                 print(f"******Successfully set initial parameters on attempt {attempt + 1} ******")
#                 return True
#             else:
#                 print(f"Failed to set initial parameters on attempt {attempt + 1}. Status code: {scrambled_response.status_code}")
#         except requests.exceptions.RequestException as e:
#             print(f"Error setting initial camera params on attempt {attempt + 1}: {e}")
        
#         time.sleep(SLEEP_TIME_FOR_CGI)
    
#     print(f"Failed to set Scrambled parameters after {ATTEMPTS_SET_CGI} attempts")
#     return False

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scramble camera parameters.")
    parser.add_argument("--cam_id", type=int, nargs='+', choices=[1, 2, 3, 4, 5, 6], required=True, help="Camera ID(s) (1-6)")
    parser.add_argument("--venue_number", type=int, choices=range(1, 16), required=True, help="Venue number (1-15)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    success_count = 0
    for cam_id in args.cam_id:
        result = scramble_camera_params(cam_id, args.venue_number, USERNAME, PASSWORD)
        if result:
            success_count += 1
            print(f"Camera {cam_id} parameters successfully scrambled.")
        else:
            print(f"Failed to scramble camera {cam_id} parameters.")
    
    print(f"\nScrambled {success_count} out of {len(args.cam_id)} cameras.")