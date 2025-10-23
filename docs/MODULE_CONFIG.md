## Module `config.yaml` Schema

Each module folder must contain a `config.yaml` that describes how to run the module on the client. The backend validates and stores this information; the Rust client uses it to launch the module process and stream stdout/stderr.

### Required fields

- **`name`**: Human-friendly module name. The backend will normalize it to `snake_case` internally (e.g., `Test Module` -> `test_module`).
- **`version`**: Semver-like version string (e.g., `1.0.0`).
- **`start`**: Startup mode.
  - `manual` — only runs when requested via the UI/API.
  - `on_start` — starts automatically when the client starts.
- **`binaries`**: Paths to the module's executable per platform. Typically the binary lives next to `config.yaml` inside the module folder.
  - As a map:
    - `windows`: Relative or absolute path to the Windows binary.
    - `mac`: Relative or absolute path to the macOS binary.
    - `linux`: Relative path to the Linux binary.

### Optional fields

- **`description`**: A short description.

Notes:
- The client currently supports `windows`, `mac`, and `linux` keys. On unsupported platforms, the module will fail to start.
- Paths should be **relative** to the module folder. When packaging a client, only the referenced binary and the `config.yaml` file are copied; keep binaries colocated with their config.

### Minimal example (manual start)

```yaml
name: Test Module
version: 1.0.0
start: manual
description: Prints a line and exits
binaries:
  mac: test_module
  windows: test_module.exe
```

### Minimal example (auto start)

```yaml
name: Heartbeat
version: 0.1.0
start: on_start
description: Emits a periodic heartbeat
binaries:
  mac: heartbeat
  windows: heartbeat.exe
```

### Uploading and updating modules

- Upload a new module folder (must include `config.yaml`):
  - `PUT /module/upload` (multipart form field `files` includes folder contents)
- Add by local path on the backend host:
  - `PUT /module/add` with `{ "module_path": "<relative-or-absolute-path>" }`
- Update an existing module (replaces files and config):
  - `PUT /module/update/{module_name}` with a new module folder upload

### Runtime behavior

- On `module_run`, the Rust client spawns the configured binary with stdin/stdout/stderr piped.
- Stdout/stderr lines are streamed to the server and broadcast to the UI as WebSocket `console_output` messages.
- Exit status is forwarded in a `module_exit` event (`code` numeric, may be 0).
