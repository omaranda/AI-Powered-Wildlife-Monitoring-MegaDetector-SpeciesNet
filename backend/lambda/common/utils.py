"""
Utility functions for image processing and metadata extraction

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

from PIL import Image, ExifTags
import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger()


def extract_exif_data(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract EXIF metadata from image

    Args:
        image_bytes: Image file as bytes

    Returns:
        Dictionary with EXIF data including GPS, camera settings, etc.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        exif_data = {
            'width': image.width,
            'height': image.height,
            'format': image.format,
            'mode': image.mode
        }

        # Extract EXIF tags
        exif = image.getexif()

        if exif:
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)

                # Handle specific tags
                if tag_name == 'DateTime':
                    try:
                        exif_data['captured_at'] = datetime.strptime(
                            str(value), '%Y:%m:%d %H:%M:%S'
                        ).isoformat()
                    except:
                        pass

                elif tag_name == 'Make':
                    exif_data['camera_make'] = str(value)

                elif tag_name == 'Model':
                    exif_data['camera_model'] = str(value)

                elif tag_name == 'GPSInfo':
                    gps_data = extract_gps_data(value)
                    if gps_data:
                        exif_data.update(gps_data)

                elif tag_name in ['ExposureTime', 'FNumber', 'ISO', 'FocalLength']:
                    exif_data[tag_name.lower()] = str(value)

        logger.info(f"Extracted EXIF data: {len(exif_data)} fields")
        return exif_data

    except Exception as e:
        logger.error(f"Error extracting EXIF data: {str(e)}")
        return {}


def extract_gps_data(gps_info: Dict) -> Optional[Dict[str, float]]:
    """
    Extract GPS coordinates from EXIF GPS info

    Args:
        gps_info: GPS info dictionary from EXIF

    Returns:
        Dictionary with latitude, longitude, altitude
    """
    try:
        gps_data = {}

        # GPS latitude
        if 1 in gps_info and 2 in gps_info:  # GPSLatitudeRef, GPSLatitude
            lat = convert_to_degrees(gps_info[2])
            if gps_info[1] == 'S':
                lat = -lat
            gps_data['gps_latitude'] = lat

        # GPS longitude
        if 3 in gps_info and 4 in gps_info:  # GPSLongitudeRef, GPSLongitude
            lon = convert_to_degrees(gps_info[4])
            if gps_info[3] == 'W':
                lon = -lon
            gps_data['gps_longitude'] = lon

        # GPS altitude
        if 6 in gps_info:  # GPSAltitude
            altitude = float(gps_info[6])
            if 5 in gps_info and gps_info[5] == 1:  # Below sea level
                altitude = -altitude
            gps_data['gps_altitude'] = altitude

        return gps_data if gps_data else None

    except Exception as e:
        logger.error(f"Error extracting GPS data: {str(e)}")
        return None


def convert_to_degrees(value):
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal degrees

    Args:
        value: Tuple of (degrees, minutes, seconds)

    Returns:
        Decimal degrees
    """
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def calculate_image_quality(image_bytes: bytes) -> Dict[str, float]:
    """
    Calculate image quality metrics

    Args:
        image_bytes: Image file as bytes

    Returns:
        Dictionary with quality scores:
            - brightness: Average pixel brightness (0-1)
            - sharpness: Laplacian variance (higher = sharper)
            - overall: Combined quality score (0-1)
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('L')  # Convert to grayscale
        img_array = np.array(image)

        # Calculate brightness (average pixel value)
        brightness = np.mean(img_array) / 255.0

        # Calculate sharpness using Laplacian variance
        laplacian = np.array([
            [0, 1, 0],
            [1, -4, 1],
            [0, 1, 0]
        ])

        # Convolve image with Laplacian kernel
        from scipy import signal
        lap = signal.convolve2d(img_array, laplacian, mode='same', boundary='symm')
        sharpness = np.var(lap)

        # Normalize sharpness to 0-1 range (typical range is 0-500 for camera trap images)
        sharpness_normalized = min(sharpness / 500.0, 1.0)

        # Calculate overall quality score
        # Penalize very dark or very bright images
        brightness_quality = 1.0 - abs(brightness - 0.5) * 2

        # Combine metrics
        overall = (brightness_quality * 0.3 + sharpness_normalized * 0.7)

        quality = {
            'brightness': round(brightness, 4),
            'sharpness': round(sharpness_normalized, 4),
            'overall': round(overall, 4)
        }

        logger.info(f"Image quality: {quality}")
        return quality

    except Exception as e:
        logger.error(f"Error calculating image quality: {str(e)}")
        return {
            'brightness': 0.5,
            'sharpness': 0.5,
            'overall': 0.5
        }


def resize_image(
    image_bytes: bytes,
    max_width: int = 1920,
    max_height: int = 1080,
    quality: int = 90
) -> bytes:
    """
    Resize image while maintaining aspect ratio

    Args:
        image_bytes: Image file as bytes
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)

    Returns:
        Resized image as bytes
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Calculate new dimensions
        width, height = image.size
        aspect_ratio = width / height

        if width > max_width or height > max_height:
            if aspect_ratio > 1:  # Landscape
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:  # Portrait
                new_height = max_height
                new_width = int(max_height * aspect_ratio)

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)

        return buffer.read()

    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}")
        return image_bytes


def generate_thumbnail(image_bytes: bytes, size: tuple = (300, 300)) -> bytes:
    """
    Generate thumbnail from image

    Args:
        image_bytes: Image file as bytes
        size: Thumbnail size (width, height)

    Returns:
        Thumbnail image as bytes
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail(size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        return buffer.read()

    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        return image_bytes
