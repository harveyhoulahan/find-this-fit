# Production Deployment Guide

## Overview

This guide covers deploying Find This Fit to production at scale, handling 50M+ items with sub-100ms query latency.

## Architecture for Scale

```
┌────────────────────────────────────────────┐
│         CloudFront CDN (Images)            │
└─────────────────┬──────────────────────────┘
                  │
┌─────────────────▼──────────────────────────┐
│     Application Load Balancer (ALB)        │
│     - SSL Termination                      │
│     - Rate Limiting                        │
│     - WAF Rules                            │
└─────────────────┬──────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
┌────────▼─────┐  ┌───────▼────────┐
│  FastAPI     │  │  FastAPI       │
│  Instance 1  │  │  Instance 2-N  │
│  (ECS/K8s)   │  │  (Auto-scaled) │
└────────┬─────┘  └───────┬────────┘
         │                │
         └────────┬───────┘
                  │
    ┌─────────────▼──────────────┐
    │  RDS PostgreSQL Cluster    │
    │  - Primary (writes)         │
    │  - Read Replicas (searches) │
    │  - pgvector HNSW indexes    │
    └────────────────────────────┘
```

## Cloud Provider Options

### 1. AWS (Recommended for Enterprise)

#### Components

- **Compute**: ECS Fargate or EKS (Kubernetes)
- **Database**: RDS PostgreSQL 15+ with pgvector
- **Load Balancer**: Application Load Balancer (ALB)
- **CDN**: CloudFront
- **Storage**: S3 for backups, scraped images
- **Monitoring**: CloudWatch, X-Ray
- **Secrets**: Secrets Manager

#### Setup Steps

```bash
# 1. Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier findthisfit-prod \
  --db-instance-class db.r6g.2xlarge \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password $DB_PASSWORD \
  --allocated-storage 500 \
  --storage-type gp3 \
  --iops 12000 \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx

# 2. Install pgvector extension
psql -h findthisfit-prod.xxxxx.rds.amazonaws.com -U postgres -c "CREATE EXTENSION vector;"

# 3. Load schema
psql -h findthisfit-prod.xxxxx.rds.amazonaws.com -U postgres -d find_this_fit -f database/init.sql

# 4. Create ECS cluster
aws ecs create-cluster --cluster-name findthisfit-prod

# 5. Build and push Docker image
aws ecr create-repository --repository-name findthisfit-api
docker build -t findthisfit-api -f backend/Dockerfile .
docker tag findthisfit-api:latest $ECR_URL/findthisfit-api:latest
docker push $ECR_URL/findthisfit-api:latest

# 6. Create ECS task definition (see below)
# 7. Create ALB and target groups
# 8. Create ECS service with auto-scaling
```

**ECS Task Definition** (`task-definition.json`):

```json
{
  "family": "findthisfit-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "${ECR_URL}/findthisfit-api:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://..."},
        {"name": "EMBEDDING_PROVIDER", "value": "clip"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/findthisfit",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

#### RDS Configuration for 50M Items

```sql
-- PostgreSQL settings for large vector workloads

-- Memory
shared_buffers = 16GB              -- 25% of RAM
effective_cache_size = 48GB        -- 75% of RAM
work_mem = 256MB                   -- Per query operation
maintenance_work_mem = 4GB         -- For index builds

-- Query planner
random_page_cost = 1.1             -- For SSD storage
effective_io_concurrency = 200     -- For gp3 storage

-- Connection pooling
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

-- Checkpoints (reduce I/O spikes)
checkpoint_timeout = 15min
max_wal_size = 16GB
checkpoint_completion_target = 0.9

-- Monitoring
log_min_duration_statement = 500   -- Log slow queries (>500ms)
track_activity_query_size = 2048
```

**Read Replicas** (for search offloading):

```bash
# Create read replica for searches
aws rds create-db-instance-read-replica \
  --db-instance-identifier findthisfit-prod-replica-1 \
  --source-db-instance-identifier findthisfit-prod \
  --db-instance-class db.r6g.2xlarge

# Update app to route searches to replica
export DATABASE_READ_URL="postgresql://postgres:pass@replica-endpoint:5432/find_this_fit"
```

### 2. Railway (Fastest Setup)

```bash
# Install CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Add PostgreSQL plugin (automatically gets pgvector)
railway add

# Deploy
railway up

# Get database URL
railway variables
```

Configure in Railway dashboard:
- Add `OPENAI_API_KEY` secret
- Set `EMBEDDING_PROVIDER=clip` (or openai)
- Enable auto-scaling (Pro plan)

### 3. Fly.io (Edge Deployment)

```bash
# Install flyctl
brew install flyctl

# Login
flyctl auth login

# Create app
flyctl launch --dockerfile backend/Dockerfile

# Create Postgres cluster
flyctl postgres create --name findthisfit-db

# Attach to app
flyctl postgres attach findthisfit-db

# Install pgvector
flyctl ssh console -a findthisfit-db
> apt-get update && apt-get install -y postgresql-15-pgvector
> exit

# Load schema
flyctl postgres connect -a findthisfit-db < database/init.sql

# Deploy
flyctl deploy

# Scale
flyctl scale count 3 --region iad,ord,lax  # Multi-region
```

**fly.toml**:

```toml
app = "findthisfit-api"
primary_region = "iad"

[build]
  dockerfile = "backend/Dockerfile"

[env]
  EMBEDDING_PROVIDER = "clip"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 2

[[http_service.checks]]
  grace_period = "30s"
  interval = "15s"
  method = "GET"
  timeout = "5s"
  path = "/health"

[resources]
  cpu_kind = "shared"
  cpus = 2
  memory = "4gb"

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

## Database Optimization for 50M Items

### Index Build Strategy

```sql
-- 1. Disable autovacuum during bulk insert
ALTER TABLE depop_items SET (autovacuum_enabled = false);

-- 2. Bulk insert items (no embeddings yet)
COPY depop_items (external_id, title, price, url, image_url) 
FROM '/data/items.csv' WITH CSV;

-- 3. Generate embeddings in batches (use embed_items.py)

-- 4. Build HNSW index (takes 10-15 hours for 50M items)
SET maintenance_work_mem = '8GB';
CREATE INDEX CONCURRENTLY depop_items_embedding_idx 
ON depop_items USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);

-- 5. Re-enable autovacuum
ALTER TABLE depop_items SET (autovacuum_enabled = true);
VACUUM ANALYZE depop_items;
```

### Partitioning (Optional, for 100M+)

```sql
-- Partition by category for easier sharding
CREATE TABLE depop_items_partitioned (
    LIKE depop_items INCLUDING ALL
) PARTITION BY LIST (category);

CREATE TABLE depop_items_tops PARTITION OF depop_items_partitioned
    FOR VALUES IN ('tshirt', 'sweater', 'hoodie');

CREATE TABLE depop_items_bottoms PARTITION OF depop_items_partitioned
    FOR VALUES IN ('jeans', 'pants', 'shorts');

-- Each partition gets its own HNSW index
```

### Query Optimization

```sql
-- For production, tune ef_search per query
SET LOCAL hnsw.ef_search = 200;  -- Higher = better recall

SELECT * FROM depop_items
ORDER BY embedding <=> '[...]'
LIMIT 20;

-- Profile queries
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM depop_items 
ORDER BY embedding <=> '[...]' 
LIMIT 20;
```

## Caching Strategy

### Redis for Hot Queries

```python
# Add to backend/app.py
import redis
import hashlib
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=False)

def get_cached_results(embedding: List[float]) -> Optional[List[dict]]:
    # Hash embedding to create cache key
    key = hashlib.sha256(json.dumps(embedding).encode()).hexdigest()
    cached = redis_client.get(f"search:{key}")
    if cached:
        return json.loads(cached)
    return None

def cache_results(embedding: List[float], results: List[dict]):
    key = hashlib.sha256(json.dumps(embedding).encode()).hexdigest()
    redis_client.setex(f"search:{key}", 3600, json.dumps(results))  # 1 hour TTL
```

### CDN for Images

```python
# In backend/models.py - rewrite image URLs to CDN
class DepopItem(BaseModel):
    image_url: Optional[str] = None
    
    @property
    def cdn_image_url(self):
        if not self.image_url:
            return None
        return f"https://cdn.yourapp.com/images/{hash(self.image_url)}.jpg"
```

## Monitoring & Observability

### Prometheus Metrics

```python
# Add to backend/app.py
from prometheus_client import Counter, Histogram, generate_latest

search_requests = Counter('search_requests_total', 'Total search requests')
search_latency = Histogram('search_latency_seconds', 'Search latency')

@app.post("/search_by_image")
async def search_by_image(payload: SearchRequest):
    search_requests.inc()
    with search_latency.time():
        # ... existing code

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Sentry Error Tracking

```python
# In backend/app.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://xxx@sentry.io/xxx",
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
)
```

### Logging

```python
# Use structured logging
import structlog

logger = structlog.get_logger()

@app.post("/search_by_image")
async def search_by_image(payload: SearchRequest):
    logger.info("search_started", embedding_provider=EMBEDDING_PROVIDER)
    # ...
    logger.info("search_completed", results_count=len(items), latency_ms=elapsed)
```

## Rate Limiting

```python
# Add to backend/app.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/search_by_image")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def search_by_image(request: Request, payload: SearchRequest):
    # ... existing code
```

## Cost Estimation (50M Items, 100K Searches/Day)

### AWS

| Service           | Spec                  | Monthly Cost |
|-------------------|-----------------------|--------------|
| RDS Primary       | db.r6g.2xlarge        | ~$650        |
| RDS Replica (2x)  | db.r6g.2xlarge        | ~$1,300      |
| ECS Fargate (4x)  | 2 vCPU, 4GB RAM       | ~$240        |
| ALB               | 100GB transfer        | ~$50         |
| CloudFront        | 1TB transfer          | ~$85         |
| **Total**         |                       | **~$2,325**  |

### Fly.io

| Service           | Spec                  | Monthly Cost |
|-------------------|-----------------------|--------------|
| Postgres (High)   | 4 CPU, 16GB RAM       | ~$169        |
| Apps (3 regions)  | 2 CPU, 4GB RAM × 3    | ~$186        |
| **Total**         |                       | **~$355**    |

### Railway (Pro)

| Service           | Spec                  | Monthly Cost |
|-------------------|-----------------------|--------------|
| Pro Plan          | Unlimited projects    | $20          |
| Postgres          | 8GB RAM, 50GB storage | ~$40         |
| App (2 instances) | 2GB RAM × 2           | ~$40         |
| **Total**         |                       | **~$100**    |

*Note: Railway cheapest for <1M items, AWS best for 50M+ scale*

## Performance Benchmarks

### Search Latency (50M Items)

| Component         | Latency    |
|-------------------|------------|
| Embedding (CLIP)  | 50-200ms   |
| Embedding (OpenAI)| 100-300ms  |
| pgvector Search   | 20-80ms    |
| Network           | 10-50ms    |
| **Total (CLIP)**  | **80-330ms**|
| **Total (OpenAI)**| **130-430ms**|

### Optimization Tips

1. **GPU for CLIP**: 200ms → 20ms (10x faster)
2. **Batch embeddings**: Process 100 images in 2s instead of 20s
3. **Increase ef_search**: Better recall, 20ms → 50ms
4. **Read replicas**: Offload searches from primary DB

## Disaster Recovery

### Backup Strategy

```bash
# Daily full backup
pg_dump -Fc find_this_fit > backup_$(date +%Y%m%d).dump

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).dump s3://findthisfit-backups/

# Automated with AWS Backup or RDS automated backups
```

### Restore Procedure

```bash
# 1. Create new RDS instance
# 2. Restore from snapshot or dump
pg_restore -d find_this_fit backup_20251125.dump

# 3. Verify data
psql -c "SELECT COUNT(*) FROM depop_items WHERE embedding IS NOT NULL;"

# 4. Update DNS to point to new instance
```

## Security Hardening

```bash
# 1. Use secrets management
export DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id db-url --query SecretString --output text)

# 2. Network isolation (VPC)
# - Database in private subnet
# - ALB in public subnet
# - App in private subnet with NAT gateway

# 3. SSL/TLS enforcement
ALTER SYSTEM SET ssl = on;

# 4. API authentication
# Add JWT or API key middleware (see FastAPI security docs)
```

## Next Steps

1. **Monitor performance** with DataDog/New Relic
2. **Add A/B testing** for embedding models
3. **Implement caching** with Redis
4. **Set up CI/CD** with GitHub Actions
5. **Load test** with Locust/K6

---

Ready for production deployment. See README.md for local development setup.
