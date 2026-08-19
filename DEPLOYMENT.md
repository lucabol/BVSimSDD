# Deploying BVSim Web

BVSim includes a production Docker image and deployment scripts for Azure
Container Apps. It can also run on any server that supports Docker.

## Included Deployment Files

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the web application with Python and Gunicorn |
| `docker-entrypoint.sh` | Initializes `/data` and starts Gunicorn |
| `deploy.sh` | Deploys the local source to Azure Container Apps from Bash |
| `deploy.bat` | Deploys the local source to Azure Container Apps from Windows Command Prompt |

There are currently no Docker Compose, Kubernetes, Terraform, Ansible, or
systemd deployment files.

## Azure Container Apps

### Prerequisites

- An Azure subscription
- The [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- Docker, when required by the Azure CLI build process

Sign in and deploy from the repository root:

```bash
az login
./deploy.sh
```

On Windows Command Prompt:

```cmd
az login
deploy.bat
```

The scripts create or reuse the required Container Apps resources, build the
application from the local `Dockerfile`, deploy it, and print its HTTPS URL.

The following variables override the defaults:

| Variable | Default |
|---|---|
| `APP_NAME` | `bvsim-web` |
| `RESOURCE_GROUP` | `bvsim-rg` |
| `ENVIRONMENT` | `bvsim-env` |
| `LOCATION` | `westeurope` |
| `SOURCE_DIR` | `.` |

Example:

```bash
APP_NAME=my-bvsim \
RESOURCE_GROUP=my-rg \
ENVIRONMENT=my-env \
LOCATION=westeurope \
./deploy.sh
```

The deployment scripts do not configure persistent Azure storage. Team YAML
files created or edited through the web interface are stored in `/data` and
may be lost when a container restarts or a new revision is deployed. Configure
an Azure Files volume mounted at `/data` before using the application for
persistent data.

## Docker Server

Build the image from the repository root:

```bash
docker build -t bvsim-web .
```

Create a persistent volume and run the container:

```bash
docker volume create bvsim-data

docker run -d \
  --name bvsim-web \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  -v bvsim-data:/data \
  -e BVSIM_WEB_WORKERS=2 \
  bvsim-web
```

The application is then available to the server at
`http://127.0.0.1:8000`. Binding to localhost prevents clients from bypassing
the reverse proxy.

The container supports these runtime variables:

| Variable | Default | Purpose |
|---|---:|---|
| `BVSIM_WEB_HOST` | `0.0.0.0` | Listening interface inside the container |
| `BVSIM_WEB_PORT` | `8000` | Listening port inside the container |
| `BVSIM_WEB_WORKERS` | `2` | Gunicorn worker count |
| `BVSIM_WEB_TIMEOUT` | `60` | Gunicorn request timeout in seconds |
| `BVSIM_WEB_LOGLEVEL` | `info` | Gunicorn log level |

## HTTPS and Access Control

Put a reverse proxy such as Caddy, Nginx, or Apache in front of the container
to terminate HTTPS and forward requests to `127.0.0.1:8000`.

The BVSim web interface has no built-in authentication and is intended for
local or trusted use. Do not expose it directly to the public internet.
Restrict access with a private network, VPN, identity-aware proxy, or
authentication configured at the reverse proxy.

