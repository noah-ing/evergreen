# Evergreen Production Roadmap

> Assessment & Sprint Plan - December 2025

## Executive Summary

**Current State:** Strong foundation with 70% core functionality complete. The architecture is solid, multi-tenant from day 1, and uses cutting-edge tech stack (Dec 2025 vintage).

**Critical Gaps for MVP:**
1. ❌ No authentication/authorization layer
2. ❌ No background sync scheduler (manual sync only)
3. ❌ Tenant management not implemented (API stubs only)
4. ❌ No frontend/demo interface
5. ⚠️ Google Workspace connector not started
6. ⚠️ Limited error recovery/retry logic in ingestion

**Time to Deployable MVP:** 3-4 weeks focused development

---

## Production Readiness Assessment

### ✅ What's Solid

| Component | Status | Notes |
|-----------|--------|-------|
| Data Models | ✅ Production-ready | Pydantic v2, multi-tenant from day 1 |
| Configuration | ✅ Good | Settings pattern, env vars, feature flags |
| Vector Store | ✅ Good | Qdrant integration with tenant isolation |
| Graph Store | ✅ Good | FalkorDB with proper schema |
| Embeddings | ✅ Good | Voyage AI with batching & retry |
| Entity Extraction | ✅ Good | GLiNER2 + LLM fallback |
| Retrieval Engine | ✅ Good | Hybrid search + reranking + synthesis |
| M365 Connector | ✅ Basic | Email working, needs Teams/Files completion |
| API Structure | ✅ Good | FastAPI with proper error handling |
| Docker Compose | ✅ Good | All infra services defined |

### ❌ Critical Gaps

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| **Auth/AuthZ** | Can't deploy without | 3-4 days | 🔴 P0 |
| **Tenant CRUD** | No multi-tenant | 2-3 days | 🔴 P0 |
| **Background Sync** | Manual-only ingestion | 3-4 days | 🔴 P0 |
| **Webhook Handlers** | No real-time updates | 2-3 days | 🟡 P1 |
| **Frontend** | No demo capability | 3-5 days | 🟡 P1 |
| **Google Connector** | M365-only | 4-5 days | 🟠 P2 |

### ⚠️ Needs Hardening

| Area | Issue | Fix |
|------|-------|-----|
| Ingestion error handling | Basic try/catch | Add dead-letter queue, retry policies |
| Rate limiting | None | Add per-tenant limits |
| Input validation | Minimal | Add request size limits, sanitization |
| Logging/Observability | Basic structlog | Add request IDs, trace correlation |
| Secrets management | Env vars only | Move to vault/secrets manager |
| Database migrations | None | Add Alembic |

---

## Risk Analysis

### 🔴 Security Risks

1. **No Authentication (CRITICAL)**
   - All endpoints currently public
   - **Fix:** JWT with tenant claims, OAuth2 for user auth
   - **Effort:** 3-4 days

2. **Credential Storage**
   - Azure/Google creds in plain env vars
   - **Fix:** Secret manager (AWS Secrets Manager, GCP Secret Manager, or Vault)
   - **Effort:** 1-2 days

3. **No Rate Limiting**
   - API vulnerable to abuse
   - **Fix:** FastAPI rate limiting middleware with per-tenant quotas
   - **Effort:** 1 day

4. **CORS Wide Open in Dev**
   - `allow_origins=["*"]` in development
   - **Fix:** Proper origin allowlist in production
   - **Effort:** 1 hour

### 🟡 Scaling Risks

1. **Synchronous Entity Extraction**
   - GLiNER runs in thread pool but blocks request
   - **Fix:** Move to background task queue
   - **Effort:** Already architected with Redis

2. **Single-Process API**
   - Current setup won't scale horizontally
   - **Fix:** Stateless design (already done), add Redis for shared state
   - **Effort:** 1 day config

3. **M365 Rate Limits**
   - 10k requests/10min per mailbox
   - **Fix:** Respect Retry-After, batch requests
   - **Already have:** tenacity retry, but needs enhancement

### 🟠 Cost Risks

1. **LLM Costs at Scale**
   - Claude synthesis per query (~$0.02-0.05/query)
   - **Mitigation:** Response caching, smaller models for simple queries
   - Consider: Local LLM (Llama 3.2) for classification

2. **Embedding Re-runs**
   - Risk of re-embedding unchanged content
   - **Fix:** Content hashing, change detection
   - **Effort:** 2-3 hours

3. **Graph Explosion**
   - Entity relationships can grow O(n²)
   - **Fix:** Relationship strength thresholds, pruning
   - **Effort:** Already have strength field, add cleanup job

---

## Prioritized Roadmap

### Phase 1: Security & Core (Week 1) 🔴
**Goal:** Deploy to staging with auth

| Task | Days | Dependencies |
|------|------|--------------|
| JWT auth middleware | 2 | - |
| Tenant CRUD implementation | 2 | Auth |
| API rate limiting | 0.5 | Auth |
| Basic audit logging | 0.5 | - |
| Secrets to Secret Manager | 1 | - |
| Integration tests | 1 | All above |

**Deliverable:** Authenticated multi-tenant API on Railway/Render

### Phase 2: Background Sync (Week 2) 🔴
**Goal:** Automated incremental sync

| Task | Days | Dependencies |
|------|------|--------------|
| Celery/Redis task setup | 1 | Docker Compose |
| Initial sync job | 1 | Tasks |
| Delta sync job | 1.5 | Tasks |
| Webhook subscription handlers | 1.5 | Tasks |
| Sync status API | 0.5 | Tasks |
| Webhook renewal cron | 0.5 | Webhooks |

**Deliverable:** Auto-syncing M365 connector with webhook support

### Phase 3: Demo Frontend (Week 3) 🟡
**Goal:** Interactive demo for pilots

| Task | Days | Dependencies |
|------|------|--------------|
| Next.js scaffold | 0.5 | - |
| Auth flow (OAuth) | 1 | Auth API |
| Chat interface | 2 | Query API |
| Entity explorer | 1 | Entity API |
| Source viewer | 1 | Query API |

**Deliverable:** Web UI for query interface + entity browsing

### Phase 4: Polish & Pilots (Week 4) 🟡
**Goal:** Ready for 3 pilot SMBs

| Task | Days | Dependencies |
|------|------|--------------|
| Google Workspace connector | 3 | - |
| Error monitoring (Sentry) | 0.5 | - |
| Usage analytics | 1 | Audit logs |
| Admin dashboard | 1.5 | Frontend |
| Documentation | 1 | All |

**Deliverable:** Production system with both M365 + Google support

---

## Sprint 1: Immediate Tasks (Next 5 Days)

### Day 1-2: Authentication
```
1. Add python-jose, passlib dependencies
2. Create auth module:
   - JWT token generation/validation
   - Tenant claim extraction
   - OAuth2 password flow for MVP
3. Auth middleware for all /api/v1/* routes
4. Tests for auth flows
```

### Day 2-3: Tenant Management
```
1. Create tenant table (PostgreSQL)
2. Alembic migration setup
3. Implement TenantService:
   - create_tenant()
   - get_tenant()
   - update_tenant()
   - delete_tenant()
4. Wire up tenant API endpoints
5. Tenant isolation verification tests
```

### Day 3-4: Background Tasks
```
1. Add celery, redis dependencies
2. Create tasks module:
   - Task definitions
   - Task routing
   - Result backend
3. Implement sync tasks:
   - full_sync_task
   - delta_sync_task
4. Add Celery worker to docker-compose
```

### Day 4-5: Integration & Deploy
```
1. Integration tests for full flow
2. Railway/Render deployment config
3. Environment variable setup
4. Health checks & monitoring
5. README with deployment docs
```

---

## Architecture Enhancements for Production

### Recommended Additions

```
evergreen/
├── src/evergreen/
│   ├── auth/                    # NEW: Authentication module
│   │   ├── __init__.py
│   │   ├── jwt.py              # JWT token handling
│   │   ├── middleware.py       # Auth middleware
│   │   └── oauth.py            # OAuth2 flows
│   │
│   ├── tasks/                   # NEW: Background tasks
│   │   ├── __init__.py
│   │   ├── celery.py           # Celery app
│   │   ├── sync.py             # Sync tasks
│   │   └── maintenance.py      # Cleanup tasks
│   │
│   ├── services/                # NEW: Business logic layer
│   │   ├── __init__.py
│   │   ├── tenant.py           # Tenant management
│   │   ├── sync.py             # Sync orchestration
│   │   └── analytics.py        # Usage tracking
│   │
│   └── connectors/
│       └── google.py            # NEW: Google Workspace
```

### Database Schema (PostgreSQL)

```sql
-- Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Connections (M365, Google credentials per tenant)
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    provider VARCHAR(50) NOT NULL,  -- 'm365', 'google'
    credentials_encrypted BYTEA NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    last_sync_at TIMESTAMP,
    sync_cursor JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sync Jobs
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    connection_id UUID REFERENCES connections(id),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    documents_processed INT DEFAULT 0,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_connections_tenant ON connections(tenant_id);
CREATE INDEX idx_sync_jobs_tenant ON sync_jobs(tenant_id);
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
```

---

## Cost Projections (Per SMB Client)

### Infrastructure (Self-Hosted)
| Service | Sizing | Monthly Cost |
|---------|--------|--------------|
| Railway/Render (API) | 1GB RAM | $25 |
| Qdrant (self-hosted) | 2GB RAM | $20 |
| FalkorDB (self-hosted) | 1GB RAM | $15 |
| PostgreSQL | Shared | $15 |
| Redis | Shared | $10 |
| **Total Infra** | | **~$85/client** |

### API Costs (Per Client)
| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Voyage AI Embeddings | 100K docs | $10-30 |
| Cohere Reranking | 2K queries | $10-25 |
| Claude Synthesis | 2K queries | $40-100 |
| **Total API** | | **~$60-155/client** |

### Gross Margin Analysis
| Plan | Price | Costs | Margin |
|------|-------|-------|--------|
| Starter ($500/mo) | $500 | $145 | 71% |
| Growth ($1000/mo) | $1000 | $200 | 80% |
| Enterprise ($2000/mo) | $2000 | $300 | 85% |

✅ **Healthy margins achievable at target pricing**

---

## Neural Network Training Notes

Per PROJECT_BRIEF.md request about training custom models:

### When Custom Training Makes Sense
1. **Entity Resolution** - Train a model to merge duplicate entities
2. **Document Classification** - Categorize documents by type/importance
3. **Relationship Extraction** - Custom relation types for business context

### Recommended Approach (Dec 2025)
1. **Start with zero-shot** (GLiNER2, Voyage AI) - already implemented
2. **Collect training data** from pilot customers (3-6 months)
3. **Fine-tune when needed:**
   - SetFit for few-shot classification (< 100 examples)
   - LoRA fine-tuning on Llama 3.2 for custom tasks
   - EmbeddingGemma (308M) for domain-specific embeddings

### Training Visualization Code
The matplotlib snippet in PROJECT_BRIEF.md is ready to use. When training:

```python
# Example integration
from evergreen.training.visualize import plot

for epoch in range(EPOCHS):
    train_loss = train_epoch(model, train_loader)
    val_error, val_acc = evaluate(model, val_loader)
    
    val_errors.append(val_error)
    val_accs.append(val_acc)
    
    if epoch % 50 == 0:
        plot(val_errors, val_accs, epoch)
```

---

## Success Metrics for MVP

### Week 2 Milestone
- [ ] Auth working, tenant isolation verified
- [ ] Background sync processing 100 docs/hour
- [ ] P95 query latency < 5s

### Week 4 Milestone
- [ ] 3 pilot SMBs onboarded
- [ ] Query volume: 5+ queries/user/week
- [ ] Zero security incidents
- [ ] <1% sync failure rate

### 60-Day Milestone
- [ ] 90%+ pilot retention
- [ ] Avg response relevance score > 4/5
- [ ] <3s P95 query latency
- [ ] Google Workspace parity with M365

---

## Next Steps

1. **Today:** Review this roadmap, adjust priorities
2. **Tomorrow:** Start Sprint 1 (Auth implementation)
3. **End of Week 1:** Deploy to staging
4. **Week 2:** First pilot setup with real M365 data

Ready to start with authentication implementation?
