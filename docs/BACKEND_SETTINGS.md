## Backend Settings (Python)

The Python backend reads configuration from `server/backend/config.toml`. These settings control database connections, JWT security, CORS, paths, and testing overrides.

Important: paths may contain the placeholder `[ROOT]`, which is automatically resolved to the repository root by the backend at runtime.

### File: `server/backend/config.toml`

Sections you will see in this file:

- **`[app]`**
  - **`debug`**: Enables extra logging in the backend.
  - **`client_version`**: Current required client version. Must be non-empty.

- **`[cors]`**
  - **`allow_origins`**: Allowed origins for the frontend.

- **`[database]`**
  - **`url`**: Async SQLAlchemy DSN (e.g., `postgresql+asyncpg://user:pass@host:5432/db`).
  - **`pool_size`**: Connection pool size.
  - **`pool_timeout`**: Seconds to wait for a connection.
  - **`echo`**: SQL echo logging.

- **`[security]`**
  - **`secret_key`**: JWT signing key.
  - **`algorithm`**: JWT algorithm (e.g., `HS256`).
  - **`access_token_expires_minutes`**: Access token lifetime.
  - **`refresh_token_expires_days`**: Refresh token lifetime.
  - **`jwt_issuer`**: JWT issuer claim.
  - **`jwt_audience`**: JWT audience claim.

- **`[paths]`**
  - **`client_dir`**: Location of the Rust client source (used by the backend for some tasks).
  - **`module_dir`**: Where the backend looks for modules (your `modules/` directory).
  - **`avatar_dir`**: Where user avatars are stored.

- **`[other]`**
  - **`max_avatar_size_mb`**: Upload size limit for avatars.

#### Testing overrides

If you set **`[testing].testing = true`**, values under **`[testing.database]`**, **`[testing.security]`**, and **`[testing.paths]`** will override the main **`[database]`**, **`[security]`**, and **`[paths]`** sections during runtime. This is useful for integration tests and local sandboxing.

Example minimal config (development):

```
[app]
debug = true
client_version = "0.1.0"

[cors]
allow_origins = ["http://localhost:5173"]

[database]
url = "postgresql+asyncpg://onewayuser:password@localhost:5432/oneway"
pool_size = 10
pool_timeout = 30
echo = false

[security]
secret_key = "dev-secret"
algorithm = "HS256"
access_token_expires_minutes = 15
refresh_token_expires_days = 7
jwt_issuer = "https://api.oneway.local"
jwt_audience = "onewAy-api"

[paths]
client_dir = "[ROOT]/client"
module_dir = "[ROOT]/modules"
avatar_dir = "[ROOT]/server/backend/app/resources/avatars"

[other]
max_avatar_size_mb = 2
```

See `server/backend/app/settings.py` for the exact shape and validation rules applied at startup.

