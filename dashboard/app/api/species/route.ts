/**
 * Camera Trap Species Detection Platform - Species API Route
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
    const conservationStatus = searchParams.get('conservation_status')
    const search = searchParams.get('search')

    let sql = `
      SELECT
        s.*,
        COUNT(DISTINCT d.id) as detection_count,
        COUNT(DISTINCT i.camera_id) as location_count,
        MIN(i.captured_at) as first_observed,
        MAX(i.captured_at) as last_observed,
        AVG(d.speciesnet_confidence) as avg_confidence
      FROM species s
      LEFT JOIN detections d ON s.id = d.species_id
      LEFT JOIN images i ON d.image_id = i.id
      WHERE 1=1
    `

    const params: any[] = []
    let paramIndex = 1

    if (conservationStatus) {
      sql += ` AND s.conservation_status = $${paramIndex}`
      params.push(conservationStatus)
      paramIndex++
    }

    if (search) {
      sql += ` AND (s.scientific_name ILIKE $${paramIndex} OR s.common_name ILIKE $${paramIndex})`
      params.push(`%${search}%`)
      paramIndex++
    }

    sql += `
      GROUP BY s.id
      HAVING COUNT(DISTINCT d.id) > 0
      ORDER BY COUNT(DISTINCT d.id) DESC
      LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
    `
    params.push(limit, offset)

    const species = await query(sql, params)

    // Get total count
    let countSql = 'SELECT COUNT(DISTINCT s.id) as total FROM species s LEFT JOIN detections d ON s.id = d.species_id WHERE 1=1'
    const countParams: any[] = []
    let countParamIndex = 1

    if (conservationStatus) {
      countSql += ` AND s.conservation_status = $${countParamIndex}`
      countParams.push(conservationStatus)
      countParamIndex++
    }

    if (search) {
      countSql += ` AND (s.scientific_name ILIKE $${countParamIndex} OR s.common_name ILIKE $${countParamIndex})`
      countParams.push(`%${search}%`)
    }

    countSql += ' AND EXISTS (SELECT 1 FROM detections WHERE species_id = s.id)'

    const [{ total }] = await query(countSql, countParams)

    return NextResponse.json({
      species,
      pagination: {
        total: parseInt(total),
        limit,
        offset,
        hasMore: offset + limit < parseInt(total)
      }
    })
  } catch (error) {
    console.error('Error fetching species:', error)
    return NextResponse.json({ error: 'Failed to fetch species' }, { status: 500 })
  }
}
