#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
COMPOSE_FILE="${PROJECT_ROOT}/ops/docker/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
    echo "Could not find docker-compose file at ${COMPOSE_FILE}" >&2
    exit 1
fi

if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD=(docker-compose)
    else
        echo "Docker Compose is not installed. Install Docker Compose v2 or docker-compose." >&2
        exit 1
    fi
else
    echo "Docker is not installed or not available in PATH." >&2
    exit 1
fi

DEFAULT_REPO_URL="${REPO_URL:-}"
if [[ -z "${DEFAULT_REPO_URL}" ]]; then
    DEFAULT_REPO_URL=$(git -C "${PROJECT_ROOT}" config --get remote.origin.url 2>/dev/null || true)
fi

if [[ -z "${DEFAULT_REPO_URL}" ]]; then
    cat >&2 <<'MSG'
REPO_URL is not set and could not be determined from the current repository.
Please export REPO_URL with the Git URL you want to clone, for example:

  export REPO_URL="https://github.com/your-org/onewAy.git"

Then re-run this script.
MSG
    exit 1
fi

export REPO_URL="${DEFAULT_REPO_URL}"
export REPO_REF="${REPO_REF:-main}"
export POSTGRES_DB="${POSTGRES_DB:-oneway}"
export POSTGRES_USER="${POSTGRES_USER:-oneway}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-oneway}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"
export FRONTEND_PORT="${FRONTEND_PORT:-5173}"
export CLIENT_VERSION="${CLIENT_VERSION:-0.1.0}"
export SECURITY_SECRET_KEY="${SECURITY_SECRET_KEY:-dev-secret}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-oneway}"

cd "${PROJECT_ROOT}"
"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" up --build -d

cat <<EOF
Docker services are starting in the background.

Frontend: http://127.0.0.1:${FRONTEND_PORT}
Backend:  http://127.0.0.1:${BACKEND_PORT}
Postgres: 127.0.0.1:${POSTGRES_PORT}

Follow logs with:
  ${COMPOSE_CMD[*]} -f ${COMPOSE_FILE} logs -f
Stop services with:
  ${COMPOSE_CMD[*]} -f ${COMPOSE_FILE} down
EOF
