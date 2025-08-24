# onewAy - Prototype 2 Planning Checklist

---

## Phase One: Project Setup

- [x] Setup project skeleton and initialize Git
- [x] Create `requirements.txt`
- [x] Configure PostgreSQL for FastAPI
- [x] Add Tailwind + Flowbite

## Phase Two: Authentication

### server/backend

- [x] Add database model Client
- [x] Setup Alembic
~~- [ ] Setup timer lifecycle and client `alive` tracking~~
- [x] Implement client authentication endpoints:
  - [x] `/client/auth/enroll`
  - [x] `/client/auth/login`
  - [x] `/client/auth/refresh`
- [x] Implement JWT-based access and refresh tokens:
  - [x] Define token structure and claims (sub, exp, iat)
  - [x] Create refresh token database model and secure storage
  - [x] Implement token expiration and rotation policy
  - [x] Add revocation logic
- [x] Write unit tests for authentication routes
- [x] Write fixtures for test database

### client

- [x] Implement a custom logger
- [x] Implement HTTP API client
- [x] Implement system metadata collection
- [x] Implement authentication lifecycle:
  - [x] Enroll on first run
  - [x] Login on subsequent runs
  - [x] Refresh token if access token is expired
- [x] Write tests for information processing and lifecycle events

### server/frontend

- [x] Setup global state management with Zustand
- [x] Create `APIClient.ts` with generic types
- [x] Create the `LoginPanel` component
- [x] Create the `RegisterPanel` component
- [x] Setup protected routes and routes to existing components
- [x] Write tests for:
  - [x] Login form input and submission logic
  - [x] Zustand store behavior (e.g., token set/reset)
  - [x] Protected route access control

## Phase Three: Dashboard and Websockets

### server/backend

- [ ] Add `/client/all`
- [ ] Add websockets to FastAPI
- [ ] Write websocket tests

### server/frontend

- [ ] Create basic dashboard and implement websockets
- [ ] Create dashboard test

## Phase Four: Client Modules & Update System

### server/backend

- [ ] Create endpoints for core update
- [ ] Create module datatypes
- [ ] Create endpoints for module CRUD
- [ ] Add testing for update backend and module CRUD

### client

- [ ] Implement module datatypes
- [ ] Implement module lifecycle
- [ ] Add update functionality
- [ ] Add update testing a test modules

### server/frontend

- [ ] Create the following user journey (basic) login->dashboard->select specific device->see advanced device info->CRUD module interface
- [ ] Add CRUD module interface testing
