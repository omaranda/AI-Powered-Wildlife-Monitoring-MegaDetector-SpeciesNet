/**
 * Camera Trap Species Detection Platform - Map View Page
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

'use client'

import { useEffect, useState, useRef } from 'react'

interface Location {
  id: number
  camera_id: string
  location_name: string
  latitude: number
  longitude: number
  species_count: number
  detection_count: number
  image_count: number
}

export default function MapPage() {
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)
  const mapContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchLocations()
  }, [])

  async function fetchLocations() {
    setLoading(true)
    try {
      const res = await fetch('/api/locations')
      const data = await res.json()
      setLocations(data.locations || [])
    } catch (error) {
      console.error('Error fetching locations:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Camera Locations Map</h1>
        <p className="mt-2 text-sm text-gray-600">
          Geographic distribution of species detections
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Container */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div
              ref={mapContainerRef}
              className="h-[600px] bg-gray-100 flex items-center justify-center"
            >
              <div className="text-center">
                <p className="text-gray-500 mb-4">Interactive map view</p>
                <p className="text-sm text-gray-400">
                  To enable map functionality, add Mapbox token to environment variables
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  NEXT_PUBLIC_MAPBOX_TOKEN=your_token_here
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Locations List */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="px-4 py-5 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Camera Locations ({locations.length})
              </h2>
            </div>
            <div className="max-h-[550px] overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center text-gray-500">Loading locations...</div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {locations.map((location) => (
                    <li
                      key={location.id}
                      onClick={() => setSelectedLocation(location)}
                      className={`px-4 py-4 hover:bg-gray-50 cursor-pointer ${
                        selectedLocation?.id === location.id ? 'bg-green-50' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">
                            {location.location_name || location.camera_id}
                          </p>
                          <p className="text-xs text-gray-500">
                            {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                          </p>
                        </div>
                        <div className="ml-4 flex-shrink-0">
                          <div className="text-right">
                            <p className="text-sm font-medium text-green-600">
                              {location.species_count} species
                            </p>
                            <p className="text-xs text-gray-500">
                              {location.detection_count} detections
                            </p>
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {selectedLocation && (
            <div className="mt-4 bg-white shadow rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Location Details
              </h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-500">Camera ID</dt>
                  <dd className="text-sm text-gray-900">{selectedLocation.camera_id}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Images</dt>
                  <dd className="text-sm text-gray-900">{selectedLocation.image_count}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Detections</dt>
                  <dd className="text-sm text-gray-900">{selectedLocation.detection_count}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Unique Species</dt>
                  <dd className="text-sm text-gray-900">{selectedLocation.species_count}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">Map Integration</h3>
        <p className="text-sm text-blue-800">
          To enable the interactive map with markers and clustering:
        </p>
        <ol className="mt-2 text-sm text-blue-800 list-decimal list-inside space-y-1">
          <li>Sign up for a free Mapbox account at mapbox.com</li>
          <li>Get your access token from the dashboard</li>
          <li>Add to .env.local: NEXT_PUBLIC_MAPBOX_TOKEN=your_token</li>
          <li>Restart the development server</li>
        </ol>
      </div>
    </div>
  )
}
