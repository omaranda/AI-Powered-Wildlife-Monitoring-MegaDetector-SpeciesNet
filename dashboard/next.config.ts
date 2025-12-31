/**
 * Camera Trap Species Detection Platform - Next.js Configuration
 *
 * Copyright (c) 2025 Omar Miranda
 * SPDX-License-Identifier: Apache-2.0
 */

import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  experimental: {
    serverActions: {
      bodySizeLimit: '2mb'
    }
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com'
      }
    ]
  }
}

export default nextConfig
