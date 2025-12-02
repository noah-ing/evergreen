# Evergreen: Institutional Memory as a Service

## Project Overview

**Evergreen** is a business intelligence platform that captures, indexes, and synthesizes institutional knowledge scattered across an organization's communication and document systems—making it queryable through natural language.

**NOTE FROM USER**
if we are building any neural networks, lets train them on the best datasets for our mission now and beyond. and use the best techniques (research this), to do so. when we are training then i want to use this to visualize them:

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

def plot(val_errors, val_accs, epoch):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0d1117')
    
    for ax in [ax1, ax2]:
        ax.set_facecolor('#0d1117')
        ax.tick_params(colors='#c9d1d9')
        ax.xaxis.label.set_color('#c9d1d9')
        ax.yaxis.label.set_color('#c9d1d9')
        ax.title.set_color('#c9d1d9')
        for spine in ax.spines.values():
            spine.set_color('#30363d')
        ax.grid(True, alpha=0.2, color='#30363d')
    
    epochs = list(range(len(val_errors)))
    
    # Left: Error
    ax1.plot(epochs, val_errors, color='#3fb950', linewidth=1.5, label='Val Mean Error')
    ax1.axhline(y=10, color='#f85149', linestyle='--', label='10% Tolerance')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Error (%)')
    ax1.set_title('Validation Error', fontweight='bold')
    ax1.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    
    # Right: Accuracy
    ax2.plot(epochs, val_accs, color='#d29922', linewidth=1.5, label='Val Accuracy')
    ax2.axhline(y=30, color='#3fb950', linestyle='--', label='30% Target')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_title('Validation Accuracy', fontweight='bold')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='lower right', facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    
    plt.tight_layout()
    plt.savefig('training_progress.png', dpi=150, facecolor='#0d1117')
    plt.close()

# In training loop:
for epoch in range(EPOCHS):
    # ... train ...
    if epoch % 50 == 0:
        plot(val_errors, val_accs, epoch)




### The Problem We Solve

Every SMB has their business truth scattered across:
- **Email** - deals, client relationships, promises made
- **Files** - contracts, SOWs, pricing, procedures  
- **Chat** - Slack/Teams where real decisions happen
- **SaaS tools** - CRM half-updated, PM tool half-used
- **People's heads** - the worst one

When someone asks "What did we promise Acme Corp on that renewal?" it takes 45 minutes of archaeology. When a key employee leaves, years of context walks out the door.

### Our Solution

An always-listening, always-indexing system that:
1. Connects to M365/Google Workspace
2. Indexes emails, files, chat, calendar
3. Builds a knowledge graph of relationships (people ↔ organizations ↔ projects ↔ topics)
4. Makes everything queryable via natural language

**Example queries:**
- "What's the full history of our relationship with Client X?"
- "What did we learn from the last time we did a project like this?"
- "If John left tomorrow, what would we lose?"
- "What promises have we made that aren't in any system of record?"

---

## Target Market

**Primary:** SMBs (20-150 employees) served by MSPs
**Distribution:** Through MSP partner (bundled into IT services)
**Pricing target:** $500-2000/month per organization

### Why MSP Distribution?
- Already have admin access to M365/Google Workspace
- Already have trust to touch sensitive systems
- Can bundle into existing contracts
- See which clients have messiest knowledge problems

---

## Technical Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Microsoft 365  │ Google Workspace│      (Future: Slack,        │
│  - Outlook      │ - Gmail         │       Salesforce, etc.)     │
│  - OneDrive     │ - Drive         │                             │
│  - SharePoint   │ - Calendar      │                             │
│  - Teams        │                 │                             │
│  - Calendar     │                 │                             │
└────────┬────────┴────────┬────────┴─────────────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                               │
│  - Delta sync (incremental updates)                              │
│  - Document parsing & chunking                                   │
│  - Entity extraction (people, orgs, projects, topics)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                 │
├─────────────────────────────┬───────────────────────────────────┤
│      Vector Database        │       Knowledge Graph              │
│      (Qdrant)               │       (FalkorDB)                   │
│                             │                                    │
│  - Document chunks          │  - Person nodes                    │
│  - Semantic embeddings      │  - Organization nodes              │
│  - Metadata filtering       │  - Project nodes                   │
│                             │  - Topic nodes                     │
│                             │  - Relationships                   │
└─────────────────────────────┴───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL LAYER                               │
│  - Hybrid search (vector + keyword)                              │
│  - Graph traversal                                               │
│  - Reranking                                                     │
│  - Context assembly                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY INTERFACE                               │
│  - Natural language chat                                         │
│  - Proactive insights                                            │
│  - Source attribution                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Current Progress (Sprint 1 Complete - Dec 1, 2025)
- [x] Full authentication system (JWT, multi-tenant)
- [x] Database schema with migrations (5 tables)
- [x] API endpoints protected with tenant isolation
- [x] Vector store integration (Qdrant)
- [x] Graph store integration (FalkorDB)
- [x] Entity extraction pipeline (GLiNER2)
- [x] Retrieval engine with reranking
- [x] 13 unit tests passing
- [x] Docker infrastructure (PostgreSQL, Qdrant, FalkorDB, Redis)

### MVP Success (Week 8-10)
- [ ] Full M365 integration working (email ✅, files ⏳, Teams ⏳)
- [ ] Knowledge graph populated with entities from real data
- [ ] Natural language queries returning relevant results
- [ ] 3 pilot SMBs onboarded

### Product-Market Fit Indicators
- Query volume per user (target: 5+/week)
- "Aha moment" rate in demos (target: 80%+)
- Retention after 60 days (target: 90%+)

---

## Competitive Landscape

| Company | Target | Price | Gap |
|---------|--------|-------|-----|
| Glean | Enterprise (10k+) | $50k+/yr | Too expensive for SMB |
| Guru | Enterprise | $15+/user/mo | Wiki-focused, not discovery |
| Notion AI | Teams | $10/user/mo | Only indexes Notion |
| Slack AI | Slack users | Included | Only indexes Slack |

**Our edge:** Cross-system synthesis at SMB price point, delivered through MSP trust relationship.

---

## Project Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Foundation | Weeks 1-2 | Core infrastructure, M365 auth |
| 2. Indexing | Weeks 3-4 | Email/file ingestion, chunking, embedding |
| 3. Knowledge Graph | Weeks 5-6 | Entity extraction, relationship mapping |
| 4. Retrieval | Weeks 7-8 | Hybrid search, query interface |
| 5. Polish | Weeks 9-10 | UI, pilot onboarding, iteration |

---

## Open Questions → Decisions Made

1. **Multi-tenancy:** ✅ **DECIDED** - Single instance, multi-tenant architecture
   - Separate Qdrant collection per tenant
   - Separate FalkorDB graph per tenant  
   - All PostgreSQL tables have tenant_id FK
   - JWT tokens include tenant_id claim

2. **Data residency:** ✅ **DECIDED** - Store indexed data (encrypted at rest)
   - Required for fast retrieval
   - Tenant can request full data deletion

3. **Compliance:** 🔄 **IN PROGRESS**
   - Audit logging implemented (audit_log table)
   - SOC2 design patterns followed
   - GDPR: Need data export/deletion endpoints

4. **Pricing model:** ✅ **DECIDED** - Per-organization flat monthly
   - $500-2000/month based on document count
   - Estimated costs: $145-300/client → 60-85% margin
