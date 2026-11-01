# Docker Setup Instructions for macOS

This service supports two Docker workflows:

1. A self-contained local debug stack from this repository.
2. A shared microservice stack that connects to `distracted-dev-infra`.

For a portable multi-repo setup, use
`/Users/hritvikdinkar/repositories/distracted-dev-infra` as the main entrypoint:

```bash
cd /Users/hritvikdinkar/repositories/distracted-dev-infra
make bootstrap
make up
```

## Step 1: Start Docker Desktop
1. Open Docker Desktop from Applications folder
2. Wait for Docker engine to start (check menu bar icon)
3. Verify Docker is running:
   ```bash
   docker --version
   docker compose version
   ```

## Option A: Local Debug Stack

Use this for day-to-day debugging when you want Unified Data Service, MongoDB,
and Redis started together from this repository.

```bash
cd /Users/hritvikdinkar/repositories/unified-data-service
docker compose -f docker-compose.local.yml up --build
```

Equivalent Makefile command:

```bash
make up
```

Run it in the background:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

Check logs and health:

```bash
docker compose -f docker-compose.local.yml logs -f unified-data-service
curl http://localhost:8080/health
```

Stop the local stack:

```bash
docker compose -f docker-compose.local.yml down
```

Delete local MongoDB/Redis data as well:

```bash
docker compose -f docker-compose.local.yml down -v
```

## Image Registry Workflow

Use this when another laptop, CI/CD, or cloud infrastructure should pull the
same image instead of rebuilding locally.

```bash
IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=<org-or-user> \
IMAGE_TAG=dev \
make image-build

IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=<org-or-user> \
IMAGE_TAG=dev \
make image-push
```

Run a published image with shared infrastructure:

```bash
UDS_IMAGE=ghcr.io/<org-or-user>/unified-data-service:dev \
docker compose -f docker-compose.registry.yml up -d
```

## Option B: Shared Microservice Stack

Use this when Unified Data Service should run as one component in the broader
microservice infrastructure.

### Step 2: Start Infrastructure Services
Once Docker is running, execute:
```bash
cd /Users/hritvikdinkar/repositories/distracted-dev-infra
docker compose -f docker-compose/shared-infrastructure.yml up -d
```

## Step 3: Verify Services
```bash
# Check running containers
docker ps

# Test MongoDB
mongosh mongodb://admin:password@localhost:27017

# Test Redis
redis-cli ping
```

### Step 4: Start Unified Data Service
```bash
cd /Users/hritvikdinkar/repositories/unified-data-service
docker compose up -d
```

### Step 5: Verify Service Health
```bash
# Check service logs
docker compose logs -f unified-data-service

# Test health endpoint
curl http://localhost:8080/health
```

## Troubleshooting
- If Docker commands don't work, ensure Docker Desktop is fully started
- Check port conflicts (27017, 6379, 8080, 8081, 8082)
- Verify network connectivity between containers
