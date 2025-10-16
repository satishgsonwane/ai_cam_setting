"""
ROI Detection Module for Smart Camera Control System

This module provides robust region-of-interest detection for camera analysis,
including green pitch mask generation for football field analysis.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
import json


class ROIDetector:
    """
    Region of Interest detector with green pitch mask capabilities.
    """
    
    def __init__(self, config_file: str = "camera_control_config.json"):
        """
        Initialize ROI detector with configuration.
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self._load_config(config_file)
        self.roi_config = self.config.get('roi_detection', {})
        self.use_green_mask = self.roi_config.get('use_green_mask', False)
        
        # Green HSV range for pitch detection
        self.green_hsv_lower = np.array(self.roi_config.get('green_hsv_range', {}).get('lower', [35, 40, 40]))
        self.green_hsv_upper = np.array(self.roi_config.get('green_hsv_range', {}).get('upper', [85, 255, 255]))
        
        # Morphological operation parameters
        morph_config = self.roi_config.get('morphology', {})
        kernel_size = morph_config.get('kernel_size', 5)
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        self.morph_iterations = morph_config.get('iterations', 2)
        
        # Statistics for debugging
        self.mask_stats = {
            'total_pixels': 0,
            'masked_pixels': 0,
            'mask_percentage': 0.0,
            'last_update': 0
        }
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def get_pitch_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Generate a binary mask for green pitch areas.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Binary mask where 1 indicates pitch pixels
        """
        # Convert BGR to HSV
        hsv_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        
        # Create mask for green pitch
        mask = cv2.inRange(hsv_image, self.green_hsv_lower, self.green_hsv_upper)
        
        # Apply morphological operations to clean noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.morph_kernel, iterations=self.morph_iterations)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.morph_kernel, iterations=self.morph_iterations)
        
        # Update statistics
        self._update_mask_stats(mask)
        
        return mask
    
    def _update_mask_stats(self, mask: np.ndarray):
        """Update mask statistics for debugging."""
        total_pixels = mask.shape[0] * mask.shape[1]
        masked_pixels = np.sum(mask > 0)
        mask_percentage = (masked_pixels / total_pixels) * 100 if total_pixels > 0 else 0
        
        self.mask_stats.update({
            'total_pixels': total_pixels,
            'masked_pixels': masked_pixels,
            'mask_percentage': mask_percentage,
            'last_update': cv2.getTickCount()
        })
    
    def apply_roi_mask(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Apply ROI mask to image for analysis.
        
        Args:
            image_bgr: Input image in BGR format
            mask: Binary mask
            
        Returns:
            Masked image where non-mask pixels are set to black
        """
        # Create 3-channel mask
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        # Apply mask
        masked_image = cv2.bitwise_and(image_bgr, mask_3channel)
        
        return masked_image
    
    def get_roi_image(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get ROI image with optional green mask filtering.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Tuple of (roi_image, mask) where mask is None if not using green mask
        """
        if self.use_green_mask:
            mask = self.get_pitch_mask(image_bgr)
            
            # Check if mask has sufficient coverage
            if self.mask_stats['mask_percentage'] < 5.0:  # Less than 5% coverage
                print(f"Warning: Green mask coverage only {self.mask_stats['mask_percentage']:.1f}%, using full image")
                return image_bgr, None
            
            roi_image = self.apply_roi_mask(image_bgr, mask)
            return roi_image, mask
        else:
            return image_bgr, None
    
    def get_mask_coverage_percentage(self) -> float:
        """Get the percentage of image covered by the mask."""
        return self.mask_stats['mask_percentage']
    
    def is_mask_valid(self, min_coverage_percentage: float = 5.0) -> bool:
        """
        Check if the current mask has sufficient coverage.
        
        Args:
            min_coverage_percentage: Minimum coverage percentage to consider valid
            
        Returns:
            True if mask has sufficient coverage
        """
        return self.mask_stats['mask_percentage'] >= min_coverage_percentage
    
    def visualize_mask(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Create visualization of mask overlay on image.
        
        Args:
            image_bgr: Original image
            mask: Binary mask
            
        Returns:
            Image with mask overlay for debugging
        """
        # Create colored mask
        colored_mask = np.zeros_like(image_bgr)
        colored_mask[mask > 0] = [0, 255, 0]  # Green overlay
        
        # Blend with original image
        alpha = 0.3
        overlay = cv2.addWeighted(image_bgr, 1 - alpha, colored_mask, alpha, 0)
        
        # Add text with coverage percentage
        coverage_text = f"Coverage: {self.mask_stats['mask_percentage']:.1f}%"
        cv2.putText(overlay, coverage_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return overlay
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update ROI detection configuration.
        
        Args:
            new_config: New configuration parameters
        """
        self.roi_config.update(new_config)
        
        # Update HSV range if provided
        if 'green_hsv_range' in new_config:
            hsv_range = new_config['green_hsv_range']
            if 'lower' in hsv_range:
                self.green_hsv_lower = np.array(hsv_range['lower'])
            if 'upper' in hsv_range:
                self.green_hsv_upper = np.array(hsv_range['upper'])
        
        # Update morphological parameters if provided
        if 'morphology' in new_config:
            morph_config = new_config['morphology']
            if 'kernel_size' in morph_config:
                kernel_size = morph_config['kernel_size']
                self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            if 'iterations' in morph_config:
                self.morph_iterations = morph_config['iterations']
        
        # Update green mask usage
        if 'use_green_mask' in new_config:
            self.use_green_mask = new_config['use_green_mask']


def crop_lower_third_of_image(image: np.ndarray) -> np.ndarray:
    """
    Crop the lower third of the image (existing function for compatibility).
    
    Args:
        image: Input image
        
    Returns:
        Cropped image containing lower third
    """
    height, _, _ = image.shape
    cropped_image = image[(2*height)//3 : height, :]
    return cropped_image


def create_roi_detector(config_file: str = "camera_control_config.json") -> ROIDetector:
    """
    Factory function to create ROI detector instance.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        ROIDetector instance
    """
    return ROIDetector(config_file)
