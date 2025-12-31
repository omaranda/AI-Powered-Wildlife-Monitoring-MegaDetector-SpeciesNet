-- Camera Trap Species Detection Database Schema
-- PostgreSQL 15+
--
-- Copyright (c) 2025 Omar Miranda
-- SPDX-License-Identifier: Apache-2.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Species catalog table
CREATE TABLE species (
    id SERIAL PRIMARY KEY,
    scientific_name VARCHAR(255) UNIQUE NOT NULL,
    common_name VARCHAR(255),
    taxonomy_kingdom VARCHAR(100),
    taxonomy_phylum VARCHAR(100),
    taxonomy_class VARCHAR(100),
    taxonomy_order VARCHAR(100),
    taxonomy_family VARCHAR(100),
    taxonomy_genus VARCHAR(100),
    conservation_status VARCHAR(50), -- LC, NT, VU, EN, CR, EW, EX, DD, NE
    iucn_id VARCHAR(50),
    description TEXT,
    habitat_notes TEXT,
    behavior_notes TEXT,
    average_weight_kg DECIMAL(10, 2),
    average_length_cm DECIMAL(10, 2),
    thumbnail_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Camera trap locations
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) UNIQUE NOT NULL,
    location_name VARCHAR(255),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    altitude DECIMAL(10, 2),
    geom GEOGRAPHY(POINT, 4326), -- PostGIS geography for spatial queries
    country VARCHAR(100),
    state_province VARCHAR(100),
    protected_area VARCHAR(255),
    habitat_type VARCHAR(100), -- forest, grassland, wetland, desert, etc.
    vegetation_type VARCHAR(100),
    installation_date DATE,
    last_maintenance_date DATE,
    camera_model VARCHAR(100),
    camera_settings JSONB,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Image metadata
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64), -- SHA-256 hash for deduplication
    width INTEGER,
    height INTEGER,
    format VARCHAR(20), -- JPEG, PNG, etc.

    -- Camera and location info
    camera_id VARCHAR(100) REFERENCES locations(camera_id),
    location_id INTEGER REFERENCES locations(id),

    -- Temporal data
    captured_at TIMESTAMP,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,

    -- Project/organization metadata
    project_name VARCHAR(100),
    client VARCHAR(100),
    country VARCHAR(100),

    -- EXIF data
    exif_data JSONB,
    gps_latitude DECIMAL(10, 8),
    gps_longitude DECIMAL(11, 8),
    gps_altitude DECIMAL(10, 2),
    camera_make VARCHAR(100),
    camera_model VARCHAR(100),

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    has_detections BOOLEAN DEFAULT false,
    detection_count INTEGER DEFAULT 0,

    -- Quality metrics
    brightness_score DECIMAL(5, 4),
    sharpness_score DECIMAL(5, 4),
    quality_score DECIMAL(5, 4),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Detection results
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    image_id INTEGER REFERENCES images(id) ON DELETE CASCADE NOT NULL,
    species_id INTEGER REFERENCES species(id),

    -- Detection type
    detection_type VARCHAR(50) NOT NULL, -- animal, person, vehicle

    -- Bounding box (normalized coordinates 0-1)
    bbox_x DECIMAL(8, 6) NOT NULL,
    bbox_y DECIMAL(8, 6) NOT NULL,
    bbox_width DECIMAL(8, 6) NOT NULL,
    bbox_height DECIMAL(8, 6) NOT NULL,

    -- Confidence scores
    megadetector_confidence DECIMAL(5, 4) NOT NULL,
    speciesnet_confidence DECIMAL(5, 4),
    overall_confidence DECIMAL(5, 4),

    -- Species classification
    species_top5 JSONB, -- Top 5 species predictions with confidence

    -- Detection metadata
    is_verified BOOLEAN DEFAULT false,
    verified_by VARCHAR(100),
    verified_at TIMESTAMP,
    verification_notes TEXT,

    -- Flags
    is_false_positive BOOLEAN DEFAULT false,
    needs_review BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Detection statistics by location (materialized view for performance)
CREATE MATERIALIZED VIEW location_statistics AS
SELECT
    l.id AS location_id,
    l.camera_id,
    l.location_name,
    l.latitude,
    l.longitude,
    COUNT(DISTINCT i.id) AS total_images,
    COUNT(DISTINCT d.id) AS total_detections,
    COUNT(DISTINCT d.species_id) AS unique_species,
    COUNT(DISTINCT CASE WHEN d.detection_type = 'animal' THEN d.species_id END) AS unique_animal_species,
    MIN(i.captured_at) AS first_capture,
    MAX(i.captured_at) AS last_capture,
    AVG(d.megadetector_confidence) AS avg_detection_confidence,
    AVG(d.speciesnet_confidence) AS avg_species_confidence
FROM locations l
LEFT JOIN images i ON l.camera_id = i.camera_id
LEFT JOIN detections d ON i.id = d.image_id
GROUP BY l.id, l.camera_id, l.location_name, l.latitude, l.longitude;

-- Species statistics (materialized view for performance)
CREATE MATERIALIZED VIEW species_statistics AS
SELECT
    s.id AS species_id,
    s.scientific_name,
    s.common_name,
    s.conservation_status,
    COUNT(DISTINCT d.id) AS total_detections,
    COUNT(DISTINCT d.image_id) AS images_with_species,
    COUNT(DISTINCT i.camera_id) AS unique_locations,
    MIN(i.captured_at) AS first_observed,
    MAX(i.captured_at) AS last_observed,
    AVG(d.speciesnet_confidence) AS avg_confidence,
    AVG(d.bbox_width * d.bbox_height) AS avg_detection_size
FROM species s
LEFT JOIN detections d ON s.id = d.species_id
LEFT JOIN images i ON d.image_id = i.id
WHERE d.detection_type = 'animal'
GROUP BY s.id, s.scientific_name, s.common_name, s.conservation_status;

-- Indexes for performance
CREATE INDEX idx_images_camera ON images(camera_id);
CREATE INDEX idx_images_captured ON images(captured_at);
CREATE INDEX idx_images_status ON images(processing_status);
CREATE INDEX idx_images_project ON images(project_name, country, client);
CREATE INDEX idx_images_s3_key ON images(s3_key);

CREATE INDEX idx_detections_image ON detections(image_id);
CREATE INDEX idx_detections_species ON detections(species_id);
CREATE INDEX idx_detections_type ON detections(detection_type);
CREATE INDEX idx_detections_confidence ON detections(megadetector_confidence, speciesnet_confidence);
CREATE INDEX idx_detections_verified ON detections(is_verified);
CREATE INDEX idx_detections_review ON detections(needs_review);

CREATE INDEX idx_locations_camera ON locations(camera_id);
CREATE INDEX idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX idx_locations_active ON locations(is_active);

CREATE INDEX idx_species_scientific ON species(scientific_name);
CREATE INDEX idx_species_common ON species(common_name);
CREATE INDEX idx_species_status ON species(conservation_status);

-- PostGIS spatial index
CREATE INDEX idx_locations_geom ON locations USING GIST(geom);

-- Trigger to update geom from lat/lon
CREATE OR REPLACE FUNCTION update_location_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_location_geom
BEFORE INSERT OR UPDATE ON locations
FOR EACH ROW
EXECUTE FUNCTION update_location_geom();

-- Trigger to update image detection count
CREATE OR REPLACE FUNCTION update_image_detection_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE images
    SET
        detection_count = (SELECT COUNT(*) FROM detections WHERE image_id = NEW.image_id),
        has_detections = true,
        updated_at = NOW()
    WHERE id = NEW.image_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_image_detection_count
AFTER INSERT ON detections
FOR EACH ROW
EXECUTE FUNCTION update_image_detection_count();

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_species_timestamp
BEFORE UPDATE ON species
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_update_images_timestamp
BEFORE UPDATE ON images
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_update_locations_timestamp
BEFORE UPDATE ON locations
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_update_detections_timestamp
BEFORE UPDATE ON detections
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY location_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY species_statistics;
END;
$$ LANGUAGE plpgsql;

-- Create unique indexes on materialized views for concurrent refresh
CREATE UNIQUE INDEX idx_location_stats_id ON location_statistics(location_id);
CREATE UNIQUE INDEX idx_species_stats_id ON species_statistics(species_id);

-- Comments for documentation
COMMENT ON TABLE species IS 'Catalog of wildlife species with taxonomic information';
COMMENT ON TABLE locations IS 'Camera trap locations with geographic and habitat data';
COMMENT ON TABLE images IS 'Camera trap images with metadata and EXIF information';
COMMENT ON TABLE detections IS 'Animal detection results from MegaDetector and SpeciesNet';
COMMENT ON MATERIALIZED VIEW location_statistics IS 'Aggregated statistics per camera location';
COMMENT ON MATERIALIZED VIEW species_statistics IS 'Aggregated statistics per species';

-- Grant permissions (adjust as needed for your user)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO species_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO species_readonly;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO species_admin;
