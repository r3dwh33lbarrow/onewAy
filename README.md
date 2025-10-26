<picture>
  <source media="(prefers-color-scheme: dark)" srcset="logos/onewAy_logo_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="logos/onewAy_logo_light.png">
  <img alt="onewAy logo" src="logos/onewAy_logo_light.png" height="100">
</picture>

# onewAy

> ⚠️ This project is still a work in progress

onewAy is a modern red-team module orchestration for Windows, macOS, and Linux targets. onewAy delivers a FastAPI backend, a Rust agent, and a React/Vite frontend for building, deploying, and operating offensive tooling. Inspired by Armitage, the project focuses on custom executable modules that can be packaged and distributed to remote clients. The codebase is actively developed—APIs and UI flows may change as the platform evolves.

## Key Features

- **Client Builder**: Generate per-target bundles that embed credentials, selected modules, and platform-specific builds (Windows, macOS, Linux).
- **Module Runtime**: The Rust client authenticates, pulls module instructions over WebSockets, executes binaries, and streams stdout/stderr/events back to operators.
- **Web Console**: Operators can trigger modules, send stdin, revoke credentials, and observe output in real time from the React dashboard.
- **Security Controls**:
  - Access/refresh token rotation with one-click revocation.
  - Automatic WebSocket heartbeats (ping/pong) and cleanup of non-responsive clients.
  - Forced credential resets when regenerating clients.
- **Resource Packaging**: Client bundles only contain the referenced module binaries and configuration, reducing distribution size.

Documentation for specific topics lives in `docs/`:

- [`docs/BACKEND_SETTINGS.md`](docs/BACKEND_SETTINGS.md) – `config.toml` reference.
- [`docs/MODULES.md`](docs/MODULES.md) – module directory layout and workflows.
- [`docs/MODULE_CONFIG.md`](docs/MODULE_CONFIG.md) – `config.yaml` schema.
- [`docs/DOCKER.md`](docs/DOCKER.md) - specific information on docker configuration and setting up docker on the network.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Rust toolchain (stable)
- PostgreSQL 14+
- `libmagic` (required by the backend)

### Clone the repository

```bash
git clone https://github.com/r3dwh33lbarrow/onewAy.git
cd onewAy
```

### Docker one-step environment

Launch the full stack (PostgreSQL, backend, frontend) with Docker Compose:

```bash
cd docker
docker compose up --build
```

During startup the container prompts you for the PostgreSQL password and the JWT `SECURITY_SECRET_KEY`. Press Enter to auto-generate strong random values or provide your own secrets. In non-interactive environments you can pre-set `POSTGRES_PASSWORD` and `SECURITY_SECRET_KEY` in your shell. The database boots with a temporary password (`changeme`) and the start script will rotate it to whatever you provide.

The container installs the Rust toolchain with cross-compilation targets for Windows (`x86_64-pc-windows-gnu`) and Linux (`x86_64-unknown-linux-gnu`).

### Backend (FastAPI)

```bash
cd server/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure PostgreSQL and other settings
cp config.toml.example config.toml
# edit config.toml as needed – see docs/BACKEND_SETTINGS.md

# Run migrations (if needed)
alembic upgrade head

# Start the API (http://127.0.0.1:8000)
uvicorn app.main:app --reload
```

### Frontend (React + Vite)

```bash
cd server/frontend
npm install
npm run dev
```

The development server typically runs at [http://127.0.0.1:5173](http://127.0.0.1:5173).

### Rust Client
Should be generated automatically by the frontend but can be compiled directly to the desired supported platform.

## Usage Highlights

- **Module Packaging**: Place each module under `modules/<module_name>/` with a `config.yaml`. Only binaries referenced under `binaries.<platform>` are copied into generated client bundles. See [`docs/MODULE_CONFIG.md`](docs/MODULE_CONFIG.md) for details.
- **Client Builder**: From the UI, pre-select modules, credentials, and desired platform. The backend compiles the Rust client with tailored environment variables and ships a zip containing the client binary, config, and selected modules.
- **Token Revocation**: Revoking a client invalidates all refresh tokens, forces a password reset, and disconnects WebSockets immediately.

## Testing & Tooling

- Backend tests live under `server/backend/tests/`; run with `pytest` (ensure `testing = true` in `config.toml`).
- Client integration tests under `client/tests/` expect the backend in testing mode.
- Frontend tests can be added under `server/frontend/src/__tests__/`.

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.
