onewAy
========

A multi-component system for running and streaming output from modules across clients.

- Python FastAPI backend (HTTP + WebSockets)
- Rust client (executes modules, streams stdout/stderr, receives commands)
- TypeScript React frontend (console view, module management)

Useful docs:
- docs/BACKEND_SETTINGS.md — Backend config (config.toml)
- docs/MODULES.md — Modules directory and workflows
- docs/MODULE_CONFIG.md — Module config.yaml schema and examples

Architecture
------------
- Backend exposes REST endpoints for auth, modules, and client/user WebSockets.
- Client authenticates, receives run/cancel/stdin commands over WS, runs binaries, and streams output and events back.
- Frontend connects as a user WebSocket client, renders console output and module events, and can send stdin.

Quickstart
----------
Prerequisites: Python 3.11+, Node 20+, Rust stable, PostgreSQL.

### Docker one-step environment

You can spin up a full development environment (PostgreSQL, backend, and Vite frontend on http://127.0.0.1:5173) with Docker:

```
./scripts/start_dev_container.sh
```

The script relies on Docker Compose v2. If the repository does not have a remote configured, export `REPO_URL` with the Git URL to clone before running it. Once the stack is running, you can visit the frontend at `http://127.0.0.1:5173` and the backend API at `http://127.0.0.1:8000`.

Backend (FastAPI)
-----------------
- Configure `server/backend/config.toml` (database, security, paths). See docs/BACKEND_SETTINGS.md.
- Create DB and run migrations (if applicable):
  - From `server/backend/`: `alembic upgrade head`
- Install and run:
  - From `server/backend/`: `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - Dev server: `uvicorn app.main:app --reload` (or `fastapi dev app/main.py`)
- API root: `http://127.0.0.1:8000/` returns `{ "message": "onewAy API" }`.

Frontend (React + Vite)
-----------------------
- From `server/frontend/`: `npm install`
- Dev server: `npm run dev` (typically http://127.0.0.1:5173)
- In the UI, set the API URL (Settings) to your backend URL, e.g. `http://127.0.0.1:8000`.

Rust Client
-----------
- Configure `client/config.toml`:
  - `[module]` `modules_directory` (defaults to `[CURRENT_DIR]/../modules`)
  - `[auth]` `username`, `password`, `enrolled`
- The client connects to `http://127.0.0.1:8000` and `ws://127.0.0.1:8000/ws-client` by default (see `client/src/main.rs`).
- From `client/`: `cargo run`

Modules
-------
- Place modules under `modules/`, each module in its own folder with a `config.yaml`.
- See docs/MODULE_CONFIG.md for the schema and examples.
- Manage modules via backend endpoints:
  - `PUT /module/upload` — upload module folder
  - `PUT /module/add` — add by local path on backend host
  - `PUT /module/update/{module_name}` — replace module files + config
  - `DELETE /module/delete/{module_name}` — remove module

WebSockets
----------
- Users: `ws://<api>/ws-user` (token via `/ws-user-token`)
- Clients: `ws://<api>/ws-client` (token via `/ws-client-token`)
- Message shapes align with:
  - Frontend types: `server/frontend/src/schemas/websockets.ts`
  - Rust client types: `client/src/schemas/websockets.rs`

Development Tips
----------------
- Names are normalized across layers:
  - Backend/DB: `snake_case` (e.g., `test_module`)
  - Routes: `kebab-case` (e.g., `/test-module`)
  - Frontend TS: `camelCase` (e.g., `testModule`)
  - Display: free-form (e.g., `Test Module`)
- Exit codes are forwarded on `module_exit` events and rendered by the console UI.

Testing
-------
- Backend tests live under `server/backend/tests/`.
- You can run them with the configured test environment; see `server/backend/pytest.ini`.

License
-------
- See project license (if applicable).

