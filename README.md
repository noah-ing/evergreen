# Evergreen 

**Institutional Memory as a Service** - Cross-system knowledge retrieval for SMBs

> *"What did we promise Acme Corp on that renewal?"* -> Answered in seconds, not 45 minutes.

## What is Evergreen?

Evergreen is a business intelligence platform that captures, indexes, and synthesizes institutional knowledge scattered across an organization's communication and document systems - making it queryable through natural language.

### The Problem

Every SMB has their business truth scattered across:
- **Email** - deals, client relationships, promises made
- **Files** - contracts, SOWs, pricing, procedures 
- **Chat** - Slack/Teams where real decisions happen
- **People's heads** - the worst one

When a key employee leaves, years of context walks out the door. Onboarding takes 3-6 months of tribal knowledge absorption.

### The Solution

Evergreen connects to M365/Google Workspace and builds a living knowledge graph that:
- Indexes all emails, files, and chat messages
- Extracts entities (people, companies, projects, topics)
- Maps relationships across all data sources
- Answers natural language questions with source attribution

## Features

- ** Natural Language Search**: Ask questions in plain English
- **️ Knowledge Graph**: Understand relationships between people, projects, and clients
- ** Source Attribution**: Every answer includes citations
- ** Real-time Sync**: Delta sync keeps index fresh
- ** Multi-tenant**: Strict data isolation per organization
- ** API-first**: Easy integration with existing tools

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- M365 or Google Workspace admin access (for data sources)

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/evergreen.git
cd evergreen

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Start infrastructure
docker-compose up -d

# Run the development server
poetry run uvicorn evergreen.api.main:app --reload
```

### Configuration

See `.env.example` for all configuration options. Key variables:

```bash
# Azure AD / M365
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# LLM Providers
ANTHROPIC_API_KEY=your-key
VOYAGE_API_KEY=your-key
COHERE_API_KEY=your-key
```

## Architecture

```
┌─────────────────┐ ┌─────────────────┐
│ M365 / Google │────│ Connectors │
└─────────────────┘ └────────┬────────┘
 │
 ▼
 ┌─────────────────┐
 │ Ingestion │
 │ Pipeline │
 └────────┬────────┘
 │
 ┌──────────────────┼──────────────────┐
 ▼ ▼ ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ Qdrant │ │ FalkorDB │ │ Metadata │
 │ (Vector) │ │ (Graph) │ │ Store │
 └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
 └──────────────────┼──────────────────┘
 ▼
 ┌─────────────────┐
 │ Retrieval │
 │ Engine │
 └────────┬────────┘
 │
 ▼
 ┌─────────────────┐
 │ Query API │
 └─────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Database | PostgreSQL + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Embeddings | Voyage AI voyage-3.5 |
| Vector DB | Qdrant |
| Graph DB | FalkorDB |
| Entity Extraction | GLiNER2 + LLM |
| Orchestration | LlamaIndex + LangGraph |
| Reranking | Cohere rerank-v3.5 |
| LLM | Claude 3.5 Sonnet |
| Task Queue | Celery + Redis (planned) |

## Documentation

- [Project Brief](docs/memory-bank/PROJECT_BRIEF.md)
- [Tech Stack Decisions](docs/memory-bank/TECH_STACK.md)
- [Architecture](docs/memory-bank/ARCHITECTURE.md)
- [M365 Integration](docs/memory-bank/M365_INTEGRATION.md)

## Development

```bash
# Start local infrastructure
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start development server
uvicorn evergreen.api.main:app --reload

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/

# Format code
black src/
```

## API Endpoints

### Authentication

```bash
# Register new tenant + user
curl -X POST http://localhost:8000/api/v1/auth/register \
 -H "Content-Type: application/json" \
 -d '{"email":"admin@company.com","password":"secret","name":"Admin","tenant_name":"My Company","tenant_slug":"my-company"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
 -H "Content-Type: application/json" \
 -d '{"email":"admin@company.com","password":"secret"}'

# Get current user (protected)
curl http://localhost:8000/api/v1/auth/me \
 -H "Authorization: Bearer <access_token>"
```

## License

Proprietary - All rights reserved

## Contributing

This is a private project. Contact the maintainers for access.
