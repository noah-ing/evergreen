# Technology Stack Decisions

> Last updated: December 1, 2025 (Sprint 1 Complete)

## Final Stack Summary

| Layer | Technology | Status | Rationale |
|-------|------------|--------|------------|
| **API Framework** | FastAPI + Pydantic v2 | ✅ Implemented | Async, fast, great DX |
| **Auth** | JWT (python-jose) + bcrypt | ✅ Implemented | Stateless, secure |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | ✅ Implemented | Async, migrations |
| **Migrations** | Alembic | ✅ Implemented | Version control for schema |
| **Embeddings** | Voyage AI voyage-3.5 | ✅ Implemented | 32K context, best quality/cost |
| **Vector DB** | Qdrant | ✅ Implemented | Free tier, native hybrid search |
| **Graph DB** | FalkorDB | ✅ Implemented | Free, GraphRAG-SDK, multi-tenant |
| **Entity Extraction** | GLiNER2 + LLM fallback | ✅ Implemented | Local, fast, flexible |
| **Orchestration** | LlamaIndex + LangGraph | 🔄 Partial | Best RAG + best agents |
| **Reranking** | Cohere rerank-v3.5 | ✅ Implemented | 10-30% quality boost |
| **LLM** | Claude 3.5 Sonnet | ✅ Implemented | Primary reasoning |
| **Task Queue** | Celery + Redis | ⏳ Planned | Background sync jobs |
| **M365 SDK** | msgraph-sdk + azure-identity | 🔄 Partial | Email working, needs Teams/Files |
| **Google SDK** | google-api-python-client | ⏳ Planned | Future connector |

---

## Detailed Decisions

### Embedding Model: Voyage AI voyage-3.5

**Why:**
- 32K context window (handles long email threads, documents)
- Flexible dimensions (256-2048) for cost/performance tuning
- Strong multilingual support
- Best-in-class retrieval benchmarks (Dec 2025)

**Alternatives considered:**
- OpenAI text-embedding-3-large: Good but 8K context limit
- Cohere embed-v3: Close second, slightly lower quality
- BGE-M3: Free/local option if cost becomes critical
- **EmbeddingGemma (NEW - Dec 2025):** 308M param multilingual model from Google
  - Highest-ranking text-only multilingual embedding model under 500M on MTEB
  - Great for local/on-device deployments
  - Consider for cost-sensitive clients or air-gapped environments

**Cost:** ~$0.06/1M tokens (very cheap at SMB scale)

> **Note:** HuggingFace Transformers v5.0.0rc0 released Dec 1, 2025. We're pinning to
> v4.57.x for stability. Revisit v5 when stable (likely Jan 2026). Key v5 features:
> unified tokenizer backend, `dtype` replacing `torch_dtype`, EmbeddingGemma integration.

---

### Vector Database: Qdrant

**Why:**
- Free 1GB cloud cluster (enough for MVP)
- Native hybrid search (dense + sparse vectors)
- Excellent metadata filtering (essential for M365 attributes)
- Easy Docker self-hosting when we scale
- Payload storage included (no separate doc store needed)

**Alternatives considered:**
- Pinecone: More expensive, less filtering flexibility
- Weaviate: Good but heavier operational overhead
- ChromaDB: Not production-ready for multi-tenant
- pgvector: Good but no native hybrid search

**Deployment plan:**
1. Start: Qdrant Cloud free tier
2. Scale: Self-hosted Docker on fly.io or Railway
3. Enterprise: Qdrant dedicated cluster

---

### Graph Database: FalkorDB

**Why:**
- 100% free (Docker deployment)
- GraphRAG-SDK built for retrieval applications
- Native multi-tenancy (essential for serving multiple SMBs)
- 496x faster than Neo4j (per their benchmarks)
- LangChain/LlamaIndex integrations

**Alternatives considered:**
- Neo4j: Industry standard but expensive at scale ($65+/mo cloud)
- Kùzu: ⚠️ ARCHIVED October 2025 - do not use
- Memgraph: $25k/year minimum for cloud

**Docker command:**
```bash
docker run -p 6379:6379 -it --rm -v ./data:/data falkordb/falkordb
```

---

### Entity Extraction: GLiNER2 + LLM Hybrid

**Why:**
- GLiNER2 (Nov 2025): 205M params, runs on CPU, zero-shot custom entities
- Handles people, companies, projects without training
- LLM fallback only for topics/themes (semantic understanding required)
- Fully local option (no API costs for extraction)

**Pipeline:**
1. GLiNER2 extracts: people, organizations, projects, dates
2. LLM extracts: topics, themes, sentiment (complex cases)
3. spaCy + coreferee: coreference resolution ("John" → "he" → "Smith")
4. Embedding clustering: cross-document entity resolution

**Install:**
```bash
pip install gliner spacy coreferee
python -m spacy download en_core_web_trf
```

---

### RAG Orchestration: LlamaIndex + LangGraph

**Why both:**
- **LlamaIndex**: Best-in-class for data ingestion, connectors, RAG pipelines
- **LangGraph**: Best-in-class for complex agent workflows, human-in-loop

**Division of labor:**
- LlamaIndex: Indexing, chunking, retrieval, PropertyGraphIndex
- LangGraph: Multi-step reasoning, tool orchestration, state machines

**Key LlamaIndex features we'll use:**
- 300+ data connectors
- PropertyGraphIndex (graph + vector hybrid)
- Metadata filtering
- Response synthesis

---

### Reranking: Cohere rerank-v3.5

**Why:**
- 10-30% retrieval quality improvement
- Fast (adds ~100ms latency)
- Cheap (~$0.50/1K queries)
- Best benchmarks for business documents

**When to use:**
- Always on queries (worth the latency)
- Rerank top 20-50 results down to top 5-10

---

### LLM: Claude 3.5 Sonnet (primary) / GPT-4o (fallback)

**Why Claude:**
- Best reasoning for document synthesis
- Excellent instruction following
- Good cost/performance ratio

**Why GPT-4o fallback:**
- Structured outputs (native JSON mode)
- Some users prefer/require OpenAI

**Local option (future):**
- Llama 3.2 3B for simple classification tasks
- Phi-3.5-mini for cost-sensitive deployments

---

## Cost Estimates (Per SMB Client)

### Low usage (1000 queries/month, 100K documents)
| Component | Monthly Cost |
|-----------|--------------|
| Embeddings (Voyage) | $10 |
| Vector DB (Qdrant free) | $0 |
| Graph DB (FalkorDB self-hosted) | $5 (compute) |
| Reranking (Cohere) | $5 |
| LLM (Claude) | $50 |
| **Total** | **~$70/month** |

### Medium usage (5000 queries/month, 500K documents)
| Component | Monthly Cost |
|-----------|--------------|
| Embeddings | $30 |
| Vector DB (Qdrant starter) | $25 |
| Graph DB | $15 |
| Reranking | $25 |
| LLM | $200 |
| **Total** | **~$300/month** |

**Margin at $500-2000/month pricing: 60-85%** ✅

---

## Infrastructure

### Development
- Python 3.11+
- Docker + Docker Compose
- Poetry for dependency management

### Staging/Production
- **Option A:** Railway/Render (simplest)
- **Option B:** Fly.io (better for distributed)
- **Option C:** AWS/GCP (enterprise clients)

### CI/CD
- GitHub Actions
- Pytest for testing
- Ruff for linting

---

## Security Considerations

1. **Data encryption:** All data at rest and in transit
2. **Multi-tenancy:** Strict data isolation per client
3. **Token storage:** Azure Key Vault / GCP Secret Manager
4. **Audit logging:** Every query and access logged
5. **SOC2 path:** Design for compliance from day 1

---

## Dependencies (pyproject.toml)

```toml
# Core
python = "^3.11"
pydantic = "^2.5"
pydantic-settings = "^2.1"
httpx = "^0.26"
fastapi = "^0.109"
uvicorn = "^0.27"

# Authentication
python-jose = {extras = ["cryptography"], version = "^3.3"}
passlib = {extras = ["bcrypt"], version = "^1.7"}
bcrypt = "^4.0"

# Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"
alembic = "^1.13"

# Task Queue (Sprint 2)
celery = "^5.3"
redis = "^5.0"

# LLM & RAG
llama-index = "^0.10"
langchain = "^0.1"
langgraph = "^0.0.40"
anthropic = "^0.18"
cohere = "^4.40"
voyageai = "^0.2"

# Vector & Graph
qdrant-client = "^1.7"
falkordb = "^1.0"

# Entity Extraction
gliner = "^0.2"
spacy = "^3.7"
transformers = "^4.57"  # Pinned <5.0 for stability

# Microsoft 365
msgraph-sdk = "^1.2"
azure-identity = "^1.15"

# Utils
python-dotenv = "^1.0"
structlog = "^24.0"
```
