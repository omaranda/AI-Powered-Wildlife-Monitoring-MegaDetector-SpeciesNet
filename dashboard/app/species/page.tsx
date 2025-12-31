/**
 * Camera Trap Species Detection Platform - Species List Page
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

'use client'

import { useEffect, useState } from 'react'
import { formatConfidence, getConservationStatusColor } from '@/lib/utils'

interface Species {
  id: number
  scientific_name: string
  common_name: string
  conservation_status: string
  detection_count: number
  location_count: number
  first_observed: string
  last_observed: string
  avg_confidence: number
}

export default function SpeciesPage() {
  const [species, setSpecies] = useState<Species[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [conservationFilter, setConservationFilter] = useState('')

  useEffect(() => {
    fetchSpecies()
  }, [search, conservationFilter])

  async function fetchSpecies() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (conservationFilter) params.append('conservation_status', conservationFilter)

      const res = await fetch(`/api/species?${params}`)
      const data = await res.json()
      setSpecies(data.species || [])
    } catch (error) {
      console.error('Error fetching species:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Detected Species</h1>
        <p className="mt-2 text-sm text-gray-600">
          Browse all species identified by AI detection
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search species..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
        </div>
        <select
          value={conservationFilter}
          onChange={(e) => setConservationFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500"
        >
          <option value="">All Status</option>
          <option value="LC">Least Concern</option>
          <option value="NT">Near Threatened</option>
          <option value="VU">Vulnerable</option>
          <option value="EN">Endangered</option>
          <option value="CR">Critically Endangered</option>
        </select>
      </div>

      {/* Species Table */}
      {loading ? (
        <div className="text-center py-12">Loading species...</div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Species
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Detections
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Locations
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Confidence
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Observed
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {species.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {s.common_name || 'Unknown'}
                      </div>
                      <div className="text-sm text-gray-500 italic">
                        {s.scientific_name}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${getConservationStatusColor(s.conservation_status || 'NE')}`}>
                      {s.conservation_status || 'NE'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {s.detection_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {s.location_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {s.avg_confidence ? formatConfidence(parseFloat(s.avg_confidence.toString())) : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {s.last_observed ? new Date(s.last_observed).toLocaleDateString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {species.length === 0 && !loading && (
        <div className="text-center py-12 text-gray-500">
          No species found matching your criteria
        </div>
      )}
    </div>
  )
}
