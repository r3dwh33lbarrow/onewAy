# OnewAy Project

## Project Overview

This project is a client-server application designed to manage and execute modules on remote clients. It consists of three main components:

*   **Backend:** A Python-based API built with FastAPI that serves as the central control server.
*   **Frontend:** A React and TypeScript web interface for managing clients and modules.
*   **Client:** A Rust-based application that runs on client machines, communicates with the backend, and executes modules.

### Architecture

The backend exposes a REST API and WebSocket endpoints for communication with the frontend and clients. The frontend provides a user interface for administrators to monitor and manage clients and modules. The client application runs on remote machines, enrolls with the server, and then communicates over WebSockets to receive commands and execute modules.

## Building and Running

### Backend (Python/FastAPI)

*   **Dependencies:** Install dependencies from `server/backend/requirements.txt`:
    ```bash
    pip install -r server/backend/requirements.txt
    ```
*   **Database Migrations:** Apply database migrations using Alembic:
    ```bash
    alembic -c server/backend/alembic.ini upgrade head
    ```
*   **Running:** Run the FastAPI development server:
    ```bash
    uvicorn app.main:app --reload --ws-ping-interval 300 --ws-ping-timeout 300 --host 0.0.0.0
    ```

### Frontend (React/TypeScript)

*   **Dependencies:** Install dependencies from `server/frontend/package.json`:
    ```bash
    npm install --prefix server/frontend
    ```
*   **Running:** Start the Vite development server:
    ```bash
    npm run dev --prefix server/frontend
    ```
*   **Building:** Build the production-ready frontend:
    ```bash
    npm run build --prefix server/frontend
    ```
*   **Testing:** Run tests:
    ```bash
    npm run test --prefix server/frontend
    ```

### Client (Rust)

*   **Dependencies:** The dependencies are managed by Cargo.
*   **Building:** Build the client application:
    ```bash
    cargo build --manifest-path client/Cargo.toml
    ```
*   **Running:** Run the client application:
    ```bash
    cargo run --manifest-path client/Cargo.toml
    ```

## Development Conventions

### Module Naming

The project uses different naming conventions for modules across its components:

*   **Frontend (TypeScript):** `camelCase` (e.g., `testModule`)
*   **Backend (Python):** `snake_case` (e.g., `test_module`)
*   **URL Endpoints:** `kebab-case` (e.g., `test-module`)

### Modules

Modules are defined by YAML configuration files and can be added to the system via the `/user/modules/add` backend endpoint. The `docs/MODULES.md` file provides more details on the module structure.
