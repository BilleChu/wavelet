# OpenFinance Server Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Git installed
- At least 4GB RAM available for containers

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd wavelet
```

### 2. Create environment files

```bash
# Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

# Frontend environment (optional, defaults work for most cases)
cp frontend/.env.example frontend/.env.local
```

### 3. Start all services

```bash
docker-compose -f docker-compose.server.yml up -d
```

### 4. Check service status

```bash
docker-compose -f docker-compose.server.yml ps
```

## Environment Variables

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection URL | `postgresql+asyncpg://openfinance:openfinance@postgres:5432/openfinance` |
| REDIS_URL | Redis connection URL | `redis://redis:6379/0` |
| NEO4J_URI | Neo4j connection URI | `bolt://neo4j:7687` |
| NEO4J_USER | Neo4j username | `neo4j` |
| NEO4J_PASSWORD | Neo4j password | `openfinance123` |
| OPENAI_API_KEY | OpenAI API key | (required for LLM features) |
| DEBUG | Debug mode | `0` |
| LOG_LEVEL | Log level | `INFO` |

### Frontend (.env.local)

| Variable | Description | Default |
|----------|-------------|---------|
| NEXT_PUBLIC_API_URL | Backend API URL | `http://localhost:8000` |

## Service Ports

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Backend | 19100 | 8000 |
| Frontend | 3000 | 3000 |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |
| Neo4j HTTP | 7474 | 7474 |
| Neo4j Bolt | 7687 | 7687 |

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.server.yml logs -f backend
docker-compose -f docker-compose.server.yml logs -f frontend

# Restart services
docker-compose -f docker-compose.server.yml restart

# Stop all services
docker-compose -f docker-compose.server.yml down

# Remove all data (warning: deletes database)
docker-compose -f docker-compose.server.yml down -v

# Rebuild images
docker-compose -f docker-compose.server.yml build --no-cache
docker-compose -f docker-compose.server.yml up -d
```

## Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health
curl http://localhost:3000

# PostgreSQL health
docker exec openfinance-postgres pg_isready -U openfinance

# Redis health
docker exec openfinance-redis redis-cli ping

# Neo4j health
curl http://localhost:7474
```

## Data Synchronization

After deployment, sync historical data:

```bash
# Enter backend container
docker exec -it openfinance-backend bash

# Run sync script
python scripts/sync_historical_data.py --days 730
```

Or via API:

```bash
# Load pipeline config
curl -X POST http://localhost:8000/api/pipeline/dags/load-config

# Start historical data sync
curl -X POST http://localhost:8000/api/pipeline/dags/historical_data_sync/execute

# Check status
curl http://localhost:8000/api/pipeline/dags/historical_data_sync
```

## Troubleshooting

### Frontend build fails with "Module not found"

Ensure `frontend/lib/` directory is tracked by git:
```bash
git add frontend/lib/
git commit -m "Add frontend lib"
```

### Database connection fails

1. Check PostgreSQL is running: `docker ps | grep postgres`
2. Check logs: `docker logs openfinance-postgres`
3. Verify credentials in `.env`

### Neo4j connection fails

1. Wait for Neo4j to initialize (can take 60+ seconds)
2. Check logs: `docker logs openfinance-neo4j`
3. Verify password matches in both `.env` and `docker-compose.server.yml`

### Backend health check fails

1. Check logs: `docker logs openfinance-backend`
2. Verify all dependencies (postgres, redis, neo4j) are healthy
3. Check environment variables are set correctly
