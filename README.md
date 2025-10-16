onewAy
========

+    onewAy is designed as a modern, red team module manager inspired by Armitage. In this context a module can be any executable that can be run on a target machine. Just by running the client on a target machine you can create an upload any of your own modules (executables). This project is heavily a **work in progress**! The end goal for this project is to have most of the same functionality of Armitage more specifically the integration with Metasploit. Currently this project only supports custom modules and does not integrate at all with Metasploit.

Other docs:
- docs/BACKEND_SETTINGS.md — Backend config (config.toml)
- docs/MODULES.md — Modules directory and workflows
- docs/MODULE_CONFIG.md — Module config.yaml schema and examples

Architecture
------------
- Python FastAPI backend (HTTP + WebSockets)
- Rust client (executes modules, streams stdout/stderr, receives commands)
- TypeScript React frontend (console view, module management)
- Backend exposes REST endpoints for auth, modules, and client/user WebSockets.
- Client authenticates, receives run/cancel/stdin commands over WS, runs binaries, and streams output and events back.
- Frontend connects as a user WebSocket client, renders console output and module events, and can send stdin.

Quickstart
----------
Prerequisites: Python 3.11+, Node 20+, Rust stable, PostgreSQL.

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

Naming Conventions
----------------
- Names are normalized across layers:
  - Backend/DB: `snake_case` (e.g., `test_module`)
  - Routes: `kebab-case` (e.g., `/test-module`)
  - Frontend TS: `camelCase` (e.g., `testModule`)
  - Display: free-form (e.g., `Test Module`)

Testing
-------
- Backend tests live under `server/backend/tests/`.
- You can run them with the configured test environment; see `server/backend/pytest.ini`.

License
-------
ADD
