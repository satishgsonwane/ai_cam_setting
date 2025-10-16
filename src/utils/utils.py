import cv2
import numpy as np
import time
import json
import requests
from requests.auth import HTTPDigestAuth
import re
from typing import Dict, List, Union, Tuple
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
import os
import sys

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cost.cost_functions import CostFunctionCalculator
from protocols.camera_protocol import ProtocolFactory
from detection.roi_detection import ROIDetector, crop_lower_third_of_image

# Load configuration from JSON file
try:
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_settings_features_config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)
except FileNotFoundError:
    # Use default configuration if file doesn't exist
    config = {
        'image_features': {
            'brightness': [50, 200],
            'blur': [0, 1000],
            'saturation': [50, 200],
            'white_balance': [0.8, 1.2],
            'crop_size': [360, 1920]
        }
    }

# Extract constants from JSON
features = config['image_features']
brightness_min, brightness_max = features['brightness']
blur_min, blur_max = features['blur']
saturation_min, saturation_max = features['saturation']
wb_min,wb_max = features['white_balance']
crop_height, crop_width = features['crop_size']

# Load venue configuration
try:
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
    with open(config_path, 'r') as file:
        control_config = json.load(file)
        PORT = control_config.get('network', {}).get('venue_number', 15)
except FileNotFoundError:
    PORT = 15  # Default venue number

initial_params_set = False  # Flag to track if initial params are set

FFMPEG_BIN = "ffmpeg"
H_buff, W_buff = 1080, 1920
FRAME_SIZE = H_buff * W_buff * 3  # Size of one frame in bytes
BUFFER_SIZE = FRAME_SIZE * 1  # Buffer for 1 frame
DECIMAL_PLACE = 3
SLEEP_TIME_IN_SEC = 1
FOLDER_PATH = "/home/ozer/AI/jsons_cam_settings"
USERNAME = 'admin'
PASSWORD = 'media99zz'
ATTEMPTS_SET_CGI = 50
SLEEP_TIME_FOR_CGI = 1
TIMEOUT_CGI = 2

acceptable_ranges = {
    #'normalized_brightness': [0.245, 0.326],
    'normalized_brightness': [0.5, 0.7], #IR
    #'normalized_contrast': [0.129, 0.216],
    #'normalized_blur': [0, 0.9], 
    #'normalized_saturation': [0.578, 0.721],
    'normalized_saturation': [0.4,0.7], #IR
    #'normalized_dynamic_range': [0.92, 1.0]
    #'normalized_wb' : [0.8,1.2]
}

def save_to_json(camera_settings, image_features, output_filename):
    template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'template.json')
    try:
        with open(template_path, 'r') as f:
            template = json.load(f)
    except FileNotFoundError:
        # Create a basic template if it doesn't exist
        template = {
            "camera_settings": {},
            "image_features": {}
        }

    template["camera_settings"].update(camera_settings)
    template["image_features"].update(image_features)

    with open(output_filename, 'w') as f:
        json.dump(template, f, indent=4)

def process_frame(raw_image):
    image = np.frombuffer(raw_image, dtype='uint8')
    imageBGR = image.reshape((H_buff,W_buff,3))
    imageRGB = cv2.cvtColor(imageBGR,cv2.COLOR_BGR2RGB)
    return imageBGR,imageRGB

# Function to compute sharpness and blur
def compute_sharpness_and_blur(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_image, cv2.CV_64F).var()
    return laplacian_var, laplacian_var  # Using laplacian_var for both sharpness and blur for simplicity

# Function to normalize a metric to a 0-1 range
def normalize_metric(value, min_value, max_value):
    return (value - min_value) / (max_value - min_value)

def normalize_white_balance(image: np.ndarray) -> float:
    """
    Normalize the white balance of an image and return the normalized white balance value.
    :param image: Input image in BGR format.
    :return: Normalized white balance value.
    """
    # Convert image to float32 for precision in calculations
    image = image.astype(np.float32)
    
    # Calculate the mean for each channel
    mean_b = np.mean(image[:, :, 0])
    mean_g = np.mean(image[:, :, 1])
    mean_r = np.mean(image[:, :, 2])
    
    # Calculate the overall mean
    mean_gray = (mean_b + mean_g + mean_r) / 3
    
    # Scale factors to normalize white balance
    scale_b = mean_gray / mean_b
    scale_g = mean_gray / mean_g
    scale_r = mean_gray / mean_r
    
    # Normalize each channel
    image[:, :, 0] *= scale_b
    image[:, :, 1] *= scale_g
    image[:, :, 2] *= scale_r
        
    # Calculate the normalized white balance value
    white_balance_value = (scale_b + scale_g + scale_r) / 6
    
    return white_balance_value

def calculate_image_metrics(image, roi_detector: ROIDetector = None):
    """
    Calculate image metrics with optional ROI filtering.
    
    Args:
        image: Input image in BGR format
        roi_detector: Optional ROI detector for green mask filtering
        
    Returns:
        Dictionary of calculated image metrics
    """
    if image.shape[:2] != (crop_height, crop_width):
        image = cv2.resize(image, (crop_width, crop_height))
    
    # Apply ROI filtering if detector is provided
    analysis_image = image
    mask_coverage = 100.0  # Default to full coverage
    
    if roi_detector is not None:
        analysis_image, mask = roi_detector.get_roi_image(image)
        if mask is not None:
            mask_coverage = roi_detector.get_mask_coverage_percentage()
            print(f"Using green mask with {mask_coverage:.1f}% coverage")
        else:
            print("Green mask insufficient coverage, using full image")
    
    # Convert to grayscale
    gray_image = cv2.cvtColor(analysis_image, cv2.COLOR_BGR2GRAY)
    
    # Brightness (mean pixel intensity)
    brightness = np.mean(gray_image)
    normalized_brightness = normalize_metric(brightness, brightness_min, brightness_max)
    
    # Contrast (standard deviation of pixel values)
    #contrast = np.std(gray_image)
    #normalized_contrast = normalize_metric(contrast, contrast_min, contrast_max)
    
    # Compute sharpness and blur
    sharpness, blur = compute_sharpness_and_blur(analysis_image)
    #normalized_sharpness = normalize_metric(sharpness, sharpness_min, sharpness_max)
    normalized_blur = normalize_metric(blur, blur_min, blur_max)
    
    # Saturation (mean saturation in HSV color space)
    hsv_image = cv2.cvtColor(analysis_image, cv2.COLOR_BGR2HSV)
    saturation = np.mean(hsv_image[:, :, 1])
    normalized_saturation = normalize_metric(saturation, saturation_min, saturation_max)

    # White Balance
    #normalized_wb = normalize_white_balance(image)
    #normalized_wb = normalize_metric (wb, wb_min,wb_max)
    
    # Exposure (similar to brightness in this context)
    # exposure_metric = brightness
    # normalized_exposure = normalized_brightness
    
    # Dynamic Range (difference between max and min pixel values)
    # dynamic_range = np.max(gray_image) - np.min(gray_image)
    # normalized_dynamic_range = normalize_metric(dynamic_range, dynamic_range_min, dynamic_range_max)
    
    # Histogram (normalized histogram of grayscale image with fixed bins)
    # hist = cv2.calcHist([gray_image], [0], None, [nbins], [0, 256])
    # hist = cv2.normalize(hist, hist).flatten()
    
    # Noise (standard deviation of pixel intensities)
    # noise = np.std(gray_image)
    # normalized_noise = normalize_metric(noise, noise_min, noise_max)
    
    metrics = {
        'brightness': float(round(brightness,DECIMAL_PLACE)),
        'normalized_brightness': float(round(normalized_brightness,DECIMAL_PLACE)),
        #'contrast': float(round(contrast,DECIMAL_PLACE)),
        #'normalized_contrast': float(round(normalized_contrast,DECIMAL_PLACE)),
        #'normalized_wb': float(round(normalized_wb,DECIMAL_PLACE)),
        'blur': float(round(blur,DECIMAL_PLACE)),
        'normalized_blur': float(round(normalized_blur,DECIMAL_PLACE)),
        'saturation': float(round(saturation,DECIMAL_PLACE)),
        'normalized_saturation': float(round(normalized_saturation,DECIMAL_PLACE)),
        'mask_coverage': float(round(mask_coverage,DECIMAL_PLACE)),
    }    
    return metrics

def crop_lower_third_of_image(image):
    height, _, _ = image.shape
    image = image[(2*height)//3 : height, :]
    return image

def set_initial_camera_params(cam_id, venue_number, USERNAME, PASSWORD):
    global initial_params_set
    if initial_params_set:
        return True
    venue_number += 54
    initial_params = "ExposureMode=manual&ExposureIris=11&ExposureGain=3&ExposureExposureTime=10&GammaLevel=0&WhiteBalanceMode=atw&ColorMatrixEnable=on&WhiteBalanceCbGain=54&WhiteBalanceCrGain=54&ColorHue=7&DetailLevel=7"
    initial_url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{initial_params}'
    
    for attempt in range(ATTEMPTS_SET_CGI):
        try:
            initial_response = requests.post(initial_url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=TIMEOUT_CGI)
            if initial_response.status_code == 200:
                print(f"******Successfully set initial parameters on attempt {attempt + 1} ******")
                initial_params_set = True
                return True
            else:
                print(f"Failed to set initial parameters on attempt {attempt + 1}. Status code: {initial_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error setting initial camera params on attempt {attempt + 1}: {e}")
        
        time.sleep(SLEEP_TIME_FOR_CGI)
    
    print(f"Failed to set initial parameters after {ATTEMPTS_SET_CGI} attempts")
    return False

def scramble_camera_params(cam_id, venue_number, USERNAME, PASSWORD):
    venue_number += 54
    scrambled_params = "ExposureIris=0&WhiteBalanceMode=outdoor&ColorMatrixEnable=off&DetailLevel=0&DigitalBrightLevel=0"
    scrambled_url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{scrambled_params}'
    print(scrambled_url)
    for attempt in range(ATTEMPTS_SET_CGI):
        try:
            scrambled_response = requests.post(scrambled_url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=TIMEOUT_CGI)
            if scrambled_response.status_code == 200:
                print(f"******Successfully set initial parameters on attempt {attempt + 1} ******")
                return True
            else:
                print(f"Failed to set initial parameters on attempt {attempt + 1}. Status code: {scrambled_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error setting initial camera params on attempt {attempt + 1}: {e}")
        
        time.sleep(SLEEP_TIME_FOR_CGI)
    
    print(f"Failed to set Scrambled parameters after {ATTEMPTS_SET_CGI} attempts")
    return False

def set_camera_params(cam_id, venue_number, USERNAME, PASSWORD, camera_params_to_set):
    venue_number += 54
    url = f'http://192.168.{venue_number}.5{cam_id}/command/imaging.cgi?{camera_params_to_set}'
    print(f"Sending request to: {url}")
    try:
        response = requests.post(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=TIMEOUT_CGI)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error setting camera params: {e}")
        return None

def multi_set_attempt(cam_id, venue_number, USERNAME, PASSWORD, camera_params_to_set, protocol=None):
    """
    Set camera parameters with multiple attempts using protocol abstraction.
    
    Args:
        cam_id: Camera ID (1-6)
        venue_number: Venue number (1-15)
        USERNAME: Camera username (for compatibility)
        PASSWORD: Camera password (for compatibility)
        camera_params_to_set: Parameter string or dictionary
        protocol: Camera protocol instance (if None, creates from config)
        
    Returns:
        True if successful, False otherwise
    """
    global initial_params_set
    
    if protocol is None:
        protocol = ProtocolFactory.create_protocol_from_config()
    
    if not protocol.is_connected():
        protocol.connect()
    
    # First, set initial parameters if not set
    if not initial_params_set:
        if not set_initial_camera_params(cam_id, venue_number, USERNAME, PASSWORD):
            print("Failed to set initial parameters. Aborting further attempts.")
            return False

    # Parse parameter string to dictionary if needed
    if isinstance(camera_params_to_set, str):
        params_dict = dict(item.split("=") for item in camera_params_to_set.split("&") if "=" in item)
    else:
        params_dict = camera_params_to_set
    
    # Set parameters using protocol
    return protocol.set_camera_params(cam_id, venue_number, params_dict)

def get_camera_params(cam_id, venue_number, protocol=None):
    """
    Get camera parameters using protocol abstraction.
    
    Args:
        cam_id: Camera ID (1-6)
        venue_number: Venue number (1-15)
        protocol: Camera protocol instance (if None, creates from config)
        
    Returns:
        Dictionary of camera parameters or None if failed
    """
    if protocol is None:
        protocol = ProtocolFactory.create_protocol_from_config()
    
    if not protocol.is_connected():
        protocol.connect()
    
    return protocol.get_camera_params(cam_id, venue_number)

class CameraSettingsAdjuster:
    """
    Advanced camera settings adjuster using cost-based intelligent parameter selection
    with hysteresis to prevent oscillation.
    """
    
    def __init__(self, acceptable_ranges: Dict[str, List[float]], config_file: str = None):
        """
        Initialize the camera settings adjuster.
        
        Args:
            acceptable_ranges: Dictionary mapping feature names to [min, max] acceptable ranges
            config_file: Path to configuration file for cost weights and hysteresis
        """
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'camera_control_config.json')
        
        self.acceptable_ranges = acceptable_ranges
        self.adjustment_rules = self._initialize_adjustment_rules()
        self.cam_params_range = self._load_cam_params_range()
        self.cost_calculator = CostFunctionCalculator(config_file)
        
        # Track adjustment history for debugging
        self.adjustment_history = []

    def _initialize_adjustment_rules(self):
        """Initialize rules mapping features to adjustable parameters."""
        return {
            'normalized_brightness': ['ExposureIris', 'ExposureExposureTime', 'ExposureGain', 'DigitalBrightLevel'],
            'normalized_saturation': ['ColorSaturation']
        }

    def _load_cam_params_range(self):
        """Load camera parameter ranges from JSON file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'cam_params_range.json')
        with open(config_path, 'r') as f:
            data = json.load(f)
            return {k: v for k, v in data['imaging'].items() if k in [
                 "ExposureIris", "ExposureGain","DigitalBrightLevel",
                "ExposureExposureTime", "DetailLevel", "ColorSaturation"              
            ]}

    def _get_next_param_value(self, current_value: Union[int, str], param_list: List[Union[int, str]], increase: bool = True) -> Union[int, str]:
        """
        Get the next parameter value in the specified direction.
        
        Args:
            current_value: Current parameter value
            param_list: List of available parameter values
            increase: Whether to increase (True) or decrease (False) the value
            
        Returns:
            Next parameter value in the specified direction
        """
        try:
            current_index = param_list.index(str(current_value))  # Convert current_value to string for comparison
            if increase and current_index < len(param_list) - 1:
                return param_list[current_index + 1]
            elif not increase and current_index > 0:
                return param_list[current_index - 1]
            else:
                return current_value
        except ValueError:
            # If the current_value is not in the list, find the closest value
            param_list = [int(x) for x in param_list]  # Convert all values to integers
            current_value = int(current_value)
            if increase:
                next_values = [x for x in param_list if x > current_value]
                return str(min(next_values)) if next_values else str(current_value)
            else:
                prev_values = [x for x in param_list if x < current_value]
                return str(max(prev_values)) if prev_values else str(current_value)

    def adjust_camera_settings(self, config_dict: Dict[str, Union[int, str]], image_features: Dict[str, float]) -> Dict[str, Union[int, str]]:
        """
        Intelligently adjust camera settings using cost-based parameter selection.
        
        Args:
            config_dict: Current camera configuration
            image_features: Current image feature metrics
            
        Returns:
            Dictionary of parameter changes to apply
        """
        adjusted_settings = {}
        
        for feature, value in image_features.items():
            if feature in self.acceptable_ranges:
                min_val, max_val = self.acceptable_ranges[feature]
                acceptable_range = (min_val, max_val)
                
                print(f"Checking feature '{feature}': value={value:.3f}, range=({min_val:.3f}, {max_val:.3f})")
                
                # Use hysteresis to determine if adjustment is needed
                should_adjust, reason = self.cost_calculator.should_adjust_feature(
                    feature, value, acceptable_range
                )
                
                if should_adjust:
                    print(f"Adjustment needed for '{feature}': {reason}")
                    
                    # Find the best parameter adjustment using cost function
                    best_param, best_value, best_cost = self.cost_calculator.find_best_adjustment(
                        feature, value, acceptable_range, config_dict, 
                        self.cam_params_range, self.adjustment_rules
                    )
                    
                    if best_param and best_value is not None:
                        current_value = config_dict[best_param]
                        if current_value != best_value:
                            adjusted_settings[best_param] = best_value
                            
                            # Log the adjustment for debugging
                            adjustment_info = {
                                'feature': feature,
                                'feature_value': value,
                                'parameter': best_param,
                                'old_value': current_value,
                                'new_value': best_value,
                                'cost': best_cost,
                                'timestamp': time.time()
                            }
                            self.adjustment_history.append(adjustment_info)
                            
                            print(f"Selected adjustment: {best_param} {current_value} -> {best_value} (cost: {best_cost:.2f})")
                        else:
                            print(f"No change needed for {best_param} (already at optimal value)")
                    else:
                        print(f"No suitable parameter found for adjusting '{feature}'")
                else:
                    print(f"No adjustment needed for '{feature}': {reason}")

        return adjusted_settings

    def generate_camera_params_string(self, settings: Dict[str, Union[int, str]]) -> str:
        """
        Generate camera parameter string for CGI command.
        
        Args:
            settings: Dictionary of parameter changes
            
        Returns:
            Formatted parameter string for CGI command
        """
        if not settings:
            return ""
            
        params = "&".join(f"{k}={v}" for k, v in settings.items())
        return f"{params}&ExposureMode=manual&WhiteBalanceMode=atw"
    
    def process_camera_frame(self, config_dict: Dict[str, Union[int, str]], image_features: Dict[str, float]) -> str:
        """
        Process a camera frame and determine necessary parameter adjustments.
        
        Args:
            config_dict: Current camera configuration
            image_features: Current image feature metrics
            
        Returns:
            Camera parameter string for CGI command
        """
        adjusted_settings = self.adjust_camera_settings(config_dict, image_features)
        return self.generate_camera_params_string(adjusted_settings)
    
    def get_adjustment_history(self) -> List[Dict]:
        """Get the history of parameter adjustments for debugging."""
        return self.adjustment_history.copy()
    
    def clear_adjustment_history(self):
        """Clear the adjustment history."""
        self.adjustment_history.clear()
    