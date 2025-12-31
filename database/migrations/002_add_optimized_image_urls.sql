-- Add optimized image URL columns to images table
-- For web-optimized versions: thumbnail, preview, and full size
--
-- Copyright (c) 2025 Omar Miranda
-- SPDX-License-Identifier: Apache-2.0

-- Add columns for optimized image URLs
ALTER TABLE images
ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(1000),
ADD COLUMN IF NOT EXISTS preview_url VARCHAR(1000),
ADD COLUMN IF NOT EXISTS full_url VARCHAR(1000);

-- Add index for faster lookups by URLs
CREATE INDEX IF NOT EXISTS idx_images_thumbnail_url ON images(thumbnail_url) WHERE thumbnail_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_images_preview_url ON images(preview_url) WHERE preview_url IS NOT NULL;

-- Add comment explaining the columns
COMMENT ON COLUMN images.thumbnail_url IS 'S3 URL or pre-signed URL for 200px max dimension thumbnail (JPEG, quality 80)';
COMMENT ON COLUMN images.preview_url IS 'S3 URL or pre-signed URL for 800px max dimension preview (JPEG, quality 85)';
COMMENT ON COLUMN images.full_url IS 'S3 URL or pre-signed URL for 1920px max dimension full size (JPEG, quality 90)';
