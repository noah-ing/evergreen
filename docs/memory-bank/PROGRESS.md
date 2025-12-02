# Development Progress

> Current status and active context for development

## Current Phase: Production Hardening (Sprint 1 ✅ COMPLETE)

### ✅ Completed Foundation (95%)
- [x] Deep research on tech stack
- [x] Memory bank documentation created
- [x] Architecture design complete
- [x] Project scaffolding (pyproject.toml, docker-compose, .env)
- [x] Core models defined (Pydantic v2, multi-tenant)
- [x] Base connector interface
- [x] M365 connector (email working, needs Teams/Files)
- [x] Document parser
- [x] Semantic chunker
- [x] Ingestion orchestrator
- [x] FastAPI app with routes
- [x] Basic test suite
- [x] **Storage Layer**
  - [x] Vector store (Qdrant) - `/storage/vector.py`
  - [x] Graph store (FalkorDB) - `/storage/graph.py`
  - [x] Embeddings (Voyage AI) - `/storage/embeddings.py`
- [x] **Entity Extraction**
  - [x] GLiNER2 extractor - `/extraction/extractor.py`
  - [x] LLM fallback for relationships
- [x] **Retrieval Engine**
  - [x] Hybrid search (vector + graph) - `/retrieval/engine.py`
  - [x] Cohere reranking integration
  - [x] Claude answer synthesis
- [x] **API Wiring**
  - [x] Query endpoint functional
  - [x] Entity listing/detail endpoints
- [x] **Production Roadmap** - `/docs/memory-bank/PRODUCTION_ROADMAP.md`
- [x] **Authentication & Authorization** ✅
  - [x] JWT token handling - `/auth/jwt.py`
  - [x] Password hashing (bcrypt) - `/auth/password.py`
  - [x] Auth middleware (FastAPI deps) - `/auth/dependencies.py`
  - [x] Auth schemas - `/auth/schemas.py`
  - [x] Auth routes (register, login, refresh, me) - `/api/routes/auth.py`
  - [x] Protected all API endpoints with tenant isolation
- [x] **Database Layer** ✅
  - [x] SQLAlchemy async models - `/db/models.py`
  - [x] Tenant, User, Connection, SyncJob, AuditLog tables
  - [x] Alembic migrations - `/alembic/versions/001_initial_schema.py`
  - [x] All migrations applied to local Postgres
- [x] **Services Layer** ✅
  - [x] TenantService - `/services/tenant.py`
  - [x] UserService - `/services/user.py`
  - [x] AuthService - `/services/auth.py`
- [x] **Auth Tests** - `/tests/test_auth.py` (13 tests passing)
- [x] **E2E Testing** ✅
  - [x] /health endpoint - ✅ 200 OK
  - [x] /api/v1/auth/register - ✅ Creates tenant + user + JWT
  - [x] /api/v1/auth/login - ✅ Validates creds, returns JWT
  - [x] /api/v1/auth/refresh - ✅ Issues new tokens
  - [x] /api/v1/auth/me - ✅ Returns authenticated user
  - [x] JWT tenant isolation working

### 🔴 Next Up: Railway Deployment
- [ ] Railway project setup
- [ ] Environment variables configured
- [ ] Postgres provisioned
- [ ] Deploy staging build

### 🟡 Sprint 2: Background Sync (5 days)
- [ ] Celery/Redis task setup
- [ ] Full sync job
- [ ] Delta sync job
- [ ] M365 webhook handlers
- [ ] Webhook renewal cron

### 🟠 Sprint 3: Demo Frontend (5 days)
- [ ] Next.js scaffold
- [ ] Chat interface
- [ ] Entity explorer
- [ ] Source viewer

### ⏳ Backlog
- [ ] Google Workspace connector
- [ ] Teams/Slack connector
- [ ] Admin dashboard
- [ ] Usage analytics

---

## Key Decisions Made

1. **Transformers v5 (Dec 1, 2025)**
   - Released today as RC - pinned to v4.57.x for stability
   - EmbeddingGemma noted as potential local alternative
   - Will revisit when v5 stable

2. **Multi-tenant from day 1**
   - Each tenant = separate Qdrant collection + FalkorDB graph
   - All models include tenant_id

3. **Deployment target**
   - Start with Railway for simplicity
   - Docker Compose for local dev

---

## Current File Structure

```
evergreen/
├── docs/
│   └── memory-bank/
│       ├── PROJECT_BRIEF.md
│       ├── TECH_STACK.md
│       ├── ARCHITECTURE.md
│       ├── M365_INTEGRATION.md
│       ├── PROGRESS.md (this file)
│       └── PRODUCTION_ROADMAP.md
├── src/
│   └── evergreen/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── auth/                    # NEW: Authentication module
│       │   ├── __init__.py
│       │   ├── jwt.py               # JWT token creation/validation
│       │   ├── password.py          # bcrypt password hashing
│       │   ├── dependencies.py      # FastAPI auth dependencies
│       │   └── schemas.py           # Auth Pydantic schemas
│       ├── db/                      # NEW: Database layer
│       │   ├── __init__.py          # SQLAlchemy async engine
│       │   └── models.py            # Tenant, User, Connection, etc.
│       ├── services/                # NEW: Business logic layer
│       │   ├── __init__.py
│       │   ├── tenant.py            # TenantService CRUD
│       │   ├── user.py              # UserService with auth
│       │   └── auth.py              # AuthService (register/login/refresh)
│       ├── connectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── m365.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   ├── chunker.py
│       │   └── orchestrator.py
│       ├── extraction/
│       │   ├── __init__.py
│       │   └── extractor.py
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── vector.py
│       │   ├── graph.py
│       │   └── embeddings.py
│       ├── retrieval/
│       │   ├── __init__.py
│       │   └── engine.py
│       └── api/
│           ├── __init__.py
│           ├── main.py
│           └── routes/              # NEW: API route modules
│               ├── __init__.py
│               ├── auth.py          # /auth endpoints
│               └── tenants.py       # /tenants endpoints
├── alembic/                         # NEW: Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py    # Tenant, User, Connection, SyncJob, AuditLog
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   └── test_auth.py                 # NEW: 13 auth unit tests
├── alembic.ini
├── pyproject.toml
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Key Learnings So Far

### From Research Phase
1. **Voyage AI** beats OpenAI embeddings for business docs (32K context window)
2. **FalkorDB** is free and has native GraphRAG-SDK - no need for Neo4j
3. **GLiNER2** (Nov 2025) enables local entity extraction - game changer for cost
4. **Kùzu** was archived Oct 2025 - don't use despite old recommendations
5. **Delta queries** are essential for M365 - polling is too slow/expensive

### Technical Notes
- M365 webhooks expire every 4230 minutes (≈3 days) - need renewal job
- Qdrant payload storage means no separate document store needed
- LlamaIndex PropertyGraphIndex combines vector + graph elegantly

---

## Session Log

### Dec 1, 2025 - Sprint 1 Complete: Authentication System ✅
- Implemented full JWT authentication:
  - `auth/jwt.py` - HS256 tokens with tenant claims, 30min access + 7day refresh
  - `auth/password.py` - bcrypt hashing (12 rounds)
  - `auth/dependencies.py` - FastAPI deps for protected routes
  - `auth/schemas.py` - Pydantic v2 schemas for auth flows
- Database layer with SQLAlchemy 2.0 async:
  - 5 tables: tenants, users, connections, sync_jobs, audit_log
  - Alembic migrations configured and applied
- Services layer (TenantService, UserService, AuthService)
- API routes wired with full protection
- 13 unit tests passing
- **E2E Testing Complete**:
  - POST /api/v1/auth/register → 201 Created ✅
  - POST /api/v1/auth/login → 200 OK (correct creds) / 401 (wrong) ✅
  - POST /api/v1/auth/refresh → 200 OK with new tokens ✅
  - GET /api/v1/auth/me → Returns authenticated user ✅
- Fixed RefreshRequest schema (was incorrectly requiring all TokenPair fields)
- Docker infrastructure running: PostgreSQL, Qdrant, FalkorDB, Redis

### Dec 1, 2025 - Production Readiness Assessment
- Complete code review of all modules
- Created PRODUCTION_ROADMAP.md with:
  - Gap analysis (auth, tenant mgmt, background sync missing)
  - Risk assessment (security, scaling, cost)
  - 4-week roadmap to deployable MVP
  - Sprint 1 tasks detailed
  - Cost projections ($145-300/client vs $500-2000 pricing)
  - Database schema for production
- Key findings:
  - 70% core functionality complete
  - Architecture is solid, multi-tenant from day 1
  - Critical gaps: No auth, no background jobs, no tenant persistence
  - ~3-4 weeks to deployable MVP

### Dec 1, 2025 - Project Kickoff
- Discussed project direction with user
- Landed on "Institutional Memory as a Service" concept
- Completed deep research on all major tech choices
- Created comprehensive memory bank documentation
- Ready to begin scaffolding

---

## Quick Commands

```bash
# Start local infrastructure
docker-compose up -d

# Run database migrations
source .venv/bin/activate
alembic upgrade head

# Run development server
uvicorn evergreen.api.main:app --reload --port 8000

# Run all tests
pytest tests/ -v

# Run auth tests only
pytest tests/test_auth.py -v

# Type checking
mypy src/

# Linting
ruff check src/
```

## API Testing Commands

```bash
# Health check
curl http://localhost:8000/health

# Register new tenant + user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"secret","name":"Admin","tenant_name":"Acme Corp","tenant_slug":"acme-corp"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"secret"}'

# Protected endpoint (get current user)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh tokens
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## Environment Variables Needed

```bash
# Azure AD / M365
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=

# LLM Providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
COHERE_API_KEY=
VOYAGE_API_KEY=

# Infrastructure
QDRANT_URL=http://localhost:6333
FALKORDB_URL=redis://localhost:6379
DATABASE_URL=postgresql://localhost:5432/evergreen

# App Config
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```
