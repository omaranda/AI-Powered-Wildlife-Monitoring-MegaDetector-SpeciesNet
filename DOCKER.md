# Docker Setup Guide

This guide explains how to run the Camera Trap Species Detection Platform using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) >= 20.10
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.0 (or `docker compose` plugin)

## Quick Start

### 1. Configure Environment

Copy the example environment file and update it with your settings:

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker` and set your database password and other variables:

```bash
# Database Configuration
DB_PASSWORD=your_secure_password_here

# Mapbox (Optional)
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here
```

### 2. Build and Start Services

```bash
# Using Docker Compose directly
docker compose --env-file .env.docker up -d

# Or using the service manager
SERVICE_MODE=docker ./scripts/service-manager.sh build
SERVICE_MODE=docker ./scripts/service-manager.sh start all
```

### 3. Access the Dashboard

Open your browser to: **http://localhost:3000**

The PostgreSQL database is available at: **localhost:5432**

## Service Manager Commands

The service manager script supports Docker mode:

### Build Images
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh build
```

### Start Services
```bash
# Start all services (dashboard + postgres)
SERVICE_MODE=docker ./scripts/service-manager.sh start all

# Start only dashboard
SERVICE_MODE=docker ./scripts/service-manager.sh start dashboard

# Start only database
SERVICE_MODE=docker ./scripts/service-manager.sh start postgres
```

### Stop Services
```bash
# Stop all services
SERVICE_MODE=docker ./scripts/service-manager.sh stop all

# Stop specific service
SERVICE_MODE=docker ./scripts/service-manager.sh stop dashboard
```

### Check Status
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh status
```

### View Logs
```bash
# Show recent logs
SERVICE_MODE=docker ./scripts/service-manager.sh logs dashboard
SERVICE_MODE=docker ./scripts/service-manager.sh logs postgres

# Follow logs in real-time
SERVICE_MODE=docker ./scripts/service-manager.sh follow dashboard
```

### Execute Commands in Containers
```bash
# Open shell in dashboard container
SERVICE_MODE=docker ./scripts/service-manager.sh exec dashboard sh

# Connect to PostgreSQL
SERVICE_MODE=docker ./scripts/service-manager.sh exec postgres psql -U species_admin -d species_detection

# Run npm commands
SERVICE_MODE=docker ./scripts/service-manager.sh exec dashboard npm run lint
```

### Restart Services
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh restart all
SERVICE_MODE=docker ./scripts/service-manager.sh restart dashboard
```

## Direct Docker Compose Commands

If you prefer to use Docker Compose directly:

```bash
# Start services
docker compose --env-file .env.docker up -d

# Stop services
docker compose down

# Stop and remove volumes (database data will be lost)
docker compose down -v

# View logs
docker compose logs -f dashboard
docker compose logs -f postgres

# Rebuild images
docker compose build

# Start with rebuild
docker compose up -d --build

# Execute commands
docker compose exec dashboard sh
docker compose exec postgres psql -U species_admin -d species_detection
```

## Services

### Dashboard
- **Image**: Built from `dashboard/Dockerfile`
- **Port**: 3000
- **Environment**: Production-optimized Next.js standalone build
- **Health Check**: Pings `/api/stats` endpoint every 30s

### PostgreSQL (Local Development)
- **Image**: `postgis/postgis:15-3.3-alpine`
- **Port**: 5432
- **Extensions**: PostGIS for geospatial queries
- **Data**: Persisted in Docker volume `postgres_data`
- **Initialization**: Runs SQL scripts from `database/migrations/` on first start

> **Note**: For production deployments, use AWS RDS instead of the containerized PostgreSQL.

## Volumes

- `postgres_data`: PostgreSQL database files (persistent)

To remove the database volume and start fresh:

```bash
docker compose down -v
```

## Network

All services run on a bridge network named `species-detection`.

## Database Migrations

Database migrations are automatically run when the PostgreSQL container starts for the first time. The SQL files in `database/migrations/` are executed in alphabetical order.

To manually run migrations:

```bash
# Copy SQL file into container
docker compose cp database/migrations/002_new_migration.sql postgres:/tmp/

# Execute migration
SERVICE_MODE=docker ./scripts/service-manager.sh exec postgres psql -U species_admin -d species_detection -f /tmp/002_new_migration.sql
```

## Environment Variables

### Dashboard Container

- `NODE_ENV`: Set to `production`
- `DATABASE_URL`: PostgreSQL connection string
- `NEXT_PUBLIC_MAPBOX_TOKEN`: Mapbox API token (optional)
- `NEXT_PUBLIC_API_URL`: Base URL for API requests

### PostgreSQL Container

- `POSTGRES_USER`: Database username (default: `species_admin`)
- `POSTGRES_PASSWORD`: Database password (**required**, set in `.env.docker`)
- `POSTGRES_DB`: Database name (default: `species_detection`)

## Troubleshooting

### Container Won't Start

Check logs:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh logs dashboard
docker compose logs
```

### Database Connection Errors

1. Ensure PostgreSQL is healthy:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh exec postgres pg_isready -U species_admin
```

2. Check DATABASE_URL in dashboard environment:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh exec dashboard printenv DATABASE_URL
```

3. Verify network connectivity:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh exec dashboard ping postgres
```

### Port Already in Use

If ports 3000 or 5432 are already in use, modify `docker-compose.yml`:

```yaml
services:
  dashboard:
    ports:
      - "3001:3000"  # Use port 3001 on host
```

### Rebuild After Code Changes

```bash
SERVICE_MODE=docker ./scripts/service-manager.sh stop all
SERVICE_MODE=docker ./scripts/service-manager.sh build
SERVICE_MODE=docker ./scripts/service-manager.sh start all
```

Or:
```bash
docker compose up -d --build
```

## Production Deployment

For production:

1. **Don't use containerized PostgreSQL** - Use AWS RDS PostgreSQL instead
2. **Update environment variables** - Use production DATABASE_URL pointing to RDS
3. **Remove postgres service** - Comment out or remove from `docker-compose.yml`
4. **Use proper secrets management** - Use AWS Secrets Manager or similar
5. **Configure proper logging** - Set up CloudWatch or centralized logging
6. **Enable SSL/TLS** - Use reverse proxy (nginx, Traefik) with SSL certificates
7. **Scale horizontally** - Use container orchestration (ECS, Kubernetes)

Example production docker-compose.yml:

```yaml
version: '3.8'

services:
  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    container_name: species-detection-dashboard
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${RDS_DATABASE_URL}
      - NEXT_PUBLIC_MAPBOX_TOKEN=${MAPBOX_TOKEN}
    restart: always
    # Remove postgres service - use RDS instead
```

## Clean Up

Remove all containers, networks, and volumes:

```bash
# Stop and remove containers and networks
docker compose down

# Stop and remove containers, networks, AND volumes (WARNING: deletes database)
docker compose down -v

# Remove built images
docker rmi species-detection-dashboard
```

## Health Checks

Both services include health checks:

- **Dashboard**: HTTP check on `/api/stats` every 30s
- **PostgreSQL**: `pg_isready` check every 10s

View health status:
```bash
docker compose ps
```

## Development Workflow

1. Make code changes in `dashboard/` directory
2. Rebuild and restart:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh stop dashboard
SERVICE_MODE=docker ./scripts/service-manager.sh build
SERVICE_MODE=docker ./scripts/service-manager.sh start dashboard
```

3. View logs to debug:
```bash
SERVICE_MODE=docker ./scripts/service-manager.sh follow dashboard
```

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Next.js Docker Deployment](https://nextjs.org/docs/deployment#docker-image)
- [PostGIS Docker Image](https://registry.hub.docker.com/r/postgis/postgis/)
