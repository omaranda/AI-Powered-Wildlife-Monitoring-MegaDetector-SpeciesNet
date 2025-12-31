/**
 * Camera Trap Species Detection Platform - Statistics API Route
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextResponse } from 'next/server'
import { query } from '@/lib/db'

export async function GET() {
  try {
    // Get overview statistics
    const [stats] = await query(`
      SELECT
        COUNT(DISTINCT i.id) as total_images,
        COUNT(DISTINCT d.id) as total_detections,
        COUNT(DISTINCT s.id) as total_species,
        COUNT(DISTINCT l.id) as total_locations,
        COUNT(DISTINCT CASE WHEN i.processing_status = 'completed' THEN i.id END) as processed_images,
        COUNT(DISTINCT CASE WHEN i.processing_status = 'pending' THEN i.id END) as pending_images
      FROM images i
      LEFT JOIN detections d ON i.id = d.image_id
      LEFT JOIN species s ON d.species_id = s.id
      LEFT JOIN locations l ON i.camera_id = l.camera_id
    `)

    // Get recent detections
    const recentDetections = await query(`
      SELECT
        d.id,
        d.detection_type,
        d.megadetector_confidence,
        s.common_name,
        s.scientific_name,
        i.captured_at,
        l.location_name
      FROM detections d
      LEFT JOIN species s ON d.species_id = s.id
      JOIN images i ON d.image_id = i.id
      LEFT JOIN locations l ON i.camera_id = l.camera_id
      ORDER BY i.captured_at DESC
      LIMIT 10
    `)

    // Get top species
    const topSpecies = await query(`
      SELECT
        s.common_name,
        s.scientific_name,
        s.conservation_status,
        COUNT(d.id) as detection_count
      FROM species s
      JOIN detections d ON s.id = d.species_id
      GROUP BY s.id, s.common_name, s.scientific_name, s.conservation_status
      ORDER BY detection_count DESC
      LIMIT 10
    `)

    // Get detection timeline (last 30 days)
    const timeline = await query(`
      SELECT
        DATE(i.captured_at) as date,
        COUNT(DISTINCT d.id) as detection_count,
        COUNT(DISTINCT CASE WHEN d.detection_type = 'animal' THEN d.id END) as animal_count
      FROM detections d
      JOIN images i ON d.image_id = i.id
      WHERE i.captured_at >= NOW() - INTERVAL '30 days'
      GROUP BY DATE(i.captured_at)
      ORDER BY date DESC
    `)

    return NextResponse.json({
      stats,
      recentDetections,
      topSpecies,
      timeline
    })
  } catch (error) {
    console.error('Error fetching stats:', error)
    return NextResponse.json({ error: 'Failed to fetch statistics' }, { status: 500 })
  }
}
