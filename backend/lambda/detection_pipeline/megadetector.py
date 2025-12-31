"""
MegaDetector v5.0 Integration
YOLOv5-based model for detecting animals, people, and vehicles in camera trap images

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

import torch
import numpy as np
from PIL import Image
import io
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger()


class MegaDetector:
    """Wrapper for MegaDetector v5.0 model"""

    # Category mapping
    CATEGORIES = {
        1: 'animal',
        2: 'person',
        3: 'vehicle'
    }

    def __init__(self, model_path: str, confidence_threshold: float = 0.6, device: str = None):
        """
        Initialize MegaDetector model

        Args:
            model_path: Path to MegaDetector PyTorch model file
            confidence_threshold: Minimum confidence score for detections
            device: Device to run inference on (cuda/cpu). Auto-detect if None.
        """
        self.confidence_threshold = confidence_threshold

        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        logger.info(f"Loading MegaDetector model from {model_path}")
        logger.info(f"Using device: {self.device}")

        try:
            # Load YOLOv5 model
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
            self.model.to(self.device)
            self.model.conf = confidence_threshold
            self.model.eval()

            logger.info("MegaDetector model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load MegaDetector model: {str(e)}")
            raise

    def detect(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Detect animals, people, and vehicles in image

        Args:
            image_bytes: Image file as bytes

        Returns:
            List of detections, each containing:
                - category: 'animal', 'person', or 'vehicle'
                - confidence: Detection confidence score (0-1)
                - bbox: Bounding box as [x, y, width, height] in normalized coordinates (0-1)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_width, img_height = image.size

            # Run inference
            with torch.no_grad():
                results = self.model(image)

            # Parse results
            detections = []
            predictions = results.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2, conf, class]

            for pred in predictions:
                x1, y1, x2, y2, conf, cls = pred

                # Convert to normalized coordinates
                x = x1 / img_width
                y = y1 / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height

                # Get category name
                category_id = int(cls) + 1  # MegaDetector uses 1-indexed classes
                category = self.CATEGORIES.get(category_id, 'unknown')

                detections.append({
                    'category': category,
                    'confidence': float(conf),
                    'bbox': [float(x), float(y), float(width), float(height)]
                })

            logger.info(f"MegaDetector found {len(detections)} detections above threshold {self.confidence_threshold}")

            return detections

        except Exception as e:
            logger.error(f"Error running MegaDetector: {str(e)}", exc_info=True)
            raise

    def crop_detection(self, image_bytes: bytes, bbox: List[float]) -> bytes:
        """
        Crop image to bounding box for species classification

        Args:
            image_bytes: Original image as bytes
            bbox: Bounding box as [x, y, width, height] in normalized coordinates (0-1)

        Returns:
            Cropped image as bytes
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_width, img_height = image.size

            # Convert normalized coordinates to pixels
            x = int(bbox[0] * img_width)
            y = int(bbox[1] * img_height)
            width = int(bbox[2] * img_width)
            height = int(bbox[3] * img_height)

            # Add padding (10% on each side)
            padding = 0.1
            pad_x = int(width * padding)
            pad_y = int(height * padding)

            # Calculate crop coordinates with padding
            left = max(0, x - pad_x)
            top = max(0, y - pad_y)
            right = min(img_width, x + width + pad_x)
            bottom = min(img_height, y + height + pad_y)

            # Crop image
            cropped = image.crop((left, top, right, bottom))

            # Convert back to bytes
            buffer = io.BytesIO()
            cropped.save(buffer, format='JPEG', quality=95)
            buffer.seek(0)

            return buffer.read()

        except Exception as e:
            logger.error(f"Error cropping detection: {str(e)}", exc_info=True)
            raise

    def visualize_detections(
        self,
        image_bytes: bytes,
        detections: List[Dict[str, Any]],
        output_path: str = None
    ) -> bytes:
        """
        Visualize detections on image with bounding boxes

        Args:
            image_bytes: Original image as bytes
            detections: List of detections from detect()
            output_path: Optional path to save image

        Returns:
            Image with bounding boxes as bytes
        """
        from PIL import ImageDraw, ImageFont

        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            draw = ImageDraw.Draw(image)
            img_width, img_height = image.size

            # Define colors for each category
            colors = {
                'animal': (0, 255, 0),      # Green
                'person': (255, 0, 0),      # Red
                'vehicle': (0, 0, 255)      # Blue
            }

            for detection in detections:
                category = detection['category']
                confidence = detection['confidence']
                bbox = detection['bbox']

                # Convert normalized coordinates to pixels
                x = int(bbox[0] * img_width)
                y = int(bbox[1] * img_height)
                width = int(bbox[2] * img_width)
                height = int(bbox[3] * img_height)

                # Draw bounding box
                color = colors.get(category, (255, 255, 255))
                draw.rectangle(
                    [(x, y), (x + width, y + height)],
                    outline=color,
                    width=3
                )

                # Draw label
                label = f"{category} {confidence:.2f}"
                draw.text((x, y - 20), label, fill=color)

            # Save if output path provided
            if output_path:
                image.save(output_path)

            # Convert to bytes
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            buffer.seek(0)

            return buffer.read()

        except Exception as e:
            logger.error(f"Error visualizing detections: {str(e)}", exc_info=True)
            raise

    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = threshold
        self.model.conf = threshold
        logger.info(f"Updated confidence threshold to {threshold}")
