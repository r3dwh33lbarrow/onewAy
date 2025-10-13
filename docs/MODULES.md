## Modules Directory Structure
The `modules/` directory holds all module configurations and their binaries. Each module should live in its own folder and include a `config.yaml` at the root of that folder.

Example:

```
modules/
  test_module/
    config.yaml
    test_module (or test_module.exe)
```

Uploads via `/module/upload` expect a folder containing at least `config.yaml`.

See also: `docs/MODULE_CONFIG.md` for the full `config.yaml` schema and examples.

## Internal Module Naming Conventions
Different parts of the system use different naming conventions for the same module name:

- Backend (Python, DB): `snake_case` (e.g., `test_module`)
- HTTP routes: `kebab-case` (e.g., `/module/run/test-module`)
- Frontend (TypeScript): `camelCase` (e.g., `testModule`)
- Display name: free-form (e.g., `Test Module`), converted to `snake_case` internally

The backend will normalize names from `config.yaml` to `snake_case` automatically.

## Adding Modules
Modules can be added via:

- Upload: `PUT /module/upload` (multipart of your module folder)
- Local path add: `PUT /module/add` with `{ "module_path": "<relative-or-absolute-path>" }`

Refer to `docs/BACKEND_SETTINGS.md` for where the backend expects the modules directory to live and how to configure it.
