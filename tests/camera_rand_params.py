import numpy as np
import time
import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, List, Union
from datetime import datetime
import json
import random

# Constants
USERNAME = 'admin'
PASSWORD = 'media99zz'
ATTEMPTS_SET_CGI = 10
SLEEP_TIME_FOR_CGI = 0.5
SLEEP_TIME_FOR_ERROR = 3
TIMEOUT_CGI = 2
VENUE_NUMBER = 15 # Grotta
INDEX_CAM_PARAMS = {"ExposureIris":None, 
                    "ExposureGain":None,
                    "DigitalBrightLevel":None,
                    "ExposureExposureTime":None,
                    "ColorSaturation":None}
ARGMAX_CAM_PARAMS = {"ExposureIris":None, 
                     "ExposureGain":None,
                     "DigitalBrightLevel":None,
                     "ExposureExposureTime":None,
                     "ColorSaturation":None}
MAX_LENGTH_CAM_PARAMS = {"ExposureIris":4,
                         "ExposureGain":8,
                         "DigitalBrightLevel":4,
                         "ExposureExposureTime":4,
                         "ColorSaturation":9}

def load_cam_params_range():
    with open('cam_params_range.json', 'r') as f:
        data = json.load(f)
        return {k: v for k, v in data['imaging'].items() if k in [
                "ExposureIris", "ExposureGain","DigitalBrightLevel",
            "ExposureExposureTime", "ColorSaturation"              
        ]}

def randomize_camera_params(cam_id):
    # Load camera parameters range from JSON
    cam_param_range_dict = load_cam_params_range()
    # Randomize parameters
    camera_params_string_to_set = "&".join(f"{k}={random.choice(v)}" for k, v in cam_param_range_dict.items())
    # Apply parameters
    return multi_set_attempt(cam_id, VENUE_NUMBER, USERNAME, PASSWORD, camera_params_string_to_set)

def set_camera_params(cam_id, VENUE_NUMBER, USERNAME, PASSWORD, camera_params_to_set):
    VENUE_NUMBER += 54
    url = f'http://192.168.{VENUE_NUMBER}.5{cam_id}/command/imaging.cgi?{camera_params_to_set}'
    print(f"Sending request to: {url}")
    try:
        response = requests.post(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=TIMEOUT_CGI)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error setting camera params: {e}")
        return None

def multi_set_attempt(cam_id, VENUE_NUMBER, USERNAME, PASSWORD, camera_params_to_set):
    global INDEX_CAM_PARAMS
    for attempt in range(ATTEMPTS_SET_CGI):
        response = set_camera_params(cam_id, VENUE_NUMBER, USERNAME, PASSWORD, camera_params_to_set)
        if response == 200:
            print(f"Successfully set camera parameters on attempt {attempt + 1}")
            result = parse_data(camera_params_to_set)
            cam_param_range_dict = load_cam_params_range()
            for key, value in result.items():
                IND = cam_param_range_dict[key].index(int(value))
                INDEX_CAM_PARAMS[key] = IND
            return True, response
        else:
            print(f"Failed to set camera parameters on attempt {attempt + 1}. Status code: {response}. Retrying...")
    print(f"Failed to set camera parameters after {ATTEMPTS_SET_CGI} attempts")
    return False, response

def parse_data(camera_params_to_set):
    # This function assumes a format of 'key=value&key=value...' and returns a dictionary
    return dict(item.split("=") for item in camera_params_to_set.split("&"))

def main():
    cam_id = 1  # Replace with your camera ID
    success, response = randomize_camera_params(cam_id)

    if success:
        print("Randomized camera parameters were set successfully.")
    else:
        print(f"Failed to set randomized camera parameters. Response code: {response}")

if __name__ == "__main__":
    main()
