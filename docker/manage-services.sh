#!/usr/bin/env bash
set -euo pipefail

# Load environment variables from .env file
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default HOST_PUBLIC to false if not set
HOST_PUBLIC=${HOST_PUBLIC:-false}

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

# Function to start services
start_services() {
    if [[ "${HOST_PUBLIC}" == "true" ]]; then
        log "Starting services with public network access"
        
        # Detect host IP for better instructions
        HOST_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_HOST_IP")
        
        log "Backend will be accessible at: ${HOST_IP}:${BACKEND_PORT:-8000}"
        log "Frontend will be accessible at: ${HOST_IP}:${FRONTEND_PORT:-5173}"
        
        # Use both base compose file and public overlay
        docker compose -f docker-compose.yml -f docker-compose.public.yml up -d
        
        # Show the IP address for easy access
        log "Services started! Access your application at:"
        log "  From this Mac:     http://localhost:${BACKEND_PORT:-8000} (Backend) | http://localhost:${FRONTEND_PORT:-5173} (Frontend)"
        log "  From VMs/Network:  http://${HOST_IP}:${BACKEND_PORT:-8000} (Backend) | http://${HOST_IP}:${FRONTEND_PORT:-5173} (Frontend)"
        log ""
        log "  PostgreSQL is internal only (not exposed on public network)"
        log ""
        log "Note: On macOS, Docker containers are in a VM. VMs on your network should use your Mac's IP (${HOST_IP})."
        
    else
        log "Starting services with localhost access only"
        log "Backend will be accessible at: localhost:${BACKEND_PORT:-8000}"
        log "Frontend will be accessible at: localhost:${FRONTEND_PORT:-5173}"
        
        # Use only the base compose file
        docker compose -f docker-compose.yml up -d
        
        log "Services started! Access your application at:"
        log "  Backend API: http://localhost:${BACKEND_PORT:-8000}"
        log "  Frontend:    http://localhost:${FRONTEND_PORT:-5173}"
        log "  PostgreSQL:  localhost:${POSTGRES_PORT:-5432} (for direct DB access)"
    fi
}

# Function to stop services
stop_services() {
    log "Stopping services..."
    if [[ "${HOST_PUBLIC}" == "true" ]]; then
        docker compose -f docker-compose.yml -f docker-compose.public.yml down
    else
        docker compose -f docker-compose.yml down
    fi
    log "Services stopped."
}

# Function to show logs
show_logs() {
    if [[ "${HOST_PUBLIC}" == "true" ]]; then
        docker compose -f docker-compose.yml -f docker-compose.public.yml logs -f
    else
        docker compose -f docker-compose.yml logs -f
    fi
}

# Function to show status
show_status() {
    log "Current configuration:"
    log "  HOST_PUBLIC: ${HOST_PUBLIC}"
    log "  BACKEND_PORT: ${BACKEND_PORT:-8000}"
    log "  FRONTEND_PORT: ${FRONTEND_PORT:-5173}"
    log "  POSTGRES_PORT: ${POSTGRES_PORT:-5432}"
    
    if [[ "${HOST_PUBLIC}" == "true" ]]; then
        log "  Network mode: Public IP (172.20.0.0/16)"
        log "  App container IP: 172.20.0.10"
    else
        log "  Network mode: Localhost only"
    fi
    
    echo
    if [[ "${HOST_PUBLIC}" == "true" ]]; then
        docker compose -f docker-compose.yml -f docker-compose.public.yml ps
    else
        docker compose -f docker-compose.yml ps
    fi
}

# Main command handling
case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status}"
        echo ""
        echo "Environment variables:"
        echo "  HOST_PUBLIC=true   - Expose services on public IP (172.20.0.10)"
        echo "  HOST_PUBLIC=false  - Expose services on localhost only (default)"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start with localhost access"
        echo "  HOST_PUBLIC=true $0 start   # Start with public IP access"
        echo "  $0 status                   # Show current status"
        exit 1
        ;;
esac