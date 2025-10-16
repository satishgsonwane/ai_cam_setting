"""
ROI Detection and Image Processing

Provides region of interest detection and image processing utilities.
"""

from .roi_detection import ROIDetector, crop_lower_third_of_image

__all__ = ['ROIDetector', 'crop_lower_third_of_image']
