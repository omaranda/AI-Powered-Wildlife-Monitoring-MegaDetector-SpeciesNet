"""
Image optimization and compression utilities for web delivery
Generates optimized versions of camera trap images for dashboard display

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

from PIL import Image
import io
import logging
from typing import Dict, Tuple, Optional
import boto3

logger = logging.getLogger()


class ImageOptimizer:
    """
    Optimizes and compresses images for web delivery
    Creates multiple sizes: thumbnail, preview, and full
    """

    # Size configurations (width, height, quality)
    SIZES = {
        'thumbnail': {'max_dimension': 200, 'quality': 80, 'format': 'JPEG'},
        'preview': {'max_dimension': 800, 'quality': 85, 'format': 'JPEG'},
        'full': {'max_dimension': 1920, 'quality': 90, 'format': 'JPEG'}
    }

    def __init__(self, s3_client=None):
        """
        Initialize the image optimizer

        Args:
            s3_client: Boto3 S3 client (optional, will create if not provided)
        """
        self.s3_client = s3_client or boto3.client('s3')

    def calculate_resize_dimensions(
        self,
        original_width: int,
        original_height: int,
        max_dimension: int
    ) -> Tuple[int, int]:
        """
        Calculate new dimensions while maintaining aspect ratio

        Args:
            original_width: Original image width
            original_height: Original image height
            max_dimension: Maximum allowed dimension (width or height)

        Returns:
            Tuple of (new_width, new_height)
        """
        aspect_ratio = original_width / original_height

        if original_width > original_height:
            # Landscape
            new_width = min(original_width, max_dimension)
            new_height = int(new_width / aspect_ratio)
        else:
            # Portrait or square
            new_height = min(original_height, max_dimension)
            new_width = int(new_height * aspect_ratio)

        return new_width, new_height

    def optimize_image(
        self,
        image_data: bytes,
        size_name: str = 'preview'
    ) -> bytes:
        """
        Optimize a single image to specified size

        Args:
            image_data: Original image bytes
            size_name: Size configuration name (thumbnail, preview, full)

        Returns:
            Optimized image bytes
        """
        if size_name not in self.SIZES:
            raise ValueError(f"Unknown size: {size_name}. Available: {list(self.SIZES.keys())}")

        config = self.SIZES[size_name]

        # Open image
        img = Image.open(io.BytesIO(image_data))

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Calculate new dimensions
        new_width, new_height = self.calculate_resize_dimensions(
            img.width,
            img.height,
            config['max_dimension']
        )

        # Only resize if image is larger than target
        if new_width < img.width or new_height < img.height:
            # Use LANCZOS for high-quality downsampling
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Optimize and compress
        output = io.BytesIO()
        img.save(
            output,
            format=config['format'],
            quality=config['quality'],
            optimize=True,
            progressive=True  # Progressive JPEG for better perceived loading
        )

        return output.getvalue()

    def optimize_all_sizes(self, image_data: bytes) -> Dict[str, bytes]:
        """
        Generate all optimized sizes for an image

        Args:
            image_data: Original image bytes

        Returns:
            Dictionary mapping size names to optimized image bytes
        """
        optimized = {}

        for size_name in self.SIZES.keys():
            try:
                optimized[size_name] = self.optimize_image(image_data, size_name)
                logger.info(f"Generated {size_name} size: {len(optimized[size_name])} bytes")
            except Exception as e:
                logger.error(f"Failed to generate {size_name} size: {str(e)}")

        return optimized

    def upload_optimized_to_s3(
        self,
        bucket: str,
        original_key: str,
        optimized_images: Dict[str, bytes],
        make_public: bool = False
    ) -> Dict[str, str]:
        """
        Upload optimized images to S3

        Args:
            bucket: S3 bucket name
            original_key: Original image S3 key
            optimized_images: Dictionary of size_name -> image_bytes
            make_public: Whether to make images publicly accessible

        Returns:
            Dictionary mapping size names to S3 URLs
        """
        urls = {}

        # Extract base path and filename
        # e.g., "project/country/client/sensor/date/image.jpg"
        # -> "project/country/client/sensor/date/optimized/"
        base_path = '/'.join(original_key.split('/')[:-1])
        filename = original_key.split('/')[-1]
        filename_without_ext = '.'.join(filename.split('.')[:-1])

        for size_name, image_bytes in optimized_images.items():
            # Create key like: path/optimized/image_thumbnail.jpg
            optimized_key = f"{base_path}/optimized/{filename_without_ext}_{size_name}.jpg"

            extra_args = {
                'ContentType': 'image/jpeg',
                'CacheControl': 'max-age=31536000',  # Cache for 1 year
            }

            if make_public:
                extra_args['ACL'] = 'public-read'

            try:
                self.s3_client.put_object(
                    Bucket=bucket,
                    Key=optimized_key,
                    Body=image_bytes,
                    **extra_args
                )

                # Generate URL
                if make_public:
                    url = f"https://{bucket}.s3.amazonaws.com/{optimized_key}"
                else:
                    # Generate pre-signed URL valid for 7 days
                    url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': optimized_key},
                        ExpiresIn=604800  # 7 days
                    )

                urls[size_name] = url
                logger.info(f"Uploaded {size_name} to {optimized_key}")

            except Exception as e:
                logger.error(f"Failed to upload {size_name} to S3: {str(e)}")

        return urls

    def process_image_for_web(
        self,
        bucket: str,
        key: str,
        make_public: bool = False
    ) -> Dict[str, str]:
        """
        Complete workflow: download, optimize, and upload image

        Args:
            bucket: S3 bucket name
            key: S3 object key
            make_public: Whether to make optimized images public

        Returns:
            Dictionary mapping size names to S3 URLs
        """
        try:
            # Download original image
            logger.info(f"Downloading image from s3://{bucket}/{key}")
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            original_data = response['Body'].read()

            original_size = len(original_data)
            logger.info(f"Original image size: {original_size} bytes ({original_size / 1024 / 1024:.2f} MB)")

            # Generate optimized versions
            optimized = self.optimize_all_sizes(original_data)

            # Log compression ratios
            for size_name, data in optimized.items():
                ratio = (1 - len(data) / original_size) * 100
                logger.info(
                    f"{size_name}: {len(data)} bytes "
                    f"({len(data) / 1024:.2f} KB, {ratio:.1f}% reduction)"
                )

            # Upload to S3
            urls = self.upload_optimized_to_s3(bucket, key, optimized, make_public)

            return urls

        except Exception as e:
            logger.error(f"Failed to process image for web: {str(e)}")
            raise


def get_optimization_stats(original_size: int, optimized_sizes: Dict[str, int]) -> Dict:
    """
    Calculate optimization statistics

    Args:
        original_size: Original image size in bytes
        optimized_sizes: Dictionary of size_name -> bytes

    Returns:
        Dictionary with optimization statistics
    """
    stats = {
        'original_size_bytes': original_size,
        'original_size_mb': round(original_size / 1024 / 1024, 2),
        'optimized': {}
    }

    for size_name, size_bytes in optimized_sizes.items():
        reduction = (1 - size_bytes / original_size) * 100
        stats['optimized'][size_name] = {
            'size_bytes': size_bytes,
            'size_kb': round(size_bytes / 1024, 2),
            'size_mb': round(size_bytes / 1024 / 1024, 2),
            'reduction_percent': round(reduction, 1)
        }

    return stats
