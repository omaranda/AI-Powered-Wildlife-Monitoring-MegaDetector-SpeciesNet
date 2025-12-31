/**
 * Camera Trap Species Detection Platform - Locations API Route
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from 'next/server'
import { query } from '@/lib/db'

export async function GET(request: NextRequest) {
  try {
    const sql = `
      SELECT
        l.*,
        COUNT(DISTINCT i.id) as image_count,
        COUNT(DISTINCT d.id) as detection_count,
        COUNT(DISTINCT d.species_id) as species_count,
        MIN(i.captured_at) as first_capture,
        MAX(i.captured_at) as last_capture
      FROM locations l
      LEFT JOIN images i ON l.camera_id = i.camera_id
      LEFT JOIN detections d ON i.id = d.image_id
      WHERE l.is_active = true
      GROUP BY l.id
      ORDER BY l.location_name
    `

    const locations = await query(sql)

    return NextResponse.json({ locations })
  } catch (error) {
    console.error('Error fetching locations:', error)
    return NextResponse.json({ error: 'Failed to fetch locations' }, { status: 500 })
  }
}
