#!/usr/bin/env bash
set -euo pipefail

log() {
    echo "[$(date --iso-8601=seconds)] $*"
}

REPO_URL=${REPO_URL:-}
if [[ -z "${REPO_URL}" ]]; then
    log "Environment variable REPO_URL is required"
    exit 1
fi

REPO_REF=${REPO_REF:-main}
PROJECT_DIR=${PROJECT_DIR:-/workspace/oneway}
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-oneway}
POSTGRES_USER=${POSTGRES_USER:-oneway}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-oneway}
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
CLIENT_VERSION=${CLIENT_VERSION:-0.1.0}
SECURITY_SECRET_KEY=${SECURITY_SECRET_KEY:-dev-secret}

mkdir -p "${PROJECT_DIR}"

remote_ref_exists() {
    git ls-remote --exit-code "${REPO_URL}" "refs/heads/${1}" >/dev/null 2>&1 || \
        git ls-remote --exit-code "${REPO_URL}" "refs/tags/${1}" >/dev/null 2>&1
}

if [[ ! -d "${PROJECT_DIR}/.git" ]]; then
    log "Cloning repository ${REPO_URL} (ref: ${REPO_REF})"
    if remote_ref_exists "${REPO_REF}"; then
        git clone --branch "${REPO_REF}" --depth 1 "${REPO_URL}" "${PROJECT_DIR}" || {
            log "Failed to clone repository"
            exit 1
        }
    else
        log "Reference ${REPO_REF} not found, cloning default branch"
        git clone --depth 1 "${REPO_URL}" "${PROJECT_DIR}" || {
            log "Failed to clone repository"
            exit 1
        }
        git -C "${PROJECT_DIR}" checkout "${REPO_REF}" >/dev/null 2>&1 || true
    fi
else
    log "Repository already present. Fetching updates"
    git -C "${PROJECT_DIR}" fetch origin --prune
    if remote_ref_exists "${REPO_REF}"; then
        git -C "${PROJECT_DIR}" checkout "${REPO_REF}" >/dev/null 2>&1 || \
            git -C "${PROJECT_DIR}" checkout -B "${REPO_REF}" "origin/${REPO_REF}" || true
        git -C "${PROJECT_DIR}" reset --hard "origin/${REPO_REF}" || true
    else
        git -C "${PROJECT_DIR}" pull --ff-only || true
    fi
fi

cd "${PROJECT_DIR}"

CONFIG_FILE="server/backend/config.toml"
if [[ ! -f "${CONFIG_FILE}" ]]; then
    log "Generating backend config at ${CONFIG_FILE}"
    cat > "${CONFIG_FILE}" <<CONFIG
[app]
debug = true
client_version = "${CLIENT_VERSION}"

[cors]
allow_origins = ["http://127.0.0.1:${FRONTEND_PORT}", "http://localhost:${FRONTEND_PORT}"]

[database]
url = "postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
pool_size = 10
pool_timeout = 30
echo = false

[security]
secret_key = "${SECURITY_SECRET_KEY}"
algorithm = "HS256"
access_token_expires_minutes = 60
refresh_token_expires_days = 7
jwt_issuer = "http://127.0.0.1:${BACKEND_PORT}"
jwt_audience = "onewAy-api"

[paths]
client_dir = "[ROOT]/client"
module_dir = "[ROOT]/modules"
avatar_dir = "[ROOT]/server/backend/app/resources/avatars"

[other]
max_avatar_size_mb = 2

[testing]
testing = false

[testing.database]
url = ""
pool_size = 10
pool_timeout = 30
echo = false

[testing.security]
secret_key = ""
algorithm = "HS256"
access_token_expires_minutes = 15
refresh_token_expires_days = 7

[testing.paths]
client_dir = "[ROOT]/client"
module_dir = "[ROOT]/server/backend/tests/modules"
avatar_dir = "[ROOT]/server/backend/tests/resources/avatars"
CONFIG
else
    log "Backend config already exists, skipping generation"
fi

log "Installing backend dependencies"
python -m pip install --upgrade pip
python -m pip install -r server/backend/requirements.txt

log "Installing frontend dependencies"
cd server/frontend
npm install
cd "${PROJECT_DIR}"

log "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}"
export PGPASSWORD="${POSTGRES_PASSWORD}"
until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; do
    sleep 1
    log "PostgreSQL is not ready yet..."
done

log "Running Alembic migrations"
cd server/backend
alembic upgrade head

start_backend() {
    log "Starting backend on port ${BACKEND_PORT}"
    uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload
}

start_frontend() {
    log "Starting frontend (Vite) on port ${FRONTEND_PORT}"
    cd "${PROJECT_DIR}/server/frontend"
    npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
}

trap_handler() {
    log "Received termination signal. Stopping services..."
    pkill -P $$ || true
    wait
}

trap trap_handler TERM INT

start_backend &
BACKEND_PID=$!

start_frontend &
FRONTEND_PID=$!

log "Backend PID: ${BACKEND_PID}, Frontend PID: ${FRONTEND_PID}"
EXIT_CODE=0
if [[ ${BASH_VERSINFO[0]} -gt 4 || ( ${BASH_VERSINFO[0]} -eq 4 && ${BASH_VERSINFO[1]} -ge 3 ) ]]; then
    set +e
    wait -n
    EXIT_CODE=$?
    set -e
else
    while true; do
        if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
            wait "${BACKEND_PID}" || EXIT_CODE=$?
            break
        fi
        if ! kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
            wait "${FRONTEND_PID}" || EXIT_CODE=$?
            break
        fi
        sleep 1
    done
fi

log "A service exited with code ${EXIT_CODE}. Shutting down."
kill "${BACKEND_PID}" "${FRONTEND_PID}" >/dev/null 2>&1 || true
wait || true
exit "${EXIT_CODE}"
