# Graph Database Comparison for SMB Knowledge Systems
**Research Date: December 2025**

---

## Executive Summary

**Recommendation: FalkorDB (Self-hosted)** for startups building retrieval products at SMB scale.

**Rationale:** Best balance of cost ($0 self-hosted), performance (496x faster than Neo4j per benchmarks), Python/LangChain integration, and GraphRAG-native features. Kuzu was promising but **archived in October 2025**.

---

## 1. Database Comparison Matrix

| Feature | Neo4j | FalkorDB | Memgraph | Kùzu |
|---------|-------|----------|----------|------|
| **Pricing** | $65/GB/mo (Pro), Free tier limited | Free (OSS), $73/GB/mo cloud | $25k/yr min (16GB), Free community | ⚠️ **Archived Oct 2025** |
| **Python Support** | ✅ Official driver | ✅ Native + LangChain/LlamaIndex | ✅ GQLAlchemy + NetworkX | ✅ Native (legacy) |
| **Query Language** | Cypher | Cypher | Cypher | Cypher |
| **Self-hosted** | Community edition | ✅ Docker/Redis-based | ✅ Docker | ✅ Embedded |
| **Vector Search** | ✅ (Pro+) | ✅ Built-in | Limited | ✅ Built-in |
| **Multi-tenancy** | Enterprise only | ✅ Native (zero overhead) | Enterprise only | N/A |
| **GraphRAG Ready** | Manual setup | ✅ GraphRAG-SDK | Manual | Manual |

---

## 2. Cost Analysis (10k-500k nodes @ SMB scale)

### Self-Hosted Options

| Database | Annual Cost | Notes |
|----------|-------------|-------|
| **FalkorDB** | **$0** | Docker, Redis-based, production-ready |
| Neo4j Community | $0 | No clustering, limited scale |
| Memgraph Community | $0 | Good for streaming, limited features |
| Kùzu | $0 | ⚠️ Archived - not recommended |

### Managed Cloud Options

| Database | Est. Monthly (1-8GB) | Notes |
|----------|---------------------|-------|
| Neo4j AuraDB Free | $0 | Dev only, auto-pause |
| Neo4j AuraDB Pro | $65-520/mo | Production, 1-8GB |
| FalkorDB Cloud | $73-584/mo | Multi-tenant, 1-8GB |
| Memgraph Cloud | ~$2,083/mo | $25k/yr minimum |

**Winner for Cost:** FalkorDB self-hosted ($0) or Neo4j Free tier (dev only)

---

## 3. Ease of Use & Python Integration

### FalkorDB
```python
# pip install falkordb
from falkordb import FalkorDB

db = FalkorDB(host='localhost', port=6379)
graph = db.select_graph('knowledge')
result = graph.query("MATCH (p:Person)-[:WORKS_AT]->(o:Org) RETURN p, o")
```
- **LangChain:** Native integration via `langchain-community`
- **LlamaIndex:** Official support
- **GraphRAG-SDK:** Purpose-built for RAG applications

### Neo4j
```python
# pip install neo4j
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
with driver.session() as session:
    result = session.run("MATCH (p:Person)-[:WORKS_AT]->(o:Org) RETURN p, o")
```
- **LangChain:** Excellent support
- **Most tutorials/docs:** Industry standard

### Memgraph
```python
# pip install gqlalchemy
from gqlalchemy import Memgraph

db = Memgraph(host='localhost', port=7687)
results = db.execute_and_fetch("MATCH (p:Person) RETURN p")
```
- **NetworkX compatible:** Direct graph algorithm integration
- **Streaming focus:** Kafka/Pulsar connectors

---

## 4. Recommendation for Startup (Retrieval Product @ SMB Scale)

### 🏆 **Primary: FalkorDB (Self-hosted)**

**Why:**
1. **$0 cost** - critical for runway
2. **496x faster** than Neo4j (per their benchmarks)
3. **GraphRAG-SDK** - purpose-built for retrieval/RAG use cases
4. **Multi-tenancy native** - serve multiple SMB customers on one instance
5. **Cypher compatible** - easy migration path if needed
6. **Active development** - backed by focused team

**Deployment:**
```bash
docker run -p 6379:6379 -it --rm falkordb/falkordb
```

### Alternative: Neo4j AuraDB Free → Professional

**When to choose:**
- Need maximum ecosystem support
- Team already knows Neo4j
- Willing to pay for managed service later

### Avoid: 
- **Kùzu** - Archived October 2025, no future development
- **Memgraph** - $25k/yr minimum too expensive for early-stage

---

## 5. Knowledge Graph Schema for People ↔ Organizations ↔ Projects ↔ Documents

### Node Types

```cypher
// People
CREATE (p:Person {
    id: "uuid",
    name: "string",
    email: "string",
    role: "string",
    embedding: [float]  // for vector search
})

// Organizations
CREATE (o:Organization {
    id: "uuid",
    name: "string",
    type: "company|department|team",
    industry: "string"
})

// Projects
CREATE (pr:Project {
    id: "uuid",
    name: "string",
    status: "active|completed|archived",
    start_date: date,
    end_date: date
})

// Documents
CREATE (d:Document {
    id: "uuid",
    title: "string",
    content_hash: "string",
    doc_type: "report|email|meeting_notes|spec",
    created_at: datetime,
    embedding: [float],  // for semantic search
    source_url: "string"
})
```

### Relationship Types

```cypher
// Person relationships
(p:Person)-[:WORKS_AT {role: "Engineer", since: date}]->(o:Organization)
(p:Person)-[:MANAGES]->(p2:Person)
(p:Person)-[:CONTRIBUTES_TO {role: "Lead|Member"}]->(pr:Project)
(p:Person)-[:AUTHORED]->(d:Document)
(p:Person)-[:MENTIONED_IN]->(d:Document)

// Organization relationships
(o:Organization)-[:PARENT_OF]->(o2:Organization)
(o:Organization)-[:OWNS]->(pr:Project)
(o:Organization)-[:PARTNER_WITH]->(o2:Organization)

// Project relationships
(pr:Project)-[:DEPENDS_ON]->(pr2:Project)
(pr:Project)-[:DOCUMENTED_BY]->(d:Document)

// Document relationships
(d:Document)-[:REFERENCES]->(d2:Document)
(d:Document)-[:RELATES_TO]->(pr:Project)
(d:Document)-[:ABOUT]->(o:Organization)
```

### Indexes for Performance

```cypher
// FalkorDB / Neo4j compatible
CREATE INDEX FOR (p:Person) ON (p.id)
CREATE INDEX FOR (p:Person) ON (p.email)
CREATE INDEX FOR (o:Organization) ON (o.id)
CREATE INDEX FOR (o:Organization) ON (o.name)
CREATE INDEX FOR (pr:Project) ON (pr.id)
CREATE INDEX FOR (d:Document) ON (d.id)

// Vector indexes (for semantic search)
CREATE VECTOR INDEX doc_embedding FOR (d:Document) ON d.embedding
CREATE VECTOR INDEX person_embedding FOR (p:Person) ON p.embedding
```

### Example Queries

```cypher
// Find all documents related to a person's projects
MATCH (p:Person {email: $email})-[:CONTRIBUTES_TO]->(pr:Project)
      -[:DOCUMENTED_BY]->(d:Document)
RETURN d.title, pr.name, d.created_at
ORDER BY d.created_at DESC

// Find collaboration network (who works with whom via shared projects)
MATCH (p1:Person)-[:CONTRIBUTES_TO]->(pr:Project)<-[:CONTRIBUTES_TO]-(p2:Person)
WHERE p1.id = $person_id AND p1 <> p2
RETURN p2.name, COUNT(pr) as shared_projects
ORDER BY shared_projects DESC

// Semantic search with vector similarity (FalkorDB)
CALL db.idx.vector.queryNodes('Document', 'embedding', $query_embedding, 10)
YIELD node, score
RETURN node.title, node.doc_type, score
```

---

## 6. Quick Start: FalkorDB + Python

```bash
# 1. Start FalkorDB
docker run -p 6379:6379 -d --name falkordb falkordb/falkordb

# 2. Install Python dependencies
pip install falkordb langchain-community

# 3. Initialize schema
python init_schema.py
```

```python
# init_schema.py
from falkordb import FalkorDB

db = FalkorDB()
graph = db.select_graph('knowledge')

# Create constraints and indexes
schema_queries = [
    "CREATE INDEX FOR (p:Person) ON (p.id)",
    "CREATE INDEX FOR (o:Organization) ON (o.id)", 
    "CREATE INDEX FOR (pr:Project) ON (pr.id)",
    "CREATE INDEX FOR (d:Document) ON (d.id)",
]

for q in schema_queries:
    graph.query(q)

print("Schema initialized!")
```

---

## Summary

| Criteria | Winner |
|----------|--------|
| **Best for Startups** | FalkorDB (self-hosted) |
| **Best Ecosystem** | Neo4j |
| **Best for Streaming** | Memgraph |
| **Avoid** | Kùzu (archived) |

**Action Items:**
1. Start with FalkorDB Docker for development
2. Use GraphRAG-SDK for retrieval pipeline
3. Plan Neo4j migration path if enterprise features needed later
