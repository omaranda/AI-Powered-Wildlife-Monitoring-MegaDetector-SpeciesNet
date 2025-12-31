/**
 * Camera Trap Species Detection Platform - Dashboard Page
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

import { Suspense } from 'react'
import Link from 'next/link'

async function getDashboardStats() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'
  const res = await fetch(`${baseUrl}/api/stats`, {
    next: { revalidate: 60 } // Revalidate every 60 seconds
  })

  if (!res.ok) {
    throw new Error('Failed to fetch stats')
  }

  return res.json()
}

function StatsCard({ title, value, subtitle, icon }: {
  title: string
  value: string | number
  subtitle?: string
  icon?: string
}) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            {icon && <span className="text-3xl">{icon}</span>}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">{value}</div>
              </dd>
              {subtitle && (
                <dd className="text-sm text-gray-500 mt-1">{subtitle}</dd>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}

async function DashboardContent() {
  const data = await getDashboardStats()
  const { stats, recentDetections, topSpecies, timeline } = data

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Camera Trap Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">
          AI-powered species detection and monitoring
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatsCard
          title="Total Images"
          value={stats.total_images?.toLocaleString() || '0'}
          subtitle={`${stats.processed_images || 0} processed`}
          icon="📸"
        />
        <StatsCard
          title="Total Detections"
          value={stats.total_detections?.toLocaleString() || '0'}
          icon="🎯"
        />
        <StatsCard
          title="Species Detected"
          value={stats.total_species?.toLocaleString() || '0'}
          icon="🦌"
        />
        <StatsCard
          title="Locations"
          value={stats.total_locations?.toLocaleString() || '0'}
          icon="📍"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Detections */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Detections</h2>
          </div>
          <div className="px-6 py-4">
            <div className="space-y-4">
              {recentDetections.slice(0, 5).map((detection: any) => (
                <div key={detection.id} className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {detection.common_name || detection.detection_type}
                    </p>
                    <p className="text-xs text-gray-500">
                      {detection.location_name || 'Unknown location'} •{' '}
                      {new Date(detection.captured_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="ml-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {(detection.megadetector_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6">
              <Link
                href="/species"
                className="text-sm font-medium text-green-600 hover:text-green-500"
              >
                View all detections →
              </Link>
            </div>
          </div>
        </div>

        {/* Top Species */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Top Detected Species</h2>
          </div>
          <div className="px-6 py-4">
            <div className="space-y-4">
              {topSpecies.slice(0, 5).map((species: any, index: number) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {species.common_name}
                    </p>
                    <p className="text-xs text-gray-500 italic">
                      {species.scientific_name}
                    </p>
                  </div>
                  <div className="ml-4 flex items-center">
                    <span className="text-sm text-gray-900 font-medium">
                      {species.detection_count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6">
              <Link
                href="/species"
                className="text-sm font-medium text-green-600 hover:text-green-500"
              >
                View all species →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          href="/species"
          className="block p-6 bg-white shadow rounded-lg hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Browse Species
          </h3>
          <p className="text-sm text-gray-600">
            View and search all detected species with filtering options
          </p>
        </Link>
        <Link
          href="/map"
          className="block p-6 bg-white shadow rounded-lg hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Explore Map
          </h3>
          <p className="text-sm text-gray-600">
            Visualize species distribution across camera trap locations
          </p>
        </Link>
        <div className="block p-6 bg-white shadow rounded-lg">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Export Data
          </h3>
          <p className="text-sm text-gray-600">
            Download detection data for further analysis
          </p>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Loading dashboard...</div>}>
      <DashboardContent />
    </Suspense>
  )
}
