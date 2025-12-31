"""
Camera Trap Species Detection Pipeline
Lambda function for processing camera trap images with MegaDetector and SpeciesNet

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

import json
import os
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any
import hashlib

from megadetector import MegaDetector
from speciesnet import SpeciesNet
from database import DatabaseManager
from utils import extract_exif_data, calculate_image_quality

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DB_HOST = os.environ['DB_HOST']
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE_NAME', 'sensor-tracking')
MEGADETECTOR_THRESHOLD = float(os.environ.get('MEGADETECTOR_THRESHOLD', '0.6'))
SPECIESNET_THRESHOLD = float(os.environ.get('SPECIESNET_THRESHOLD', '0.5'))

# Initialize models (loaded once per container)
megadetector = None
speciesnet = None
db_manager = None


def init_models():
    """Initialize ML models and database connection"""
    global megadetector, speciesnet, db_manager

    if megadetector is None:
        logger.info("Initializing MegaDetector...")
        megadetector = MegaDetector(
            model_path='/opt/ml-models/megadetector_v5.pt',
            confidence_threshold=MEGADETECTOR_THRESHOLD
        )

    if speciesnet is None:
        logger.info("Initializing SpeciesNet...")
        speciesnet = SpeciesNet(
            model_path='/opt/ml-models/speciesnet_inat.pt',
            confidence_threshold=SPECIESNET_THRESHOLD
        )

    if db_manager is None:
        logger.info("Initializing database connection...")
        db_manager = DatabaseManager(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )


def parse_s3_path(s3_key: str) -> Dict[str, str]:
    """
    Parse S3 key to extract metadata based on expected structure:
    project-name/country/client/sensor-id/YYYY-MM-DD/filename.ext
    """
    parts = s3_key.split('/')

    metadata = {
        'project_name': parts[0] if len(parts) > 0 else None,
        'country': parts[1] if len(parts) > 1 else None,
        'client': parts[2] if len(parts) > 2 else None,
        'camera_id': parts[3] if len(parts) > 3 else None,
        'date': parts[4] if len(parts) > 4 else None,
        'file_name': parts[-1] if len(parts) > 0 else None
    }

    return metadata


def calculate_file_hash(file_bytes: bytes) -> str:
    """Calculate SHA-256 hash of file"""
    return hashlib.sha256(file_bytes).hexdigest()


def update_dynamodb_status(s3_key: str, status: str, metadata: Dict[str, Any] = None):
    """Update DynamoDB tracking table with processing status"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        update_data = {
            'file_key': s3_key,
            'processing_status': status,
            'updated_at': datetime.utcnow().isoformat()
        }

        if metadata:
            update_data.update(metadata)

        table.put_item(Item=update_data)
        logger.info(f"Updated DynamoDB status for {s3_key}: {status}")
    except Exception as e:
        logger.error(f"Failed to update DynamoDB: {str(e)}")


def process_image(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main image processing pipeline

    Steps:
    1. Download image from S3
    2. Extract EXIF data and metadata
    3. Run MegaDetector to detect animals
    4. For each detection, run SpeciesNet to classify species
    5. Store results in PostgreSQL
    6. Update DynamoDB tracking status
    """
    # Extract S3 information from event
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_key = event['Records'][0]['s3']['object']['key']

    logger.info(f"Processing image: s3://{s3_bucket}/{s3_key}")

    try:
        # Update status to processing
        update_dynamodb_status(s3_key, 'PROCESSING')

        # Download image from S3
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        image_bytes = response['Body'].read()
        file_size = len(image_bytes)

        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(image_bytes)

        # Parse S3 path for metadata
        path_metadata = parse_s3_path(s3_key)

        # Extract EXIF data
        exif_data = extract_exif_data(image_bytes)

        # Calculate image quality metrics
        quality_metrics = calculate_image_quality(image_bytes)

        # Store image metadata in database
        image_record = {
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'file_name': path_metadata['file_name'],
            'file_size': file_size,
            'file_hash': file_hash,
            'camera_id': path_metadata['camera_id'],
            'project_name': path_metadata['project_name'],
            'client': path_metadata['client'],
            'country': path_metadata['country'],
            'captured_at': exif_data.get('captured_at'),
            'exif_data': json.dumps(exif_data),
            'gps_latitude': exif_data.get('gps_latitude'),
            'gps_longitude': exif_data.get('gps_longitude'),
            'gps_altitude': exif_data.get('gps_altitude'),
            'camera_make': exif_data.get('camera_make'),
            'camera_model': exif_data.get('camera_model'),
            'width': exif_data.get('width'),
            'height': exif_data.get('height'),
            'format': exif_data.get('format'),
            'processing_status': 'processing',
            'brightness_score': quality_metrics.get('brightness'),
            'sharpness_score': quality_metrics.get('sharpness'),
            'quality_score': quality_metrics.get('overall')
        }

        image_id = db_manager.insert_image(image_record)
        logger.info(f"Image record created with ID: {image_id}")

        # Run MegaDetector
        logger.info("Running MegaDetector...")
        detections = megadetector.detect(image_bytes)
        logger.info(f"MegaDetector found {len(detections)} detections")

        # Process each detection
        detection_results = []

        for detection in detections:
            detection_type = detection['category']  # animal, person, vehicle
            bbox = detection['bbox']
            md_confidence = detection['confidence']

            detection_record = {
                'image_id': image_id,
                'detection_type': detection_type,
                'bbox_x': bbox[0],
                'bbox_y': bbox[1],
                'bbox_width': bbox[2],
                'bbox_height': bbox[3],
                'megadetector_confidence': md_confidence,
                'needs_review': md_confidence < 0.8  # Flag low-confidence detections
            }

            # If animal detected, run SpeciesNet
            if detection_type == 'animal':
                logger.info(f"Running SpeciesNet on animal detection (confidence: {md_confidence:.2f})...")

                # Crop image to bounding box
                cropped_image = megadetector.crop_detection(image_bytes, bbox)

                # Classify species
                species_predictions = speciesnet.classify(cropped_image, top_k=5)

                if species_predictions:
                    top_prediction = species_predictions[0]

                    # Get or create species record
                    species_id = db_manager.get_or_create_species(
                        scientific_name=top_prediction['scientific_name'],
                        common_name=top_prediction['common_name']
                    )

                    detection_record.update({
                        'species_id': species_id,
                        'speciesnet_confidence': top_prediction['confidence'],
                        'overall_confidence': (md_confidence + top_prediction['confidence']) / 2,
                        'species_top5': json.dumps(species_predictions)
                    })

                    logger.info(f"Species identified: {top_prediction['common_name']} "
                              f"(confidence: {top_prediction['confidence']:.2f})")

            # Store detection in database
            detection_id = db_manager.insert_detection(detection_record)
            detection_results.append({
                'detection_id': detection_id,
                'type': detection_type,
                'confidence': md_confidence,
                **detection_record
            })

        # Update image status to completed
        db_manager.update_image_status(image_id, 'completed')

        # Update DynamoDB with completion status
        update_dynamodb_status(s3_key, 'DETECTION_COMPLETE', {
            'image_id': image_id,
            'detection_count': len(detections),
            'has_animals': any(d['detection_type'] == 'animal' for d in detection_results)
        })

        logger.info(f"Successfully processed image {s3_key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processed successfully',
                'image_id': image_id,
                'detections': len(detections),
                'results': detection_results
            })
        }

    except Exception as e:
        logger.error(f"Error processing image {s3_key}: {str(e)}", exc_info=True)

        # Update status to failed
        if 'image_id' in locals():
            db_manager.update_image_status(image_id, 'failed', error_message=str(e))

        update_dynamodb_status(s3_key, 'DETECTION_FAILED', {
            'error_message': str(e)
        })

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to process image',
                'error': str(e)
            })
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point"""

    # Initialize models and database connection
    init_models()

    try:
        # Process the image
        result = process_image(event)

        return result

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Lambda execution failed',
                'error': str(e)
            })
        }

    finally:
        # Clean up database connection if needed
        # (connection pooling handles this automatically)
        pass
