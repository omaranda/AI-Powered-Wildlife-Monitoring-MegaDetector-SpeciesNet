"""
PostgreSQL Database Manager for Species Detection Platform
Handles all database operations for images, detections, species, and locations

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool
import logging
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger()


class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 5432,
        min_conn: int = 1,
        max_conn: int = 10
    ):
        """
        Initialize database connection pool

        Args:
            host: Database host
            database: Database name
            user: Database user
            password: Database password
            port: Database port
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        try:
            self.pool = SimpleConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                sslmode='require'
            )
            logger.info(f"Database connection pool created: {host}:{port}/{database}")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {str(e)}")
            raise

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """
        Context manager for database cursor

        Args:
            dict_cursor: If True, returns DictCursor for dict-like row access

        Yields:
            Database cursor
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor if dict_cursor else None)
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}", exc_info=True)
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def insert_image(self, image_data: Dict[str, Any]) -> int:
        """
        Insert image record

        Args:
            image_data: Dictionary with image metadata

        Returns:
            Image ID
        """
        query = """
            INSERT INTO images (
                s3_bucket, s3_key, file_name, file_size, file_hash,
                width, height, format, camera_id, location_id,
                captured_at, project_name, client, country,
                exif_data, gps_latitude, gps_longitude, gps_altitude,
                camera_make, camera_model, processing_status,
                brightness_score, sharpness_score, quality_score
            ) VALUES (
                %(s3_bucket)s, %(s3_key)s, %(file_name)s, %(file_size)s, %(file_hash)s,
                %(width)s, %(height)s, %(format)s, %(camera_id)s, %(location_id)s,
                %(captured_at)s, %(project_name)s, %(client)s, %(country)s,
                %(exif_data)s, %(gps_latitude)s, %(gps_longitude)s, %(gps_altitude)s,
                %(camera_make)s, %(camera_model)s, %(processing_status)s,
                %(brightness_score)s, %(sharpness_score)s, %(quality_score)s
            )
            ON CONFLICT (s3_key) DO UPDATE SET
                updated_at = NOW()
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, image_data)
            result = cursor.fetchone()
            image_id = result['id']
            logger.info(f"Inserted image record with ID: {image_id}")
            return image_id

    def update_image_status(
        self,
        image_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update image processing status"""
        query = """
            UPDATE images
            SET processing_status = %s,
                error_message = %s,
                processed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE processed_at END,
                updated_at = NOW()
            WHERE id = %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (status, error_message, status, image_id))
            logger.info(f"Updated image {image_id} status to: {status}")

    def insert_detection(self, detection_data: Dict[str, Any]) -> int:
        """
        Insert detection record

        Args:
            detection_data: Dictionary with detection metadata

        Returns:
            Detection ID
        """
        query = """
            INSERT INTO detections (
                image_id, species_id, detection_type,
                bbox_x, bbox_y, bbox_width, bbox_height,
                megadetector_confidence, speciesnet_confidence, overall_confidence,
                species_top5, needs_review
            ) VALUES (
                %(image_id)s, %(species_id)s, %(detection_type)s,
                %(bbox_x)s, %(bbox_y)s, %(bbox_width)s, %(bbox_height)s,
                %(megadetector_confidence)s, %(speciesnet_confidence)s, %(overall_confidence)s,
                %(species_top5)s, %(needs_review)s
            )
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, detection_data)
            result = cursor.fetchone()
            detection_id = result['id']
            logger.info(f"Inserted detection record with ID: {detection_id}")
            return detection_id

    def get_or_create_species(
        self,
        scientific_name: str,
        common_name: Optional[str] = None,
        taxonomy: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Get existing species ID or create new species record

        Args:
            scientific_name: Scientific name of species
            common_name: Common name of species
            taxonomy: Taxonomic classification

        Returns:
            Species ID
        """
        # Try to get existing species
        select_query = "SELECT id FROM species WHERE scientific_name = %s"

        with self.get_cursor() as cursor:
            cursor.execute(select_query, (scientific_name,))
            result = cursor.fetchone()

            if result:
                return result['id']

            # Create new species
            insert_query = """
                INSERT INTO species (
                    scientific_name, common_name,
                    taxonomy_kingdom, taxonomy_phylum, taxonomy_class,
                    taxonomy_order, taxonomy_family, taxonomy_genus
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """

            taxonomy = taxonomy or {}
            cursor.execute(
                insert_query,
                (
                    scientific_name,
                    common_name,
                    taxonomy.get('kingdom'),
                    taxonomy.get('phylum'),
                    taxonomy.get('class'),
                    taxonomy.get('order'),
                    taxonomy.get('family'),
                    taxonomy.get('genus')
                )
            )

            result = cursor.fetchone()
            species_id = result['id']
            logger.info(f"Created new species record: {scientific_name} (ID: {species_id})")
            return species_id

    def get_image_by_s3_key(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Get image record by S3 key"""
        query = "SELECT * FROM images WHERE s3_key = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (s3_key,))
            return cursor.fetchone()

    def get_detections_by_image(self, image_id: int) -> List[Dict[str, Any]]:
        """Get all detections for an image"""
        query = """
            SELECT
                d.*,
                s.scientific_name,
                s.common_name,
                s.conservation_status
            FROM detections d
            LEFT JOIN species s ON d.species_id = s.id
            WHERE d.image_id = %s
            ORDER BY d.megadetector_confidence DESC
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (image_id,))
            return cursor.fetchall()

    def get_species_statistics(
        self,
        limit: int = 100,
        offset: int = 0,
        conservation_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get species statistics from materialized view"""
        query = """
            SELECT * FROM species_statistics
            WHERE total_detections > 0
        """

        params = []

        if conservation_status:
            query += " AND conservation_status = %s"
            params.append(conservation_status)

        query += " ORDER BY total_detections DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_location_statistics(self) -> List[Dict[str, Any]]:
        """Get location statistics from materialized view"""
        query = "SELECT * FROM location_statistics ORDER BY total_detections DESC"

        with self.get_cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def refresh_statistics(self):
        """Refresh materialized views"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT refresh_statistics()")
            logger.info("Refreshed statistics materialized views")

    def get_or_create_location(
        self,
        camera_id: str,
        latitude: float,
        longitude: float,
        **kwargs
    ) -> int:
        """
        Get existing location ID or create new location record

        Args:
            camera_id: Camera trap identifier
            latitude: GPS latitude
            longitude: GPS longitude
            **kwargs: Additional location metadata

        Returns:
            Location ID
        """
        # Try to get existing location
        select_query = "SELECT id FROM locations WHERE camera_id = %s"

        with self.get_cursor() as cursor:
            cursor.execute(select_query, (camera_id,))
            result = cursor.fetchone()

            if result:
                return result['id']

            # Create new location
            insert_query = """
                INSERT INTO locations (
                    camera_id, latitude, longitude, altitude,
                    location_name, country, habitat_type
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """

            cursor.execute(
                insert_query,
                (
                    camera_id,
                    latitude,
                    longitude,
                    kwargs.get('altitude'),
                    kwargs.get('location_name'),
                    kwargs.get('country'),
                    kwargs.get('habitat_type')
                )
            )

            result = cursor.fetchone()
            location_id = result['id']
            logger.info(f"Created new location record: {camera_id} (ID: {location_id})")
            return location_id

    def close(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")
