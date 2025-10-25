# Docker Network Configuration

This setup supports two networking modes for your onewAy application:

## Default Mode (Localhost Only)
- **Backend API**: `http://localhost:8000`
- **Frontend**: `http://localhost:5173` 
- **PostgreSQL**: `localhost:5432`

Services are only accessible from your local machine.

## Public IP Mode
On **macOS/Windows** (Docker Desktop):
- **Backend API**: `http://<YOUR_HOST_IP>:8000`
- **Frontend**: `http://<YOUR_HOST_IP>:5173`
- **PostgreSQL**: Internal only (not exposed on public network)

Services are accessible from your local machine and VMs/other machines on the same network.

**Note:** On macOS and Windows, Docker runs in a VM, so containers don't get directly routable IPs. Instead, ports are exposed on your host machine's network interface, making them accessible to VMs and other devices on your network.

## Usage

### Method 1: Using the management script (Recommended)

```bash
# Start with localhost access (default)
./manage-services.sh start

# Start with public network access
HOST_PUBLIC=true ./manage-services.sh start

# Check status (shows your host IP and access URLs)
./manage-services.sh status

# View logs
./manage-services.sh logs

# Stop services
./manage-services.sh stop

# Restart services
./manage-services.sh restart
```

### Method 2: Using environment variable in .env

Edit the `.env` file and set:
```bash
HOST_PUBLIC=true
```

Then run:
```bash
./manage-services.sh start
```

### Method 3: Direct docker-compose commands

```bash
# Localhost only
docker compose up -d

# Public network access
docker compose -f docker-compose.yml -f docker-compose.public.yml up -d
```

## Network Details

When `HOST_PUBLIC=true`:

**On macOS/Windows (Docker Desktop):**
- Ports are bound to `0.0.0.0` (all network interfaces)
- Accessible via your Mac's IP address from VMs and other devices
- The script automatically detects and displays your host IP
- PostgreSQL remains internal for security

**On Linux:**
- Creates a custom bridge network `oneway-public` with subnet `172.20.0.0/16`
- Assigns static IP `172.20.0.10` to the application container
- Containers are directly accessible at their assigned IPs
- PostgreSQL remains internal for security

## How to Access from VMs

1. **Find your host IP:** Run the management script - it will show your IP (e.g., `10.81.70.69`)
2. **From your VM:** Access services at `http://<HOST_IP>:8000` and `http://<HOST_IP>:5173`
3. **Ensure network connectivity:** VMs must be on the same network or have routing to your host

### Example:
```bash
# On your Mac
./manage-services.sh start  # Shows: "From VMs/Network: http://10.81.70.69:8000"

# From your VM
curl http://10.81.70.69:8000/docs  # Access backend
# Open browser to http://10.81.70.69:5173  # Access frontend
```

## Security Notes

1. **PostgreSQL Security**: Database is kept internal and not exposed on the public network
2. **Firewall**: Ensure your host firewall allows traffic on ports 8000 and 5173 if needed
3. **Network Trust**: Only use `HOST_PUBLIC=true` on trusted networks
4. **VM Access**: When `HOST_PUBLIC=true`, any device on your network can access the services

## Files Modified

- `docker-compose.yml`: Base configuration
- `docker-compose.public.yml`: Public network overlay configuration  
- `.env`: Environment variables including `HOST_PUBLIC` flag
- `manage-services.sh`: Management script for easy switching between modes
- `start-services.sh`: Updated to support `HOST_PUBLIC` variable