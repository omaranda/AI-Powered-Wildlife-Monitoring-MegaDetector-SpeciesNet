# Scripts Directory

This directory contains utility scripts for managing and deploying the Camera Trap Species Detection Platform.

## Available Scripts

### service-manager.sh
**Purpose:** Manage local development services (dashboard, database) in native or Docker mode

**Usage:**
```bash
# Native mode (default)
./service-manager.sh <command> [service] [options]

# Docker mode
SERVICE_MODE=docker ./service-manager.sh <command> [service] [options]
```

**Commands:**
- `start <service>` - Start a service (dashboard, postgres, all)
- `stop <service>` - Stop a service (dashboard, postgres, all)
- `restart <service>` - Restart a service (dashboard, postgres, all)
- `status [service]` - Show status of service(s)
- `logs <service>` - Show recent logs (default: 50 lines)
- `follow <service>` - Follow logs in real-time
- `cleanup` - Clean up old logs and PID files (native mode only)
- `build` - Build Docker images (docker mode only)
- `exec <service> <cmd>` - Execute command in container (docker mode only)
- `help` - Show help message

**Examples - Native Mode:**
```bash
# Start the dashboard
./service-manager.sh start dashboard

# Check status of all services
./service-manager.sh status

# View dashboard logs
./service-manager.sh logs dashboard

# Follow logs in real-time
./service-manager.sh follow dashboard

# Restart all services
./service-manager.sh restart all

# Clean up old logs
./service-manager.sh cleanup
```

**Examples - Docker Mode:**
```bash
# Build Docker images
SERVICE_MODE=docker ./service-manager.sh build

# Start all services (dashboard + postgres)
SERVICE_MODE=docker ./service-manager.sh start all

# Check container status
SERVICE_MODE=docker ./service-manager.sh status

# View dashboard logs
SERVICE_MODE=docker ./service-manager.sh logs dashboard

# Follow PostgreSQL logs
SERVICE_MODE=docker ./service-manager.sh follow postgres

# Execute commands in containers
SERVICE_MODE=docker ./service-manager.sh exec dashboard sh
SERVICE_MODE=docker ./service-manager.sh exec postgres psql -U species_admin -d species_detection

# Stop all containers
SERVICE_MODE=docker ./service-manager.sh stop all
```

**Log Files (Native Mode):**
- Dashboard: `.logs/dashboard.log`

**PID Files (Native Mode):**
- Dashboard: `.pids/dashboard.pid`

**Services:**
- `dashboard` - Next.js web application (port 3000)
- `postgres` - PostgreSQL database with PostGIS (port 5432, Docker mode only)
- `all` - All services

For complete Docker documentation, see [../DOCKER.md](../DOCKER.md)

---

### deploy.sh
**Purpose:** Automated full deployment of the platform (infrastructure + code)

**Usage:**
```bash
./deploy.sh
```

**What it does:**
1. Validates prerequisites (Terraform, AWS CLI, Node.js, Python)
2. Deploys infrastructure with Terraform
3. Runs database migrations
4. Packages and deploys Lambda function
5. Sets up dashboard environment

**Prerequisites:**
- AWS CLI configured with credentials
- Terraform >= 1.6
- Node.js >= 20
- Python 3.11+
- PostgreSQL client

---

## Notes

- All scripts are located in the `scripts/` directory at the project root
- Make sure scripts have executable permissions: `chmod +x scripts/*.sh`
- Service manager creates `.logs/` and `.pids/` directories (gitignored)
- For production deployments, see [docs/deployment-guide.md](../docs/deployment-guide.md)

## Adding New Scripts

When adding new scripts:

1. Add copyright header:
```bash
#!/bin/bash
# Script Name - Description
#
# Copyright (c) 2025 Omar Miranda
# SPDX-License-Identifier: Apache-2.0
```

2. Make executable:
```bash
chmod +x scripts/your-script.sh
```