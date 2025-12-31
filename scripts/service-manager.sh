#!/bin/bash
# Camera Trap Species Detection Platform - Service Manager
# Manage local development services (dashboard, database connections, etc.)
# Supports both native Node.js and Docker modes
#
# Copyright (c) 2025 Omar Miranda
# SPDX-License-Identifier: Apache-2.0

set -e

# Mode: native or docker
MODE="${SERVICE_MODE:-native}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PROJECT_ROOT}/.pids"
LOG_DIR="${PROJECT_ROOT}/.logs"

# Ensure directories exist
mkdir -p "$PID_DIR" "$LOG_DIR"

# PID files
DASHBOARD_PID="${PID_DIR}/dashboard.pid"

# Log files
DASHBOARD_LOG="${LOG_DIR}/dashboard.log"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to start the dashboard
start_dashboard() {
    if is_running "$DASHBOARD_PID"; then
        print_warning "Dashboard is already running (PID: $(cat $DASHBOARD_PID))"
        return 0
    fi

    print_info "Starting Next.js dashboard..."

    cd "${PROJECT_ROOT}/dashboard"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found. Running npm install..."
        npm install
    fi

    # Check if .env.local exists
    if [ ! -f ".env.local" ]; then
        print_warning ".env.local not found. Please create it with DATABASE_URL"
    fi

    # Start the dashboard in background
    nohup npm run dev > "$DASHBOARD_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$DASHBOARD_PID"

    sleep 2

    if is_running "$DASHBOARD_PID"; then
        print_success "Dashboard started (PID: $pid)"
        print_info "Dashboard running at: http://localhost:3000"
        print_info "Logs: $DASHBOARD_LOG"
    else
        print_error "Failed to start dashboard. Check logs: $DASHBOARD_LOG"
        return 1
    fi
}

# Function to stop the dashboard
stop_dashboard() {
    if is_running "$DASHBOARD_PID"; then
        local pid=$(cat "$DASHBOARD_PID")
        print_info "Stopping dashboard (PID: $pid)..."

        # Kill the process and its children
        pkill -P $pid 2>/dev/null || true
        kill $pid 2>/dev/null || true

        # Wait a bit and force kill if necessary
        sleep 2
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null || true
        fi

        rm -f "$DASHBOARD_PID"
        print_success "Dashboard stopped"
    else
        print_warning "Dashboard is not running"
    fi
}

# Function to get dashboard status
status_dashboard() {
    if is_running "$DASHBOARD_PID"; then
        local pid=$(cat "$DASHBOARD_PID")
        print_success "Dashboard is running (PID: $pid)"
        print_info "URL: http://localhost:3000"
        print_info "Logs: $DASHBOARD_LOG"
        return 0
    else
        print_warning "Dashboard is not running"
        return 1
    fi
}

# Function to show logs
show_logs() {
    local service=$1
    local lines=${2:-50}

    case $service in
        dashboard)
            if [ -f "$DASHBOARD_LOG" ]; then
                print_info "Showing last $lines lines of dashboard logs:"
                echo "----------------------------------------"
                tail -n "$lines" "$DASHBOARD_LOG"
            else
                print_error "Dashboard log file not found: $DASHBOARD_LOG"
            fi
            ;;
        *)
            print_error "Unknown service: $service"
            print_info "Available services: dashboard"
            return 1
            ;;
    esac
}

# Function to follow logs
follow_logs() {
    local service=$1

    case $service in
        dashboard)
            if [ -f "$DASHBOARD_LOG" ]; then
                print_info "Following dashboard logs (Ctrl+C to stop):"
                echo "----------------------------------------"
                tail -f "$DASHBOARD_LOG"
            else
                print_error "Dashboard log file not found: $DASHBOARD_LOG"
            fi
            ;;
        *)
            print_error "Unknown service: $service"
            print_info "Available services: dashboard"
            return 1
            ;;
    esac
}

# Function to start all services
start_all() {
    print_info "Starting all services..."
    start_dashboard
    echo ""
    status_all
}

# Function to stop all services
stop_all() {
    print_info "Stopping all services..."
    stop_dashboard
}

# Function to restart a service
restart_service() {
    local service=$1

    case $service in
        dashboard)
            print_info "Restarting dashboard..."
            stop_dashboard
            sleep 1
            start_dashboard
            ;;
        all)
            print_info "Restarting all services..."
            stop_all
            sleep 1
            start_all
            ;;
        *)
            print_error "Unknown service: $service"
            print_info "Available services: dashboard, all"
            return 1
            ;;
    esac
}

# Function to show status of all services
status_all() {
    print_info "Service Status:"
    echo "----------------------------------------"
    status_dashboard
}

# Function to clean up old logs and PID files
cleanup() {
    print_info "Cleaning up old logs and PID files..."

    # Remove stale PID files
    if [ -f "$DASHBOARD_PID" ] && ! is_running "$DASHBOARD_PID"; then
        rm -f "$DASHBOARD_PID"
        print_info "Removed stale dashboard PID file"
    fi

    # Optionally rotate logs if they're too large (> 10MB)
    if [ -f "$DASHBOARD_LOG" ] && [ $(stat -f%z "$DASHBOARD_LOG" 2>/dev/null || stat -c%s "$DASHBOARD_LOG" 2>/dev/null || echo 0) -gt 10485760 ]; then
        mv "$DASHBOARD_LOG" "${DASHBOARD_LOG}.old"
        print_info "Rotated large dashboard log file"
    fi

    print_success "Cleanup complete"
}

# ============================================================================
# Docker Functions
# ============================================================================

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_info "Visit: https://docs.docker.com/get-docker/"
        return 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed."
        print_info "Visit: https://docs.docker.com/compose/install/"
        return 1
    fi
    return 0
}

# Function to get docker-compose command
get_docker_compose_cmd() {
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Function to start Docker services
docker_start() {
    local service=$1

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"

    # Check if .env.docker exists
    if [ ! -f ".env.docker" ]; then
        print_warning ".env.docker not found. Creating from example..."
        if [ -f ".env.docker.example" ]; then
            cp .env.docker.example .env.docker
            print_info "Please edit .env.docker with your configuration"
        else
            print_error ".env.docker.example not found"
            return 1
        fi
    fi

    local compose_cmd=$(get_docker_compose_cmd)

    if [ "$service" = "all" ]; then
        print_info "Starting all Docker services..."
        $compose_cmd --env-file .env.docker up -d
    else
        print_info "Starting Docker service: $service..."
        $compose_cmd --env-file .env.docker up -d "$service"
    fi

    if [ $? -eq 0 ]; then
        print_success "Docker services started"
        docker_status
    else
        print_error "Failed to start Docker services"
        return 1
    fi
}

# Function to stop Docker services
docker_stop() {
    local service=$1

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    if [ "$service" = "all" ]; then
        print_info "Stopping all Docker services..."
        $compose_cmd down
    else
        print_info "Stopping Docker service: $service..."
        $compose_cmd stop "$service"
    fi

    print_success "Docker services stopped"
}

# Function to restart Docker services
docker_restart() {
    local service=$1

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    if [ "$service" = "all" ]; then
        print_info "Restarting all Docker services..."
        $compose_cmd restart
    else
        print_info "Restarting Docker service: $service..."
        $compose_cmd restart "$service"
    fi

    print_success "Docker services restarted"
    docker_status
}

# Function to show Docker status
docker_status() {
    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    print_info "Docker Services Status:"
    echo "----------------------------------------"
    $compose_cmd ps
}

# Function to show Docker logs
docker_logs() {
    local service=$1
    local lines=${2:-50}

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    print_info "Showing last $lines lines of Docker logs for $service:"
    echo "----------------------------------------"
    $compose_cmd logs --tail="$lines" "$service"
}

# Function to follow Docker logs
docker_follow_logs() {
    local service=$1

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    print_info "Following Docker logs for $service (Ctrl+C to stop):"
    echo "----------------------------------------"
    $compose_cmd logs -f "$service"
}

# Function to build Docker images
docker_build() {
    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    print_info "Building Docker images..."
    $compose_cmd build

    if [ $? -eq 0 ]; then
        print_success "Docker images built successfully"
    else
        print_error "Failed to build Docker images"
        return 1
    fi
}

# Function to execute command in Docker container
docker_exec() {
    local service=$1
    shift
    local cmd="$@"

    if ! check_docker; then
        return 1
    fi

    cd "$PROJECT_ROOT"
    local compose_cmd=$(get_docker_compose_cmd)

    print_info "Executing command in $service container..."
    $compose_cmd exec "$service" $cmd
}

# Function to display help
show_help() {
    cat << EOF
${GREEN}Camera Trap Species Detection Platform - Service Manager${NC}

${YELLOW}Current Mode:${NC} $MODE (set SERVICE_MODE=docker to use Docker mode)

${YELLOW}Usage:${NC}
    $0 <command> [service] [options]
    SERVICE_MODE=docker $0 <command> [service] [options]

${YELLOW}Commands:${NC}
    start <service>     Start a service (dashboard, postgres, all)
    stop <service>      Stop a service (dashboard, postgres, all)
    restart <service>   Restart a service (dashboard, postgres, all)
    status [service]    Show status of service(s)
    logs <service>      Show recent logs (default: 50 lines)
    follow <service>    Follow logs in real-time
    cleanup             Clean up old logs and PID files (native mode only)
    build               Build Docker images (docker mode only)
    exec <service> <cmd> Execute command in Docker container (docker mode only)
    help                Show this help message

${YELLOW}Services:${NC}
    dashboard           Next.js web dashboard (port 3000)
    postgres            PostgreSQL database with PostGIS (port 5432, docker mode only)
    all                 All services

${YELLOW}Modes:${NC}
    native              Run services directly on host (npm, node, etc.)
    docker              Run services in Docker containers

${YELLOW}Examples - Native Mode:${NC}
    $0 start dashboard              # Start the dashboard with npm
    $0 start all                    # Start all services
    $0 stop dashboard               # Stop the dashboard
    $0 restart all                  # Restart all services
    $0 status                       # Show status of all services
    $0 logs dashboard               # Show last 50 lines of dashboard logs
    $0 logs dashboard 100           # Show last 100 lines
    $0 follow dashboard             # Follow dashboard logs in real-time
    $0 cleanup                      # Clean up old logs and PID files

${YELLOW}Examples - Docker Mode:${NC}
    SERVICE_MODE=docker $0 build                    # Build Docker images
    SERVICE_MODE=docker $0 start all                # Start all Docker services
    SERVICE_MODE=docker $0 start dashboard          # Start only dashboard
    SERVICE_MODE=docker $0 status                   # Show Docker container status
    SERVICE_MODE=docker $0 logs dashboard           # Show dashboard logs
    SERVICE_MODE=docker $0 follow postgres          # Follow PostgreSQL logs
    SERVICE_MODE=docker $0 exec dashboard sh        # Open shell in dashboard container
    SERVICE_MODE=docker $0 exec postgres psql -U species_admin -d species_detection
    SERVICE_MODE=docker $0 stop all                 # Stop all Docker services
    SERVICE_MODE=docker $0 restart dashboard        # Restart dashboard container

${YELLOW}Log Files:${NC}
    Dashboard: ${DASHBOARD_LOG}

${YELLOW}PID Files:${NC}
    Dashboard: ${DASHBOARD_PID}

${YELLOW}Notes:${NC}
    - Make sure to set up .env.local in the dashboard directory
    - Dashboard requires DATABASE_URL environment variable
    - Lambda functions run on AWS and are managed via AWS CLI/Terraform
    - RDS PostgreSQL is managed via AWS and accessed remotely

EOF
}

# Main command handler
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local command=$1
    shift

    case $command in
        start)
            if [ $# -eq 0 ]; then
                print_error "Service name required"
                print_info "Usage: $0 start <service>"
                if [ "$MODE" = "docker" ]; then
                    print_info "Available services: dashboard, postgres, all"
                else
                    print_info "Available services: dashboard, all"
                fi
                exit 1
            fi
            local service=$1
            if [ "$MODE" = "docker" ]; then
                docker_start "$service"
            else
                case $service in
                    dashboard)
                        start_dashboard
                        ;;
                    all)
                        start_all
                        ;;
                    *)
                        print_error "Unknown service: $service"
                        print_info "Available services: dashboard, all"
                        exit 1
                        ;;
                esac
            fi
            ;;
        stop)
            if [ $# -eq 0 ]; then
                print_error "Service name required"
                print_info "Usage: $0 stop <service>"
                exit 1
            fi
            local service=$1
            if [ "$MODE" = "docker" ]; then
                docker_stop "$service"
            else
                case $service in
                    dashboard)
                        stop_dashboard
                        ;;
                    all)
                        stop_all
                        ;;
                    *)
                        print_error "Unknown service: $service"
                        print_info "Available services: dashboard, all"
                        exit 1
                        ;;
                esac
            fi
            ;;
        restart)
            if [ $# -eq 0 ]; then
                print_error "Service name required"
                print_info "Usage: $0 restart <service>"
                exit 1
            fi
            if [ "$MODE" = "docker" ]; then
                docker_restart "$1"
            else
                restart_service "$1"
            fi
            ;;
        status)
            if [ "$MODE" = "docker" ]; then
                docker_status
            else
                if [ $# -eq 0 ]; then
                    status_all
                else
                    case $1 in
                        dashboard)
                            status_dashboard
                            ;;
                        all)
                            status_all
                            ;;
                        *)
                            print_error "Unknown service: $1"
                            print_info "Available services: dashboard, all"
                            exit 1
                            ;;
                    esac
                fi
            fi
            ;;
        logs)
            if [ $# -eq 0 ]; then
                print_error "Service name required"
                print_info "Usage: $0 logs <service> [lines]"
                exit 1
            fi
            if [ "$MODE" = "docker" ]; then
                docker_logs "$1" "${2:-50}"
            else
                show_logs "$1" "${2:-50}"
            fi
            ;;
        follow)
            if [ $# -eq 0 ]; then
                print_error "Service name required"
                print_info "Usage: $0 follow <service>"
                exit 1
            fi
            if [ "$MODE" = "docker" ]; then
                docker_follow_logs "$1"
            else
                follow_logs "$1"
            fi
            ;;
        build)
            if [ "$MODE" = "docker" ]; then
                docker_build
            else
                print_error "Build command is only available in Docker mode"
                print_info "Use: SERVICE_MODE=docker $0 build"
                exit 1
            fi
            ;;
        exec)
            if [ "$MODE" = "docker" ]; then
                if [ $# -lt 2 ]; then
                    print_error "Service name and command required"
                    print_info "Usage: SERVICE_MODE=docker $0 exec <service> <command>"
                    exit 1
                fi
                docker_exec "$@"
            else
                print_error "Exec command is only available in Docker mode"
                print_info "Use: SERVICE_MODE=docker $0 exec <service> <command>"
                exit 1
            fi
            ;;
        cleanup)
            if [ "$MODE" = "docker" ]; then
                print_warning "Cleanup is not needed in Docker mode"
            else
                cleanup
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
