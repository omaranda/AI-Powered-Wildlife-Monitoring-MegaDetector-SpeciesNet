/**
 * Camera Trap Species Detection Platform - Detections API Route
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from 'next/server'
import { query } from '@/lib/db'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')
    const speciesId = searchParams.get('species_id')
    const cameraId = searchParams.get('camera_id')
    const detectionType = searchParams.get('detection_type')
    const minConfidence = parseFloat(searchParams.get('min_confidence') || '0')

    let sql = `
      SELECT
        d.*,
        s.scientific_name,
        s.common_name,
        s.conservation_status,
        i.s3_bucket,
        i.s3_key,
        i.captured_at,
        i.camera_id,
        l.latitude,
        l.longitude,
        l.location_name
      FROM detections d
      LEFT JOIN species s ON d.species_id = s.id
      JOIN images i ON d.image_id = i.id
      LEFT JOIN locations l ON i.camera_id = l.camera_id
      WHERE 1=1
    `

    const params: any[] = []
    let paramIndex = 1

    if (speciesId) {
      sql += ` AND d.species_id = $${paramIndex}`
      params.push(parseInt(speciesId))
      paramIndex++
    }

    if (cameraId) {
      sql += ` AND i.camera_id = $${paramIndex}`
      params.push(cameraId)
      paramIndex++
    }

    if (detectionType) {
      sql += ` AND d.detection_type = $${paramIndex}`
      params.push(detectionType)
      paramIndex++
    }

    if (minConfidence > 0) {
      sql += ` AND d.megadetector_confidence >= $${paramIndex}`
      params.push(minConfidence)
      paramIndex++
    }

    sql += ` ORDER BY i.captured_at DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`
    params.push(limit, offset)

    const detections = await query(sql, params)

    return NextResponse.json({
      detections,
      pagination: {
        limit,
        offset
      }
    })
  } catch (error) {
    console.error('Error fetching detections:', error)
    return NextResponse.json({ error: 'Failed to fetch detections' }, { status: 500 })
  }
}
