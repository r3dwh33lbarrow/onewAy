#!/usr/bin/env bash
set -euo pipefail

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

# --- Default values ---
REPO_URL=${REPO_URL:-https://github.com/r3dwh33lbarrow/onewAy.git}
REPO_REF=${REPO_REF:-main}
PROJECT_DIR=${PROJECT_DIR:-/workspace/oneway}
POSTGRES_HOST=${POSTGRES_HOST:-oneway-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-oneway}
POSTGRES_USER=${POSTGRES_USER:-onewayuser}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
CLIENT_VERSION=${CLIENT_VERSION:-0.1.0}
SECURITY_SECRET_KEY=${SECURITY_SECRET_KEY:-}
SECRETS_DIR=${SECRETS_DIR:-/workspace/.secrets}
ORIGINAL_POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"

# --- Secret persistence functions ---
save_secret() {
    local secret_name=$1
    local secret_value=$2
    echo -n "${secret_value}" > "${SECRETS_DIR}/${secret_name}"
    chmod 600 "${SECRETS_DIR}/${secret_name}"
}

load_secret() {
    local secret_name=$1
    if [[ -f "${SECRETS_DIR}/${secret_name}" ]]; then
        cat "${SECRETS_DIR}/${secret_name}"
    fi
}

# --- Prompt interactively for sensitive secrets ---
generate_secret() {
    python - <<'PY'
import secrets, string

alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
print("".join(secrets.choice(alphabet) for _ in range(32)))
PY
}

generate_password() {
    python - <<'PY'
import secrets, string

alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
print("".join(secrets.choice(alphabet) for _ in range(24)))
PY
}

# Load persisted secrets if they exist
PERSISTED_PASSWORD=$(load_secret "postgres_password")
PERSISTED_SECRET_KEY=$(load_secret "security_secret_key")

if [ -t 0 ]; then
    echo ""
    # Use persisted password if available and not overridden
    if [[ -n "${PERSISTED_PASSWORD}" ]] && [[ "${POSTGRES_PASSWORD}" == "changeme" ]]; then
        POSTGRES_PASSWORD="${PERSISTED_PASSWORD}"
        log "Using persisted PostgreSQL password."
    elif [[ -z "${POSTGRES_PASSWORD}" || "${POSTGRES_PASSWORD}" == "changeme" ]]; then
        read -rsp "Enter PostgreSQL password (leave blank to auto-generate): " input_pw
        echo ""
        if [[ -n "${input_pw}" ]]; then
            POSTGRES_PASSWORD="${input_pw}"
        else
            POSTGRES_PASSWORD="$(generate_password)"
            echo "Generated PostgreSQL password."
        fi
    fi
    export POSTGRES_PASSWORD

    # Use persisted secret key if available
    if [[ -n "${PERSISTED_SECRET_KEY}" ]] && [[ -z "${SECURITY_SECRET_KEY}" ]]; then
        SECURITY_SECRET_KEY="${PERSISTED_SECRET_KEY}"
        log "Using persisted SECURITY_SECRET_KEY."
    elif [[ -z "${SECURITY_SECRET_KEY}" ]]; then
        read -rsp "Enter SECURITY_SECRET_KEY (leave blank to auto-generate): " input_sk
        echo ""
        if [[ -n "${input_sk}" ]]; then
            SECURITY_SECRET_KEY="${input_sk}"
        else
            SECURITY_SECRET_KEY="$(generate_secret)"
            echo "Generated SECURITY_SECRET_KEY."
        fi
    fi
    export SECURITY_SECRET_KEY
else
    # Non-interactive mode: use persisted or generate
    if [[ -n "${PERSISTED_PASSWORD}" ]] && [[ "${POSTGRES_PASSWORD}" == "changeme" || -z "${POSTGRES_PASSWORD}" ]]; then
        POSTGRES_PASSWORD="${PERSISTED_PASSWORD}"
        log "Using persisted PostgreSQL password for non-interactive session."
    elif [[ -z "${POSTGRES_PASSWORD}" || "${POSTGRES_PASSWORD}" == "changeme" ]]; then
        POSTGRES_PASSWORD="$(generate_password)"
        log "Auto-generated PostgreSQL password for non-interactive session."
    fi
    
    if [[ -n "${PERSISTED_SECRET_KEY}" ]] && [[ -z "${SECURITY_SECRET_KEY}" ]]; then
        SECURITY_SECRET_KEY="${PERSISTED_SECRET_KEY}"
        log "Using persisted SECURITY_SECRET_KEY for non-interactive session."
    elif [[ -z "${SECURITY_SECRET_KEY}" ]]; then
        SECURITY_SECRET_KEY="$(generate_secret)"
        log "Auto-generated SECURITY_SECRET_KEY for non-interactive session."
    fi
    export POSTGRES_PASSWORD SECURITY_SECRET_KEY
fi

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

log "Installing backend dependencies"
if [[ -f "server/backend/requirements.txt" ]]; then
    python -m pip install --upgrade pip
    python -m pip install -r server/backend/requirements.txt
else
    log "Warning: server/backend/requirements.txt not found, skipping Python package installation"
fi

log "Installing frontend dependencies"
if [[ -d "server/frontend" ]]; then
    cd server/frontend
    npm install
    cd "${PROJECT_DIR}"
else
    log "Warning: server/frontend directory not found, skipping npm install"
fi

log "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}"
export PGPASSWORD="${ORIGINAL_POSTGRES_PASSWORD}"
max_attempts=30
attempt=0

# Function to test PostgreSQL connection
test_postgres() {
    # Try pg_isready first
    if command -v pg_isready >/dev/null 2>&1; then
        pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1
    else
        # Fallback to psql if pg_isready is not available
        psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT 1;" >/dev/null 2>&1
    fi
}

until test_postgres; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        log "PostgreSQL connection timed out after ${max_attempts} attempts"
        # Try to show what's available for debugging
        log "Network connectivity test:"
        nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}" || log "Cannot connect to ${POSTGRES_HOST}:${POSTGRES_PORT}"
        exit 1
    fi
    sleep 2
    log "PostgreSQL is not ready yet... (attempt ${attempt}/${max_attempts})"
done
log "PostgreSQL is ready!"

# Update database password if needed
if [[ "${POSTGRES_PASSWORD}" != "${ORIGINAL_POSTGRES_PASSWORD}" ]]; then
    log "Updating PostgreSQL password for user '${POSTGRES_USER}'"
    if PGPASSWORD="${ORIGINAL_POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -c "ALTER ROLE \"${POSTGRES_USER}\" WITH PASSWORD '${POSTGRES_PASSWORD}';" >/dev/null 2>&1; then
        log "Database password updated successfully."
        export PGPASSWORD="${POSTGRES_PASSWORD}"
    else
        log "Failed to update PostgreSQL password; using original password."
        POSTGRES_PASSWORD="${ORIGINAL_POSTGRES_PASSWORD}"
        export PGPASSWORD="${POSTGRES_PASSWORD}"
    fi
else
    export PGPASSWORD="${POSTGRES_PASSWORD}"
fi

# Now write the config file with the final confirmed password
CONFIG_FILE="server/backend/config.toml"
log "Writing backend config to ${CONFIG_FILE}"
mkdir -p "$(dirname "${CONFIG_FILE}")"
cat > "${CONFIG_FILE}" <<CONFIG
[app]
debug = false
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
resources_dir = "[ROOT]/server/backend/app/resources"

[other]
max_avatar_size_mb = 2
CONFIG

# Persist secrets for future container restarts
save_secret "postgres_password" "${POSTGRES_PASSWORD}"
save_secret "security_secret_key" "${SECURITY_SECRET_KEY}"
log "Secrets persisted to ${SECRETS_DIR}"

log "Running Alembic migrations"
if [[ -d "server/backend" ]]; then
    cd server/backend
    if [[ -f "alembic.ini" ]]; then
        alembic upgrade head
    else
        log "Warning: alembic.ini not found, skipping migrations"
    fi
else
    log "Warning: server/backend directory not found, skipping migrations"
fi

start_backend() {
    log "Starting backend on port ${BACKEND_PORT}"
    cd "${PROJECT_DIR}/server/backend"
    uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
}

start_frontend() {
    log "Starting frontend (Vite) on port ${FRONTEND_PORT}"
    cd "${PROJECT_DIR}/server/frontend"
    npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" --strictPort
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

while true; do
    if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
        log "Backend process (PID ${BACKEND_PID}) has exited"
        wait "${BACKEND_PID}" || EXIT_CODE=$?
        break
    fi
    if ! kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
        log "Frontend process (PID ${FRONTEND_PID}) has exited"
        wait "${FRONTEND_PID}" || EXIT_CODE=$?
        break
    fi
    sleep 1
done

log "A service exited with code ${EXIT_CODE}. Shutting down."
kill "${BACKEND_PID}" "${FRONTEND_PID}" >/dev/null 2>&1 || true
wait || true
exit "${EXIT_CODE}"