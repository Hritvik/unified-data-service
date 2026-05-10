# Docker Setup Instructions for macOS

## Step 1: Start Docker Desktop
1. Open Docker Desktop from Applications folder
2. Wait for Docker engine to start (check menu bar icon)
3. Verify Docker is running:
   ```bash
   docker --version
   docker compose version
   ```

## Step 2: Start Infrastructure Services
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

## Step 4: Start Unified Data Service
```bash
cd /Users/hritvikdinkar/repositories/unified-data-service
docker compose up -d
```

## Step 5: Verify Service Health
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
