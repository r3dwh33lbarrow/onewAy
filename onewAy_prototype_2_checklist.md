# onewAy - Prototype 2 Planning Checklist

---

## Phase One: Project Setup _(July 23 – July 25)_

- [x] Setup project skeleton and initialize Git
- [x] Create `requirements.txt`
- [x] Configure PostgreSQL for FastAPI
- [x] Add Tailwind + Flowbite

## Phase Two: Authentication _(July 26 – August 15)_

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
- [ ] Implement system metadata collection
- [ ] Implement authentication lifecycle:
  - [ ] Enroll on first run
  - [ ] Login on subsequent runs
  - [ ] Refresh token if access token is expired
- [ ] Write tests for information processing and lifecycle events

### server/frontend

- [ ] Setup global state management with Zustand
- [ ] Create `APIClient.ts` with generic types
- [ ] Create the `LoginPanel` component
- [ ] Create the `RegisterPanel` component
- [ ] Setup protected routes and routes to existing components
- [ ] Write tests for:
  - [ ] Login form input and submission logic
  - [ ] Zustand store behavior (e.g., token set/reset)
  - [ ] Protected route access control

## Phase Three: Dashboard and Websockets _(August 16 – September 05)_

### server/backend

- [ ] Add `/client/all`
- [ ] Add websockets to FastAPI
- [ ] Write websocket tests

### server/frontend

- [ ] Create basic dashboard and implement websockets
- [ ] Create dashboard test

## Phase Four: Client Modules & Update System _(September 06 – October 01)_

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
